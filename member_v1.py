"""潮旅國際會員系統 V1：多重身分、OAuth、手機驗證、訂單認領與同意紀錄。

這個模組刻意以 register_member_v1() 掛入現有 Flask app，避免重寫既有單體應用。
第三方登入只信任 provider 的不可變 subject；Email/手機只有完成驗證後才能用於綁定或認領。
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import random
import base64
import secrets
import smtplib
import time
import urllib.error
import urllib.parse
import urllib.request
from email.mime.text import MIMEText

from flask import jsonify, redirect, request, session


OAUTH_PROVIDERS = {
    "google": {
        "authorize": "https://accounts.google.com/o/oauth2/v2/auth",
        "token": "https://oauth2.googleapis.com/token",
        "userinfo": "https://openidconnect.googleapis.com/v1/userinfo",
        "scope": "openid email profile",
        "subject": "sub",
        "name": "name",
        "email": "email",
        "email_verified": "email_verified",
    },
    "line": {
        "authorize": "https://access.line.me/oauth2/v2.1/authorize",
        "token": "https://api.line.me/oauth2/v2.1/token",
        "id_token_verify": "https://api.line.me/oauth2/v2.1/verify",
        "scope": "profile openid email",
        "subject": "sub",
        "name": "name",
        "email": "email",
    },
}


class ChallengeRateLimit(Exception):
    pass


def _digest(secret, *parts):
    raw = ":".join(str(part) for part in parts).encode("utf-8")
    return hmac.new(str(secret).encode("utf-8"), raw, hashlib.sha256).hexdigest()


def _mask(value):
    value = value or ""
    if "@" in value:
        local, domain = value.split("@", 1)
        return f"{local[:2]}***@{domain}"
    return "***" + value[-4:]


def _oauth_config(provider):
    spec = OAUTH_PROVIDERS.get(provider)
    if not spec:
        return None, "此登入方式尚未開放"
    client_id = os.environ.get(f"{provider.upper()}_OAUTH_CLIENT_ID", "").strip()
    client_secret = os.environ.get(f"{provider.upper()}_OAUTH_CLIENT_SECRET", "").strip()
    redirect_uri = os.environ.get(
        f"{provider.upper()}_OAUTH_REDIRECT_URI",
        f"{request.url_root.rstrip('/')}/api/member/oauth/{provider}/callback",
    ).strip()
    if not client_id or not client_secret:
        return None, "此登入方式尚未完成設定"
    return {**spec, "client_id": client_id, "client_secret": client_secret,
            "redirect_uri": redirect_uri}, None


def _post_form(url, data):
    req = urllib.request.Request(
        url, data=urllib.parse.urlencode(data).encode("utf-8"),
        headers={"Content-Type": "application/x-www-form-urlencoded",
                 "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=12) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _get_json(url, token):
    req = urllib.request.Request(
        url, headers={"Authorization": f"Bearer {token}", "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=12) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _verify_line_id_token(config, id_token, nonce, now=None):
    """透過 LINE 官方端點驗簽，再明確檢查 OIDC 的安全關鍵 claims。"""
    if not id_token or not nonce:
        raise ValueError("missing LINE id_token or nonce")
    claims = _post_form(config["id_token_verify"], {
        "id_token": id_token,
        "client_id": config["client_id"],
        "nonce": nonce,
    })
    current_time = int(time.time() if now is None else now)
    if claims.get("iss") != "https://access.line.me":
        raise ValueError("invalid LINE issuer")
    if str(claims.get("aud") or "") != str(config["client_id"]):
        raise ValueError("invalid LINE audience")
    if not hmac.compare_digest(str(claims.get("nonce") or ""), str(nonce)):
        raise ValueError("invalid LINE nonce")
    try:
        expires_at = int(claims.get("exp"))
    except (TypeError, ValueError):
        raise ValueError("invalid LINE expiry") from None
    if expires_at <= current_time:
        raise ValueError("expired LINE id_token")
    if not str(claims.get("sub") or ""):
        raise ValueError("missing LINE subject")
    return claims


def _send_email_code(destination, code, purpose):
    sender = os.environ.get("EMAIL_USER", "").strip()
    password = os.environ.get("EMAIL_PASS", "").strip()
    if not sender or not password:
        return False
    label = "訂單認領" if purpose == "order_claim" else "會員驗證"
    msg = MIMEText(f"您的潮旅{label}驗證碼是：{code}\n驗證碼 10 分鐘內有效。", "plain", "utf-8")
    msg["Subject"] = f"潮旅{label}驗證碼"
    msg["From"] = sender
    msg["To"] = destination
    with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=12) as smtp:
        smtp.login(sender, password)
        smtp.sendmail(sender, [destination], msg.as_string())
    return True


def _send_phone_code(destination, code):
    """供應商中立 SMS 接口；未設定時明確失敗，不把驗證碼寫進 log。"""
    url = os.environ.get("SMS_OTP_WEBHOOK_URL", "").strip()
    if not url:
        return False
    body = json.dumps({"to": destination, "code": code, "ttl_seconds": 600}).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    token = os.environ.get("SMS_OTP_WEBHOOK_TOKEN", "").strip()
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, data=body, headers=headers)
    with urllib.request.urlopen(req, timeout=12) as resp:
        return 200 <= resp.status < 300


def register_member_v1(app, get_db, next_member_no, normalize_phone, valid_email,
                       public_member, sync_completed_order_trip, recalculate_member,
                       require_member):
    """把 V1 API 掛到現有 app；參數注入避免循環 import。"""

    def current_member_id():
        """所有 legacy / V1 API 共用 app.py 的同一個 session validator。"""
        member = require_member()
        return member["id"] if member else None

    def has_recent_email_otp(member_id):
        """社群 identity 綁定既有帳號前，要求本站 Email OTP 的短效 step-up。"""
        proof = session.get("member_email_otp_proof") or {}
        try:
            proof_member_id = int(proof.get("member_id"))
            verified_at = int(proof.get("at"))
        except (TypeError, ValueError):
            return False
        return (proof_member_id == member_id
                and 0 <= int(time.time()) - verified_at <= 600)

    def issue_challenge(cur, member_id, purpose, channel, destination):
        cur.execute("""SELECT COUNT(*) AS n FROM member_verification_challenges
          WHERE member_id=%s AND purpose=%s AND created_at>NOW()-INTERVAL '1 hour'""",
                    (member_id, purpose))
        if int(cur.fetchone()["n"] or 0) >= 5:
            raise ChallengeRateLimit
        code = f"{random.SystemRandom().randrange(100000, 1000000)}"
        digest = _digest(app.secret_key, member_id or 0, purpose, channel, destination, code)
        cur.execute("""INSERT INTO member_verification_challenges
          (member_id,purpose,channel,destination_normalized,code_hash,expires_at)
          VALUES (%s,%s,%s,%s,%s,NOW()+INTERVAL '10 minutes') RETURNING id""",
                    (member_id, purpose, channel, destination, digest))
        return cur.fetchone()["id"], code

    def issue_anonymous_challenge(cur, purpose, channel, destination):
        """尚未有 member_id 的驗證（例如社群註冊要先證明 Email 是本人的）。

        沒有會員可以綁的時候，頻率限制必須改綁「收件目的地」，否則
        member_id IS NULL 的條件永遠算不到既有紀錄，等於完全沒有上限。
        """
        cur.execute("""SELECT COUNT(*) AS n FROM member_verification_challenges
          WHERE member_id IS NULL AND purpose=%s AND destination_normalized=%s
            AND created_at>NOW()-INTERVAL '1 hour'""", (purpose, destination))
        if int(cur.fetchone()["n"] or 0) >= 5:
            raise ChallengeRateLimit
        code = f"{random.SystemRandom().randrange(100000, 1000000)}"
        digest = _digest(app.secret_key, 0, purpose, channel, destination, code)
        cur.execute("""INSERT INTO member_verification_challenges
          (member_id,purpose,channel,destination_normalized,code_hash,expires_at)
          VALUES (NULL,%s,%s,%s,%s,NOW()+INTERVAL '10 minutes') RETURNING id""",
                    (purpose, channel, destination, digest))
        return cur.fetchone()["id"], code

    def verify_anonymous_challenge(cur, challenge_id, purpose, destination, code):
        cur.execute("""SELECT * FROM member_verification_challenges
          WHERE id=%s AND member_id IS NULL AND purpose=%s AND destination_normalized=%s
            AND used_at IS NULL AND expires_at>NOW() AND attempts<5 FOR UPDATE""",
                    (challenge_id, purpose, destination))
        row = cur.fetchone()
        if not row:
            return None
        expected = _digest(app.secret_key, 0, row["purpose"], row["channel"],
                           row["destination_normalized"], code)
        if not hmac.compare_digest(row["code_hash"], expected):
            cur.execute("UPDATE member_verification_challenges SET attempts=attempts+1 WHERE id=%s",
                        (challenge_id,))
            return None
        return row

    def verify_challenge(cur, challenge_id, member_id, code):
        cur.execute("""SELECT * FROM member_verification_challenges
          WHERE id=%s AND member_id=%s AND used_at IS NULL AND expires_at>NOW()
            AND attempts<5 FOR UPDATE""", (challenge_id, member_id))
        row = cur.fetchone()
        if not row:
            return None
        expected = _digest(app.secret_key, member_id, row["purpose"], row["channel"],
                           row["destination_normalized"], code)
        if not hmac.compare_digest(row["code_hash"], expected):
            cur.execute("UPDATE member_verification_challenges SET attempts=attempts+1 WHERE id=%s",
                        (challenge_id,))
            return None
        return row

    @app.get("/api/member/identities")
    def member_v1_identities():
        member_id = current_member_id()
        if not member_id:
            return jsonify(ok=False, error="尚未登入"), 401
        conn = get_db(); cur = conn.cursor()
        cur.execute("""SELECT provider,email_normalized,phone_normalized,verified_at,last_login_at
          FROM member_identities WHERE member_id=%s ORDER BY provider""", (member_id,))
        rows = []
        for row in cur.fetchall():
            row = dict(row)
            row["email_masked"] = _mask(row.pop("email_normalized", None))
            row["phone_masked"] = _mask(row.pop("phone_normalized", None))
            row["verified_at"] = str(row.get("verified_at") or "")
            row["last_login_at"] = str(row.get("last_login_at") or "")
            rows.append(row)
        cur.close(); conn.close()
        return jsonify(ok=True, identities=rows,
                       available_providers={"line": True, "google": True, "facebook": False})

    @app.get("/api/member/oauth/providers")
    def member_oauth_providers():
        """前台據此決定是否顯示社群登入入口。只回報「有沒有設定」，不外流憑證內容。"""
        providers = {}
        for name in OAUTH_PROVIDERS:
            client_id = os.environ.get(f"{name.upper()}_OAUTH_CLIENT_ID", "").strip()
            secret = os.environ.get(f"{name.upper()}_OAUTH_CLIENT_SECRET", "").strip()
            providers[name] = bool(client_id and secret)
        providers["facebook"] = False  # V1 保留欄位，尚未啟用。
        return jsonify(ok=True, providers=providers)

    @app.get("/api/member/oauth/<provider>/start")
    def member_oauth_start(provider):
        config, error = _oauth_config(provider)
        if error:
            return jsonify(ok=False, error=error), 503 if provider in OAUTH_PROVIDERS else 404
        state = secrets.token_urlsafe(32)
        verifier = secrets.token_urlsafe(48)
        nonce = secrets.token_urlsafe(32)
        challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).decode().rstrip("=")
        session["member_oauth_state"] = {"provider": provider, "state": state,
                                         "verifier": verifier, "nonce": nonce,
                                         "at": int(time.time())}
        query = {"response_type": "code", "client_id": config["client_id"],
                  "redirect_uri": config["redirect_uri"], "scope": config["scope"],
                  "state": state, "nonce": nonce, "code_challenge": challenge,
                  "code_challenge_method": "S256"}
        return redirect(config["authorize"] + "?" + urllib.parse.urlencode(query))

    @app.get("/api/member/oauth/<provider>/callback")
    def member_oauth_callback(provider):
        saved = session.pop("member_oauth_state", None) or {}
        state = request.args.get("state", "")
        if (saved.get("provider") != provider or not state
                or not hmac.compare_digest(saved.get("state", ""), state)
                or int(time.time()) - int(saved.get("at", 0)) > 600):
            return redirect("/member/dashboard?oauth_error=state")
        if request.args.get("error") or not request.args.get("code"):
            return redirect("/member/dashboard?oauth_error=denied")
        config, error = _oauth_config(provider)
        if error:
            return redirect("/member/dashboard?oauth_error=config")
        try:
            token = _post_form(config["token"], {
                "grant_type": "authorization_code", "code": request.args["code"],
                "redirect_uri": config["redirect_uri"], "client_id": config["client_id"],
                "client_secret": config["client_secret"], "code_verifier": saved["verifier"],
            })
            if provider == "line":
                profile = _verify_line_id_token(
                    config, token["id_token"], saved.get("nonce"))
                email_verified = bool(profile.get("email"))
            else:
                profile = _get_json(config["userinfo"], token["access_token"])
                email_verified = bool(profile.get(config["email_verified"]))
        except (KeyError, ValueError, urllib.error.URLError) as exc:
            app.logger.warning("OAuth callback failed for %s: %s", provider, type(exc).__name__)
            return redirect("/member/dashboard?oauth_error=provider")
        subject = str(profile.get(config["subject"]) or "")[:255]
        if not subject:
            return redirect("/member/dashboard?oauth_error=profile")
        email = str(profile.get(config["email"]) or "").strip().lower()[:200]
        safe_profile = {"name": str(profile.get(config["name"]) or "")[:100]}
        member_id = current_member_id()
        conn = get_db(); cur = conn.cursor()
        cur.execute("SELECT member_id FROM member_identities WHERE provider=%s AND provider_subject=%s",
                    (provider, subject))
        identity = cur.fetchone()
        if identity:
            if member_id and member_id != identity["member_id"]:
                cur.close(); conn.close()
                return redirect("/member/dashboard?oauth_error=belongs_to_other_member")
            member_id = identity["member_id"]
            cur.execute("UPDATE member_identities SET last_login_at=NOW(),updated_at=NOW() WHERE provider=%s AND provider_subject=%s",
                        (provider, subject))
            conn.commit(); cur.close(); conn.close()
            # 社群登入只證明這個 provider subject，不等於本站 Email OTP step-up。
            session.pop("member_email_otp_proof", None)
            session["member_id"] = member_id
            return redirect("/member/dashboard?oauth=ok")
        if member_id:
            cur.execute("""SELECT 1 FROM member_identities
                           WHERE member_id=%s AND provider='email'
                             AND verified_at IS NOT NULL LIMIT 1""", (member_id,))
            if not cur.fetchone() or not has_recent_email_otp(member_id):
                cur.close(); conn.close()
                return redirect("/member/dashboard?oauth_error=email_otp_required")
            cur.execute("""INSERT INTO member_identities
              (member_id,provider,provider_subject,email_normalized,verified_at,last_login_at,profile)
              VALUES (%s,%s,%s,%s,NOW(),NOW(),%s)""",
                        (member_id, provider, subject, email if email_verified else None,
                         json.dumps(safe_profile)))
            conn.commit(); cur.close(); conn.close()
            session.pop("member_email_otp_proof", None)
            return redirect("/member/dashboard?oauth=bound")
        cur.close(); conn.close()
        session["pending_oauth_identity"] = {
            "provider": provider, "subject": subject, "email": email if email_verified else "",
            "name": safe_profile["name"], "at": int(time.time())}
        return redirect("/member/dashboard?oauth_complete=1")

    @app.post("/api/member/oauth/complete")
    def member_oauth_complete():
        pending = session.get("pending_oauth_identity") or {}
        if not pending or int(time.time()) - int(pending.get("at", 0)) > 900:
            return jsonify(ok=False, error="社群登入資料已過期，請重新登入"), 400
        data = request.get_json(silent=True) or {}
        name = (data.get("name") or pending.get("name") or "").strip()[:100]
        phone = (data.get("phone") or "").strip()[:30]
        normalized = normalize_phone(phone)
        provider_email = (pending.get("email") or "").strip().lower()[:200]
        email = provider_email or (data.get("email") or "").strip().lower()[:200]
        if not data.get("consent") or not name or len(normalized) < 8 or not valid_email(email):
            return jsonify(ok=False, error="請填妥姓名、手機、Email 並同意個資告知事項"), 400
        conn = get_db(); cur = conn.cursor()
        # provider 沒有回傳「已驗證」的 Email 時，使用者自己打的那組必須先收 OTP 證明是本人。
        # 否則任何人都能拿別人的信箱＋自己的社群帳號開一個會員；受害者日後用 Email OTP
        # 登入時會登進同一個帳號，而攻擊者仍握有社群登入權（account pre-hijacking）。
        if not provider_email:
            expected_email = pending.get("verify_email")
            challenge_id = pending.get("verify_challenge_id")
            code = "".join(ch for ch in str(data.get("code") or "") if ch.isdigit())[:6]
            if not (challenge_id and expected_email == email and code):
                try:
                    challenge_id, otp = issue_anonymous_challenge(
                        cur, "oauth_signup_email", "email", email)
                except ChallengeRateLimit:
                    cur.close(); conn.close()
                    return jsonify(ok=False, error="驗證碼要求過於頻繁，請稍後再試"), 429
                conn.commit(); cur.close(); conn.close()
                try:
                    delivered = _send_email_code(email, otp, "oauth_signup")
                except Exception:
                    delivered = False
                if not delivered:
                    return jsonify(ok=False, error="驗證訊息暫時無法寄送"), 503
                session["pending_oauth_identity"] = {
                    **pending, "verify_email": email, "verify_challenge_id": challenge_id}
                return jsonify(ok=False, verify_required=True, expires_minutes=10,
                               error="請輸入寄到這個 Email 的六位數驗證碼以完成註冊"), 200
            challenge = verify_anonymous_challenge(
                cur, challenge_id, "oauth_signup_email", email, code)
            if not challenge:
                conn.commit(); cur.close(); conn.close()
                return jsonify(ok=False, error="驗證碼錯誤或已過期"), 401
            cur.execute("UPDATE member_verification_challenges SET used_at=NOW() WHERE id=%s",
                        (challenge["id"],))
            verified_email = email
        else:
            verified_email = provider_email
        # 手機或 Email 已被既有會員使用時一律回同一句話。分開回覆等於提供查詢介面，
        # 任何人都能用一個社群帳號逐一探測某支手機／某個信箱是不是潮旅會員。
        cur.execute("""SELECT id FROM members WHERE is_active=TRUE AND
          (phone_normalized=%s OR LOWER(email)=%s) LIMIT 1""", (normalized, email))
        if cur.fetchone():
            conn.commit(); cur.close(); conn.close()
            return jsonify(ok=False,
                           error="無法用這組資料建立會員；若您已是會員，請直接登入後再綁定社群帳號"), 409
        try:
            member_id, member_no = next_member_no(cur)
            cur.execute("""INSERT INTO members
              (id,member_no,name,phone,phone_normalized,email,consent_at)
              VALUES (%s,%s,%s,%s,%s,%s,NOW()) RETURNING *""",
                        (member_id, member_no, name, phone, normalized, email))
            member = cur.fetchone()
            cur.execute("""INSERT INTO member_identities
              (member_id,provider,provider_subject,email_normalized,verified_at,last_login_at,profile)
              VALUES (%s,%s,%s,%s,NOW(),NOW(),%s)""",
                        (member_id, pending["provider"], pending["subject"],
                         verified_email, json.dumps({"name": pending.get("name", "")})))
            # Email 到這裡一定通過 provider 驗證或本站 OTP，才記成可用於認領／合併的身分。
            cur.execute("""INSERT INTO member_identities
              (member_id,provider,provider_subject,email_normalized,verified_at,last_login_at)
              VALUES (%s,'email',%s,%s,NOW(),NOW())
              ON CONFLICT (provider,provider_subject) DO NOTHING""",
                        (member_id, verified_email, verified_email))
            cur.execute("""INSERT INTO member_consents
              (member_id,consent_type,policy_version,granted,source)
              VALUES (%s,'privacy',%s,TRUE,'oauth_signup')""",
                        (member_id, os.environ.get("MEMBER_PRIVACY_POLICY_VERSION", "v1")))
            conn.commit(); cur.close(); conn.close()
        except Exception:
            conn.rollback(); cur.close(); conn.close()
            return jsonify(ok=False, error="無法建立會員，請稍後再試"), 409
        session.pop("pending_oauth_identity", None)
        session.pop("member_email_otp_proof", None)
        session["member_id"] = member_id
        return jsonify(ok=True, member=public_member(member)), 201

    @app.post("/api/member/phone/request")
    def member_phone_request():
        member_id = current_member_id()
        if not member_id:
            return jsonify(ok=False, error="尚未登入"), 401
        phone = normalize_phone((request.get_json(silent=True) or {}).get("phone"))
        if len(phone) < 8:
            return jsonify(ok=False, error="手機格式不正確"), 400
        conn = get_db(); cur = conn.cursor()
        cur.execute("""SELECT member_id FROM member_identities
          WHERE provider='phone' AND provider_subject=%s""", (phone,))
        owner = cur.fetchone()
        if owner and owner["member_id"] != member_id:
            cur.close(); conn.close()
            return jsonify(ok=False, error="此手機已綁定其他會員，請聯絡客服"), 409
        try:
            challenge_id, code = issue_challenge(cur, member_id, "phone_bind", "phone", phone)
        except ChallengeRateLimit:
            cur.close(); conn.close()
            return jsonify(ok=False, error="驗證碼要求過於頻繁，請稍後再試"), 429
        conn.commit(); cur.close(); conn.close()
        try:
            delivered = _send_phone_code(phone, code)
        except Exception:
            delivered = False
        if not delivered:
            return jsonify(ok=False, error="手機驗證服務尚未設定或暫時無法使用"), 503
        return jsonify(ok=True, challenge_id=challenge_id, expires_minutes=10)

    @app.post("/api/member/phone/verify")
    def member_phone_verify():
        member_id = current_member_id(); data = request.get_json(silent=True) or {}
        if not member_id:
            return jsonify(ok=False, error="尚未登入"), 401
        code = "".join(ch for ch in str(data.get("code") or "") if ch.isdigit())[:6]
        conn = get_db(); cur = conn.cursor()
        challenge = verify_challenge(cur, data.get("challenge_id"), member_id, code)
        if not challenge or challenge["purpose"] != "phone_bind":
            conn.commit(); cur.close(); conn.close()
            return jsonify(ok=False, error="驗證碼錯誤或已過期"), 401
        phone = challenge["destination_normalized"]
        try:
            cur.execute("""INSERT INTO member_identities
              (member_id,provider,provider_subject,phone_normalized,verified_at,last_login_at)
              VALUES (%s,'phone',%s,%s,NOW(),NOW())
              ON CONFLICT (provider,provider_subject) DO UPDATE SET
                last_login_at=NOW(),updated_at=NOW()""", (member_id, phone, phone))
            cur.execute("UPDATE member_verification_challenges SET used_at=NOW() WHERE id=%s",
                        (challenge["id"],))
            conn.commit(); cur.close(); conn.close()
            return jsonify(ok=True, phone_masked=_mask(phone))
        except Exception:
            conn.rollback(); cur.close(); conn.close()
            return jsonify(ok=False, error="此手機已綁定其他會員"), 409

    @app.post("/api/member/orders/claim/request")
    def member_order_claim_request():
        member_id = current_member_id(); data = request.get_json(silent=True) or {}
        if not member_id:
            return jsonify(ok=False, error="尚未登入"), 401
        order_type = (data.get("order_type") or "").strip()
        booking_ref = (data.get("booking_ref") or "").strip()[:40]
        channel = (data.get("channel") or "").strip()
        tables = {"neihai_order": "neihai_preorders", "preorder_order": "preorder_orders"}
        if order_type not in tables or channel not in {"email", "phone"} or not booking_ref:
            return jsonify(ok=False, error="訂單或驗證方式不正確"), 400
        conn = get_db(); cur = conn.cursor()
        cur.execute(f"SELECT id,member_id,contact_email,contact_phone FROM {tables[order_type]} WHERE booking_ref=%s FOR UPDATE",
                    (booking_ref,))
        order = cur.fetchone()
        if not order:
            cur.close(); conn.close()
            return jsonify(ok=False, error="找不到可認領訂單"), 404
        if order.get("member_id") not in (None, member_id):
            cur.close(); conn.close()
            return jsonify(ok=False, error="此訂單已由其他會員認領"), 409
        destination = ((order.get("contact_email") or "").strip().lower() if channel == "email"
                       else normalize_phone(order.get("contact_phone")))
        if not destination:
            cur.close(); conn.close()
            return jsonify(ok=False, error="訂單沒有可驗證的聯絡資料，請聯絡客服"), 400
        try:
            challenge_id, code = issue_challenge(cur, member_id, "order_claim", channel, destination)
        except ChallengeRateLimit:
            cur.close(); conn.close()
            return jsonify(ok=False, error="驗證碼要求過於頻繁，請稍後再試"), 429
        cur.execute("""INSERT INTO order_claims
          (member_id,order_type,order_id,channel,destination_normalized,challenge_id)
          VALUES (%s,%s,%s,%s,%s,%s)
          ON CONFLICT (order_type,order_id) DO UPDATE SET member_id=EXCLUDED.member_id,
            channel=EXCLUDED.channel,destination_normalized=EXCLUDED.destination_normalized,
            challenge_id=EXCLUDED.challenge_id,claimed_at=NULL,created_at=NOW()
          RETURNING id""", (member_id, order_type, order["id"], channel, destination, challenge_id))
        claim_id = cur.fetchone()["id"]
        conn.commit(); cur.close(); conn.close()
        try:
            delivered = (_send_email_code(destination, code, "order_claim") if channel == "email"
                         else _send_phone_code(destination, code))
        except Exception:
            delivered = False
        if not delivered:
            return jsonify(ok=False, error="驗證訊息暫時無法寄送"), 503
        return jsonify(ok=True, claim_id=claim_id, destination_masked=_mask(destination),
                       expires_minutes=10)

    @app.post("/api/member/orders/claim/verify")
    def member_order_claim_verify():
        member_id = current_member_id(); data = request.get_json(silent=True) or {}
        if not member_id:
            return jsonify(ok=False, error="尚未登入"), 401
        code = "".join(ch for ch in str(data.get("code") or "") if ch.isdigit())[:6]
        conn = get_db(); cur = conn.cursor()
        cur.execute("""SELECT * FROM order_claims WHERE id=%s AND member_id=%s
          AND claimed_at IS NULL FOR UPDATE""", (data.get("claim_id"), member_id))
        claim = cur.fetchone()
        if not claim:
            cur.close(); conn.close()
            return jsonify(ok=False, error="認領資料不存在或已使用"), 404
        challenge = verify_challenge(cur, claim["challenge_id"], member_id, code)
        if not challenge or challenge["purpose"] != "order_claim":
            conn.commit(); cur.close(); conn.close()
            return jsonify(ok=False, error="驗證碼錯誤或已過期"), 401
        tables = {"neihai_order": "neihai_preorders", "preorder_order": "preorder_orders"}
        table = tables[claim["order_type"]]
        cur.execute(f"""UPDATE {table} SET member_id=%s,claimed_at=NOW(),claim_method=%s
          WHERE id=%s AND (member_id IS NULL OR member_id=%s) RETURNING *""",
                    (member_id, claim["channel"], claim["order_id"], member_id))
        order = cur.fetchone()
        if not order:
            conn.rollback(); cur.close(); conn.close()
            return jsonify(ok=False, error="此訂單已由其他會員認領"), 409
        cur.execute("UPDATE order_claims SET claimed_at=NOW() WHERE id=%s", (claim["id"],))
        cur.execute("UPDATE member_verification_challenges SET used_at=NOW() WHERE id=%s",
                    (challenge["id"],))
        if claim["order_type"] == "neihai_order":
            cur.execute("SELECT sailing_date FROM neihai_sailings WHERE id=%s", (order["sailing_id"],))
            sailing = cur.fetchone()
            sync_completed_order_trip(cur, "neihai_order", order["booking_ref"], member_id,
                                      "小城故事・內海巡禮",
                                      sailing["sailing_date"] if sailing else None,
                                      order["status"], True)
        else:
            cur.execute("SELECT name,counts_as_trip FROM preorder_products WHERE id=%s",
                        (order["product_id"],))
            product = cur.fetchone()
            if product:
                sync_completed_order_trip(cur, "preorder_order", order["booking_ref"], member_id,
                                          product["name"], order["departure_date"], order["status"],
                                          bool(product.get("counts_as_trip", True)))
        conn.commit(); cur.close(); conn.close()
        return jsonify(ok=True, order_type=claim["order_type"], order_id=claim["order_id"])

    @app.get("/api/member/orders")
    def member_orders():
        member_id = current_member_id()
        if not member_id:
            return jsonify(ok=False, error="尚未登入"), 401
        conn = get_db(); cur = conn.cursor()
        cur.execute("""SELECT 'neihai_order' AS order_type,o.id,o.booking_ref,o.status,
                 s.sailing_date AS departure_date,'小城故事・內海巡禮' AS product_name,o.claimed_at
          FROM neihai_preorders o JOIN neihai_sailings s ON s.id=o.sailing_id WHERE o.member_id=%s
          UNION ALL
          SELECT 'preorder_order',o.id,o.booking_ref,o.status,o.departure_date,p.name,o.claimed_at
          FROM preorder_orders o JOIN preorder_products p ON p.id=o.product_id WHERE o.member_id=%s
          ORDER BY departure_date DESC""", (member_id, member_id))
        rows = []
        for row in cur.fetchall():
            row = dict(row); row["departure_date"] = str(row.get("departure_date") or "")
            row["claimed_at"] = str(row.get("claimed_at") or "")
            rows.append(row)
        cur.close(); conn.close()
        return jsonify(ok=True, orders=rows)

    @app.post("/api/member/merge/request")
    def member_merge_request():
        """要求合併另一帳號：目前 session 證明目標帳號，OTP 證明來源帳號。"""
        target_id = current_member_id(); data = request.get_json(silent=True) or {}
        if not target_id:
            return jsonify(ok=False, error="尚未登入"), 401
        source_email = (data.get("source_email") or "").strip().lower()[:200]
        if not valid_email(source_email):
            return jsonify(ok=False, error="Email 格式不正確"), 400
        conn = get_db(); cur = conn.cursor()
        cur.execute("""SELECT i.id,i.member_id FROM member_identities i
          JOIN members m ON m.id=i.member_id
          WHERE i.provider='email' AND i.email_normalized=%s AND i.verified_at IS NOT NULL
            AND i.member_id<>%s AND m.is_active=TRUE""", (source_email, target_id))
        proof = cur.fetchone()
        if not proof:
            cur.close(); conn.close()
            # 不透露指定 Email 是否為會員或是否已驗證。
            return jsonify(ok=True, message="若資料符合，我們已寄出合併驗證碼")
        try:
            challenge_id, code = issue_challenge(cur, target_id, "account_merge", "email", source_email)
        except ChallengeRateLimit:
            cur.close(); conn.close()
            return jsonify(ok=False, error="驗證碼要求過於頻繁，請稍後再試"), 429
        cur.execute("""INSERT INTO member_merge_requests
          (source_member_id,target_member_id,proof_identity_id,challenge_id)
          VALUES (%s,%s,%s,%s) RETURNING id""",
                    (proof["member_id"], target_id, proof["id"], challenge_id))
        request_id = cur.fetchone()["id"]
        conn.commit(); cur.close(); conn.close()
        try:
            delivered = _send_email_code(source_email, code, "account_merge")
        except Exception:
            delivered = False
        if not delivered:
            return jsonify(ok=False, error="驗證訊息暫時無法寄送"), 503
        return jsonify(ok=True, request_id=request_id, expires_minutes=10,
                       message="若資料符合，我們已寄出合併驗證碼")

    @app.post("/api/member/merge/confirm")
    def member_merge_confirm():
        target_id = current_member_id(); data = request.get_json(silent=True) or {}
        if not target_id:
            return jsonify(ok=False, error="尚未登入"), 401
        code = "".join(ch for ch in str(data.get("code") or "") if ch.isdigit())[:6]
        conn = get_db(); cur = conn.cursor()
        cur.execute("""SELECT * FROM member_merge_requests
          WHERE id=%s AND target_member_id=%s AND status='pending' FOR UPDATE""",
                    (data.get("request_id"), target_id))
        merge = cur.fetchone()
        if not merge:
            cur.close(); conn.close()
            return jsonify(ok=False, error="合併要求不存在或已處理"), 404
        challenge = verify_challenge(cur, merge["challenge_id"], target_id, code)
        if not challenge or challenge["purpose"] != "account_merge":
            conn.commit(); cur.close(); conn.close()
            return jsonify(ok=False, error="驗證碼錯誤或已過期"), 401
        source_id = merge["source_member_id"]
        first, second = sorted((source_id, target_id))
        cur.execute("SELECT id FROM members WHERE id IN (%s,%s) ORDER BY id FOR UPDATE",
                    (first, second))
        if len(cur.fetchall()) != 2:
            conn.rollback(); cur.close(); conn.close()
            return jsonify(ok=False, error="來源或目標會員不存在"), 404
        try:
            # 先搬所有關聯資料；任何唯一鍵衝突都整筆 rollback，交由客服人工判斷。
            for table in ("member_identities", "member_trips", "member_points",
                          "point_transactions", "member_consents", "order_claims"):
                cur.execute(f"UPDATE {table} SET member_id=%s WHERE member_id=%s",
                            (target_id, source_id))
            for table in ("neihai_preorders", "preorder_orders"):
                cur.execute(f"UPDATE {table} SET member_id=%s WHERE member_id=%s",
                            (target_id, source_id))
            cur.execute("DELETE FROM member_auth_codes WHERE member_id=%s", (source_id,))
            cur.execute("DELETE FROM member_verification_challenges WHERE member_id=%s AND id<>%s",
                        (source_id, challenge["id"]))
            cur.execute("DELETE FROM point_wallet WHERE member_id=%s", (source_id,))
            cur.execute("""UPDATE members SET is_active=FALSE,merged_into_member_id=%s,
              phone='',phone_normalized=%s,email=%s,line_user_id=NULL,
              trip_count=0,points_balance=0,updated_at=NOW() WHERE id=%s""",
                        (target_id, f"merged:{source_id}",
                         f"merged+{source_id}@invalid.local", source_id))
            cur.execute("UPDATE member_verification_challenges SET used_at=NOW() WHERE id=%s",
                        (challenge["id"],))
            cur.execute("""UPDATE member_merge_requests SET status='completed',completed_at=NOW()
              WHERE id=%s""", (merge["id"],))
            recalculate_member(cur, target_id)
            conn.commit(); cur.close(); conn.close()
            return jsonify(ok=True, member_id=target_id)
        except Exception as exc:
            conn.rollback(); cur.close(); conn.close()
            app.logger.warning("Member merge conflict: %s", type(exc).__name__)
            return jsonify(ok=False, error="兩帳號有衝突資料，未進行合併；請聯絡客服人工確認"), 409

    @app.post("/api/member/consents")
    def member_consents():
        member_id = current_member_id(); data = request.get_json(silent=True) or {}
        if not member_id:
            return jsonify(ok=False, error="尚未登入"), 401
        consent_type = (data.get("consent_type") or "").strip()[:50]
        if consent_type not in {"privacy", "marketing", "line_notification"}:
            return jsonify(ok=False, error="同意項目不正確"), 400
        version = (data.get("policy_version") or os.environ.get("MEMBER_PRIVACY_POLICY_VERSION", "v1"))[:40]
        ip_hash = _digest(app.secret_key, request.remote_addr or "")
        ua_hash = _digest(app.secret_key, request.headers.get("User-Agent", ""))
        conn = get_db(); cur = conn.cursor()
        cur.execute("""INSERT INTO member_consents
          (member_id,consent_type,policy_version,granted,source,ip_hash,user_agent_hash)
          VALUES (%s,%s,%s,%s,'member_center',%s,%s)""",
                    (member_id, consent_type, version, bool(data.get("granted")), ip_hash, ua_hash))
        conn.commit(); cur.close(); conn.close()
        return jsonify(ok=True)
