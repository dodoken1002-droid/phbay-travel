"""會員 V1 的安全邊界與 API 契約測試（不需連線正式資料庫）。

分兩層：

* 不需資料庫的契約／路由測試，永遠會跑。
* `MEMBER_V1_TEST_DATABASE_URL` 指到一個「可拋棄」的空 PostgreSQL 時，才會跑
  真的建表、下單、認領、合併、算點的行為測試。沒設就整批 skip，
  絕對不要把這個變數指向正式資料庫——測試會直接寫入並改動資料。

  本機起一個拋棄式實例的方式（Windows，PostgreSQL 18）：

      initdb -D %TEMP%\\pgtest -U postgres -A trust -E UTF8 --locale=C
      pg_ctl -D %TEMP%\\pgtest -o "-p 55433" -l %TEMP%\\pg.log start
      psql -h 127.0.0.1 -p 55433 -U postgres -c "CREATE DATABASE member_v1_test"
      set MEMBER_V1_TEST_DATABASE_URL=postgresql://postgres@127.0.0.1:55433/member_v1_test
"""

import os
import http.client
import concurrent.futures
import threading
import time
import unittest
import urllib.parse
from pathlib import Path
from unittest import mock

from app import app
import member_v1


ROOT = Path(__file__).parent
TEST_DB_URL = os.environ.get("MEMBER_V1_TEST_DATABASE_URL", "").strip()


class MemberV1RouteTests(unittest.TestCase):
    def setUp(self):
        app.config.update(TESTING=True)
        self.client = app.test_client()

    def test_member_private_endpoints_require_login_before_database(self):
        cases = [
            ("get", "/api/member/identities", None),
            ("get", "/api/member/orders", None),
            ("post", "/api/member/phone/request", {"phone": "0912345678"}),
            ("post", "/api/member/orders/claim/request", {
                "order_type": "preorder_order", "booking_ref": "X", "channel": "email"}),
        ]
        for method, path, payload in cases:
            response = getattr(self.client, method)(path, json=payload)
            self.assertEqual(response.status_code, 401, path)

    def test_facebook_is_reserved_but_not_enabled(self):
        response = self.client.get("/api/member/oauth/facebook/start")
        self.assertEqual(response.status_code, 404)

    def test_line_and_google_start_use_state_nonce_and_pkce(self):
        provider_hosts = {
            "line": "access.line.me",
            "google": "accounts.google.com",
        }
        configured = {
            "LINE_OAUTH_CLIENT_ID": "line-test-client",
            "LINE_OAUTH_CLIENT_SECRET": "line-test-secret",
            "LINE_OAUTH_REDIRECT_URI": "https://www.phbay.info/api/member/oauth/line/callback",
            "GOOGLE_OAUTH_CLIENT_ID": "google-test-client",
            "GOOGLE_OAUTH_CLIENT_SECRET": "google-test-secret",
            "GOOGLE_OAUTH_REDIRECT_URI": "https://www.phbay.info/api/member/oauth/google/callback",
        }
        with mock.patch.dict(os.environ, configured, clear=False):
            for provider, expected_host in provider_hosts.items():
                with self.subTest(provider=provider):
                    response = self.client.get(f"/api/member/oauth/{provider}/start")
                    self.assertEqual(response.status_code, 302)
                    parsed = urllib.parse.urlparse(response.location)
                    query = urllib.parse.parse_qs(parsed.query)
                    self.assertEqual(parsed.scheme, "https")
                    self.assertEqual(parsed.hostname, expected_host)
                    self.assertEqual(query["response_type"], ["code"])
                    self.assertEqual(query["code_challenge_method"], ["S256"])
                    self.assertEqual(
                        query["redirect_uri"],
                        [f"https://www.phbay.info/api/member/oauth/{provider}/callback"])
                    self.assertTrue({"openid", "email"}.issubset(
                        set(query["scope"][0].split())))
                    self.assertGreaterEqual(len(query["state"][0]), 32)
                    self.assertGreaterEqual(len(query["nonce"][0]), 32)
                    with self.client.session_transaction() as sess:
                        saved = dict(sess["member_oauth_state"])
                    self.assertEqual(saved["provider"], provider)
                    self.assertEqual(saved["state"], query["state"][0])
                    self.assertEqual(saved["nonce"], query["nonce"][0])
                    self.assertNotEqual(saved["verifier"], query["code_challenge"][0])

    def test_oauth_callback_rejects_invalid_state_and_handles_cancel(self):
        configured = {
            "LINE_OAUTH_CLIENT_ID": "line-test-client",
            "LINE_OAUTH_CLIENT_SECRET": "line-test-secret",
        }
        with mock.patch.dict(os.environ, configured, clear=False):
            invalid = self.client.get(
                "/api/member/oauth/line/callback?state=attacker&code=unused")
            self.assertEqual(invalid.status_code, 302)
            self.assertIn("oauth_error=state", invalid.location)

            started = self.client.get("/api/member/oauth/line/start")
            query = urllib.parse.parse_qs(urllib.parse.urlparse(started.location).query)
            cancelled = self.client.get(
                "/api/member/oauth/line/callback",
                query_string={"state": query["state"][0], "error": "access_denied"})
            self.assertEqual(cancelled.status_code, 302)
            self.assertIn("oauth_error=denied", cancelled.location)
            with self.client.session_transaction() as sess:
                self.assertNotIn("member_oauth_state", sess,
                                 "OAuth state must be single-use after a callback")

    def test_oauth_callback_handles_non_ascii_state_and_provider_network_errors(self):
        configured = {
            "LINE_OAUTH_CLIENT_ID": "line-test-client",
            "LINE_OAUTH_CLIENT_SECRET": "line-test-secret",
        }
        with mock.patch.dict(os.environ, configured, clear=False):
            started = self.client.get("/api/member/oauth/line/start")
            self.assertEqual(started.status_code, 302)
            non_ascii = self.client.get(
                "/api/member/oauth/line/callback", query_string={"state": "測試", "code": "x"})
            self.assertEqual(non_ascii.status_code, 302)
            self.assertIn("oauth_error=state", non_ascii.location)

            for error in (ConnectionResetError(), http.client.IncompleteRead(b""), TimeoutError()):
                with self.subTest(error=type(error).__name__):
                    started = self.client.get("/api/member/oauth/line/start")
                    state = urllib.parse.parse_qs(
                        urllib.parse.urlparse(started.location).query)["state"][0]
                    with mock.patch.object(member_v1, "_post_form", side_effect=error):
                        failed = self.client.get(
                            "/api/member/oauth/line/callback",
                            query_string={"state": state, "code": "x"})
                    self.assertEqual(failed.status_code, 302)
                    self.assertIn("oauth_error=provider", failed.location)

    def test_member_email_codes_use_the_shared_delivery_entrypoint(self):
        delivered = []

        def deliver(sender, recipient, message):
            delivered.append((sender, recipient, message["Subject"]))
            return True, "test"

        with mock.patch.dict(os.environ, {"EMAIL_USER": "sender@example.com"}, clear=False):
            self.assertTrue(member_v1._send_email_code(
                "guest@example.com", "123456", "order_claim", deliver))
        self.assertEqual(delivered[0][:2], ("sender@example.com", "guest@example.com"))

    def test_legacy_member_regression_routes_remain_registered(self):
        """P0 修正不可移除既有正式會員、綁定、點數、合併或認領入口。"""
        routes = {(rule.rule, tuple(sorted(rule.methods - {"HEAD", "OPTIONS"})))
                  for rule in app.url_map.iter_rules()}
        expected = {
            ("/api/member/register", ("POST",)),
            ("/api/member/login/request", ("POST",)),
            ("/api/member/login/verify", ("POST",)),
            ("/api/member/me", ("GET",)),
            ("/api/member/line-bind-code", ("POST",)),
            ("/api/admin/members/<int:member_id>/points", ("POST",)),
            ("/api/admin/members/merge", ("POST",)),
            ("/api/member/orders/claim/request", ("POST",)),
            ("/api/member/orders/claim/verify", ("POST",)),
        }
        self.assertTrue(expected.issubset(routes), expected - routes)


class LineIdTokenTests(unittest.TestCase):
    def setUp(self):
        self.config = {
            "id_token_verify": "https://api.line.me/oauth2/v2.1/verify",
            "client_id": "line-channel-123",
        }
        self.claims = {
            "iss": "https://access.line.me", "aud": "line-channel-123",
            "nonce": "nonce-123", "exp": 2_000_000_000,
            "sub": "Uimmutable", "email": "member@example.com",
        }

    def test_line_identity_comes_from_verified_id_token(self):
        with mock.patch.object(member_v1, "_post_form", return_value=self.claims) as verify:
            result = member_v1._verify_line_id_token(
                self.config, "signed.jwt", "nonce-123", now=1_900_000_000)
        self.assertEqual(result["sub"], "Uimmutable")
        verify.assert_called_once_with(
            self.config["id_token_verify"],
            {"id_token": "signed.jwt", "client_id": "line-channel-123",
             "nonce": "nonce-123"})

    def test_line_id_token_rejects_wrong_security_claims(self):
        mutations = {
            "issuer": {"iss": "https://attacker.example"},
            "audience": {"aud": "other-channel"},
            "nonce": {"nonce": "replayed"},
            "expiry": {"exp": 1_800_000_000},
            "subject": {"sub": ""},
        }
        for label, mutation in mutations.items():
            with self.subTest(label=label):
                claims = {**self.claims, **mutation}
                with mock.patch.object(member_v1, "_post_form", return_value=claims):
                    with self.assertRaises(ValueError):
                        member_v1._verify_line_id_token(
                            self.config, "signed.jwt", "nonce-123", now=1_900_000_000)


class MemberV1SchemaTests(unittest.TestCase):
    def setUp(self):
        self.program = (ROOT / "member_program.py").read_text(encoding="utf-8")
        self.app_src = (ROOT / "app.py").read_text(encoding="utf-8")
        self.v1 = (ROOT / "member_v1.py").read_text(encoding="utf-8")

    def test_v1_tables_exist(self):
        for table in ("member_identities", "member_consents", "point_wallet",
                      "point_transactions", "member_verification_challenges",
                      "order_claims", "member_merge_requests"):
            self.assertIn(f"CREATE TABLE IF NOT EXISTS {table}", self.program)

    def test_orders_have_explicit_member_foreign_key(self):
        self.assertIn("ADD COLUMN IF NOT EXISTS member_id INT REFERENCES members(id)", self.app_src)
        self.assertIn("authenticated_checkout", self.app_src)

    def test_order_sync_never_guesses_member_from_contact_phone(self):
        body = self.app_src.split("def _sync_completed_order_trip", 1)[1].split("@app.route", 1)[0]
        self.assertIn("WHERE id=%s", body)
        self.assertNotIn("phone_normalized=%s", body)

    def test_claim_requires_verified_challenge(self):
        body = self.v1.split("def member_order_claim_verify", 1)[1]
        self.assertIn("verify_challenge", body)
        self.assertIn("used_at=NOW()", body)
        self.assertIn("attempts<5", self.v1)

    def test_claim_requires_contact_hint_and_preserves_audit_foreign_keys(self):
        self.assertIn('data.get("verification_hint")', self.v1)
        order_claims = self.program.split("CREATE TABLE IF NOT EXISTS order_claims", 1)[1].split(
            '"""', 1)[0]
        self.assertEqual(order_claims.count("ON DELETE RESTRICT"), 2)

    def test_member_v1_email_does_not_open_its_own_smtp_connection(self):
        self.assertNotIn("import smtplib", self.v1)
        registration = self.app_src.split("register_member_v1(app", 1)[1]
        self.assertIn("_deliver", registration)

    def test_oauth_uses_provider_subject_and_state(self):
        self.assertIn("UNIQUE (provider, provider_subject)", self.program)
        self.assertIn("hmac.compare_digest", self.v1)
        self.assertIn("member_oauth_state", self.v1)

    def test_all_member_apis_share_one_session_validator(self):
        self.assertIn("def require_member():", self.app_src)
        self.assertIn("member = require_member()", self.app_src)
        self.assertIn("require_member, deliver_email):", self.v1)
        current = self.v1.split("def current_member_id", 1)[1].split("def issue_challenge", 1)[0]
        self.assertIn("require_member()", current)
        self.assertNotIn("SELECT id FROM members", current)

    def test_line_oauth_uses_nonce_and_id_token_not_profile_endpoint(self):
        line_config = self.v1.split('"line": {', 1)[1].split("},", 1)[0]
        self.assertIn('"id_token_verify"', line_config)
        self.assertNotIn("/v2/profile", line_config)
        self.assertIn('"nonce": nonce', self.v1)
        self.assertIn('token["id_token"]', self.v1)

    def test_existing_account_binding_requires_recent_site_email_otp(self):
        callback = self.v1.split("def member_oauth_callback", 1)[1].split(
            "def member_oauth_complete", 1)[0]
        self.assertIn("has_recent_email_otp(member_id)", callback)
        self.assertIn("email_otp_required", callback)
        self.assertIn("member_email_otp_proof", self.app_src)

    def test_member_center_explains_oauth_email_step_up(self):
        member_html = (ROOT / "member.html").read_text(encoding="utf-8")
        self.assertIn("oauthError==='email_otp_required'", member_html)
        self.assertIn("請先使用 Email 驗證碼重新登入", member_html)

    def test_member_center_explains_every_oauth_callback_error(self):
        member_html = (ROOT / "member.html").read_text(encoding="utf-8")
        self.assertIn("const oauthError=params.get('oauth_error')", member_html)
        self.assertIn('id="oauth-status"', member_html)
        self.assertIn("status.textContent=text", member_html)
        self.assertIn("if(oauthError!=='email_otp_required')loadDashboard()", member_html)
        for error in ("state", "denied", "config", "provider", "profile",
                      "belongs_to_other_member", "email_otp_required"):
            self.assertIn(error, member_html)
        self.assertIn("textContent=text", member_html,
                      "OAuth errors must be rendered as text, never injected HTML")

    def test_otp_is_not_logged_or_returned(self):
        self.assertNotIn("print(code", self.v1)
        phone_response = self.v1.split("def member_phone_request", 1)[1].split(
            "@app.post", 1)[0]
        self.assertNotIn("code=code", phone_response)

    def test_checkout_does_not_trust_raw_session_member_id(self):
        """下單寫入 member_id 前必須先確認該會員仍有效（未停用、未被合併）。"""
        for marker in ("INSERT INTO neihai_preorders", "INSERT INTO preorder_orders"):
            body = self.app_src.split(marker, 1)[1].split("RETURNING id, created_at", 1)[0]
            self.assertNotIn("session.get('member_id')", body, marker)
        self.assertIn("def _checkout_member_id(cur):", self.app_src)

    def test_point_wallet_balance_is_not_clamped(self):
        """兌換後訂單被取消會讓餘額變負；wallet 不可 clamp 成 0，否則三方對不起來。"""
        create = self.program.split("CREATE TABLE IF NOT EXISTS point_wallet", 1)[1].split('"""', 1)[0]
        columns = [line.strip() for line in create.splitlines()
                   if line.strip() and not line.strip().startswith("--")]
        balance = next(line for line in columns if line.startswith("balance "))
        self.assertNotIn("CHECK", balance, balance)
        self.assertIn("DROP CONSTRAINT IF EXISTS point_wallet_balance_check", self.program)


# ─── 需要可拋棄 PostgreSQL 的行為測試 ────────────────────────────────
@unittest.skipUnless(TEST_DB_URL, "未設定 MEMBER_V1_TEST_DATABASE_URL（需可拋棄的測試資料庫）")
class MemberV1DatabaseTests(unittest.TestCase):
    """真的建表、下單、認領、合併、算點，驗證安全性與帳本一致性。"""

    @classmethod
    def setUpClass(cls):
        os.environ["DATABASE_URL"] = TEST_DB_URL
        os.environ.setdefault("MEMBER_POINTS_PER_TRIP", "100")
        import app as app_module
        import member_v1
        cls.A = app_module
        cls.V1 = member_v1
        cls.sent = []
        cls.original_send_email_code = member_v1._send_email_code
        cls.original_send_phone_code = member_v1._send_phone_code
        member_v1._send_email_code = lambda dest, code, purpose, deliver: (
            cls.sent.append((dest, code, purpose)), True)[1]
        member_v1._send_phone_code = lambda dest, code: (
            cls.sent.append((dest, code, "phone")), True)[1]
        cls.A.init_db()
        cls.A.app.config.update(TESTING=True)

    @classmethod
    def tearDownClass(cls):
        cls.V1._send_email_code = cls.original_send_email_code
        cls.V1._send_phone_code = cls.original_send_phone_code

    def setUp(self):
        self.sent.clear()
        conn = self.A.get_db(); cur = conn.cursor()
        # 每個測試從乾淨的會員／訂單資料開始，但保留 schema。
        for table in ("order_claims", "member_merge_requests", "point_transactions",
                      "point_wallet", "member_verification_challenges", "member_consents",
                      "member_identities", "member_points", "member_trips"):
            cur.execute(f"DELETE FROM {table}")
        cur.execute("UPDATE preorder_orders SET member_id=NULL")
        cur.execute("UPDATE neihai_preorders SET member_id=NULL")
        cur.execute("DELETE FROM preorder_passengers")
        cur.execute("DELETE FROM preorder_orders")
        cur.execute("DELETE FROM members")
        conn.commit(); cur.close(); conn.close()
        self.product_id = self._product()

    # ── 小工具 ──
    def _rows(self, sql, params=()):
        conn = self.A.get_db(); cur = conn.cursor(); cur.execute(sql, params)
        out = [dict(r) for r in cur.fetchall()]
        cur.close(); conn.close(); return out

    def _product(self):
        conn = self.A.get_db(); cur = conn.cursor()
        cur.execute("""INSERT INTO preorder_products (slug,name,min_people,capacity,counts_as_trip)
                       VALUES ('v1test','測試商品',2,50,TRUE)
                       ON CONFLICT (slug) DO UPDATE SET name=EXCLUDED.name RETURNING id""")
        pid = cur.fetchone()["id"]; conn.commit(); cur.close(); conn.close(); return pid

    def _member(self, name, email, phone):
        conn = self.A.get_db(); cur = conn.cursor()
        member_id, member_no = self.A.next_member_no(cur)
        cur.execute("""INSERT INTO members (id,member_no,name,phone,phone_normalized,email,consent_at)
                       VALUES (%s,%s,%s,%s,%s,%s,NOW())""",
                    (member_id, member_no, name, phone, phone, email))
        cur.execute("""INSERT INTO member_identities
                       (member_id,provider,provider_subject,email_normalized,verified_at)
                       VALUES (%s,'email',%s,%s,NOW())""", (member_id, email, email))
        conn.commit(); cur.close(); conn.close(); return member_id

    def _order(self, ref, email, phone, status="pending_departure", member_id=None):
        conn = self.A.get_db(); cur = conn.cursor()
        cur.execute("""INSERT INTO preorder_orders
            (product_id,departure_date,departure_time,booking_ref,contact_name,
             contact_phone,contact_email,passenger_count,status,member_id)
            VALUES (%s,'2026-02-01','09:00',%s,'客人',%s,%s,2,%s,%s) RETURNING id""",
                    (self.product_id, ref, phone, email, status, member_id))
        order_id = cur.fetchone()["id"]; conn.commit(); cur.close(); conn.close(); return order_id

    def _client(self, member_id=None):
        client = self.A.app.test_client()
        if member_id:
            with client.session_transaction() as sess:
                sess["member_id"] = member_id
        return client

    def _sync(self, ref, member_id, order_status):
        conn = self.A.get_db(); cur = conn.cursor()
        self.A._sync_completed_order_trip(cur, "preorder_order", ref, member_id,
                                          "測試行程", "2026-02-01", order_status, True)
        conn.commit(); cur.close(); conn.close()

    def _ledger(self, member_id):
        one = self._rows("SELECT points_balance FROM members WHERE id=%s", (member_id,))
        legacy = self._rows("SELECT COALESCE(SUM(delta),0) s FROM member_points WHERE member_id=%s",
                            (member_id,))[0]["s"]
        earned = self._rows("""SELECT COALESCE(SUM(delta),0) s FROM member_points
                               WHERE member_id=%s AND delta>0""", (member_id,))[0]["s"]
        txns = self._rows("SELECT COALESCE(SUM(points),0) s FROM point_transactions WHERE member_id=%s",
                          (member_id,))[0]["s"]
        wallet = self._rows("SELECT balance,lifetime_earned FROM point_wallet WHERE member_id=%s",
                            (member_id,))
        return {
            "members": int(one[0]["points_balance"]) if one else None,
            "member_points": int(legacy), "earned": int(earned), "point_transactions": int(txns),
            "wallet_balance": int(wallet[0]["balance"]) if wallet else None,
            "wallet_lifetime": int(wallet[0]["lifetime_earned"]) if wallet else None,
        }

    def _claim(self, client, ref, channel="email", verification_hint=None):
        if verification_hint is None:
            verification_hint = "a" if channel == "email" else "1111"
        response = client.post("/api/member/orders/claim/request",
                               json={"order_type": "preorder_order", "booking_ref": ref,
                                     "channel": channel,
                                     "verification_hint": verification_hint})
        return response, (response.get_json() or {})

    def _claim_hint_lock_keys(self, member_id, booking_ref):
        """Mirror the production lock-key derivation without changing production code."""
        secret = self.A.app.secret_key
        booking_key = self.V1._digest(secret, "order_claim_hint", booking_ref)
        member_lock = int.from_bytes(bytes.fromhex(self.V1._digest(
            secret, "claim_hint_member_lock", member_id))[:8], "big", signed=True)
        booking_lock = int.from_bytes(bytes.fromhex(self.V1._digest(
            secret, "claim_hint_booking_lock", booking_key))[:8], "big", signed=True)
        return member_lock, booking_lock, booking_key

    # ── 五、訂單認領 ──
    def test_legacy_register_login_member_center_and_line_binding(self):
        """正式站既有註冊→Email OTP→會員中心→LINE OA 綁定不可退化。"""
        delivered = []
        with mock.patch.object(
                self.A, "_send_member_code_email",
                side_effect=lambda member, code: (delivered.append((member["email"], code)),
                                                   (True, "test"))[1]):
            registered = self.A.app.test_client().post("/api/member/register", json={
                "name": "回歸會員", "phone": "0912345000",
                "email": "legacy-flow@example.com", "consent": True})
        self.assertEqual(registered.status_code, 200, registered.get_json())
        self.assertTrue((registered.get_json() or {}).get("verify_required"))
        self.assertEqual(delivered[-1][0], "legacy-flow@example.com")

        client = self.A.app.test_client()
        verified = client.post("/api/member/login/verify", json={
            "email": "legacy-flow@example.com", "code": delivered[-1][1]})
        self.assertEqual(verified.status_code, 200, verified.get_json())
        self.assertEqual(client.get("/api/member/me").status_code, 200)

        bind = client.post("/api/member/line-bind-code")
        self.assertEqual(bind.status_code, 200, bind.get_json())
        result = self.A._try_bind_member_line(
            "Ulegacy-regression", f"綁定會員 {bind.get_json()['code']}")
        self.assertIn("綁定完成", result)
        identities = client.get("/api/member/identities")
        self.assertEqual(identities.status_code, 200, identities.get_json())
        self.assertIn("line", {row["provider"] for row in identities.get_json()["identities"]})

    def test_admin_points_and_merge_regression(self):
        """P0 修改後，既有後台點數調整與會員合併仍可完成。"""
        source = self._member("來源", "admin-source@example.com", "0913000001")
        target = self._member("目標", "admin-target@example.com", "0913000002")
        client = self.A.app.test_client()
        admin_headers = ({"X-Admin-Key": os.environ["ADMIN_KEY"]}
                         if os.environ.get("ADMIN_KEY") else {})
        adjusted = client.post(f"/api/admin/members/{source}/points", json={
            "delta": 30, "source": "P0 regression"}, headers=admin_headers)
        self.assertEqual(adjusted.status_code, 200, adjusted.get_json())
        self.assertEqual(adjusted.get_json()["points_balance"], 30)
        merged = client.post("/api/admin/members/merge", json={
            "source_id": source, "target_id": target}, headers=admin_headers)
        self.assertEqual(merged.status_code, 200, merged.get_json())
        self.assertEqual(merged.get_json()["target_id"], target)
        self.assertEqual(self._rows("SELECT id FROM members WHERE id=%s", (source,)), [])
        self.assertEqual(self._ledger(target)["members"], 30)

    def test_claim_writes_member_id_only_after_correct_code(self):
        owner = self._member("甲", "a@example.com", "0911111111")
        self._order("CLAIM-1", "a@example.com", "0911111111", "completed")
        client = self._client(owner)
        response, payload = self._claim(client, "CLAIM-1")
        self.assertEqual(response.status_code, 200, payload)
        code = self.sent[-1][1]
        self.assertNotIn(code, str(payload), "API 回應不可包含 OTP")

        wrong = client.post("/api/member/orders/claim/verify",
                            json={"claim_id": payload["claim_id"], "code": "000000"})
        self.assertEqual(wrong.status_code, 401)
        self.assertIsNone(
            self._rows("SELECT member_id FROM preorder_orders WHERE booking_ref='CLAIM-1'")[0]["member_id"])

        ok = client.post("/api/member/orders/claim/verify",
                         json={"claim_id": payload["claim_id"], "code": code})
        self.assertEqual(ok.status_code, 200, ok.get_json())
        self.assertEqual(
            self._rows("SELECT member_id FROM preorder_orders WHERE booking_ref='CLAIM-1'")[0]["member_id"],
            owner)

    def test_expired_challenge_cannot_claim(self):
        owner = self._member("甲", "a@example.com", "0911111111")
        self._order("CLAIM-EXP", "a@example.com", "0911111111", "completed")
        client = self._client(owner)
        _, payload = self._claim(client, "CLAIM-EXP")
        code = self.sent[-1][1]
        conn = self.A.get_db(); cur = conn.cursor()
        cur.execute("""UPDATE member_verification_challenges SET expires_at=NOW()-INTERVAL '1 minute'
                       WHERE id=(SELECT challenge_id FROM order_claims WHERE id=%s)""",
                    (payload["claim_id"],))
        conn.commit(); cur.close(); conn.close()
        response = client.post("/api/member/orders/claim/verify",
                               json={"claim_id": payload["claim_id"], "code": code})
        self.assertEqual(response.status_code, 401)

    def test_claim_cannot_take_over_another_members_order(self):
        first = self._member("甲", "a@example.com", "0911111111")
        second = self._member("乙", "b@example.com", "0922222222")
        self._order("CLAIM-OWNED", "a@example.com", "0911111111", "completed", member_id=first)
        response, payload = self._claim(self._client(second), "CLAIM-OWNED")
        self.assertEqual(response.status_code, 400, payload)

    def test_claim_request_failures_are_uniform_and_require_contact_hint(self):
        owner = self._member("甲", "a@example.com", "0911111111")
        other = self._member("乙", "b@example.com", "0922222222")
        self._order("CLAIM-SECRET", "a@example.com", "0911111111", member_id=other)
        client = self._client(owner)
        responses = [
            self._claim(client, "DOES-NOT-EXIST", verification_hint="a")[0],
            self._claim(client, "CLAIM-SECRET", verification_hint="wrong")[0],
            self._claim(client, "CLAIM-SECRET", verification_hint="a")[0],
        ]
        self.assertEqual({response.status_code for response in responses}, {400})
        self.assertEqual(len({response.get_json()["error"] for response in responses}), 1)
        failures = self._rows("""SELECT COUNT(*) AS n FROM member_verification_challenges
                                 WHERE member_id=%s AND purpose='order_claim_hint_failure'""",
                              (owner,))[0]["n"]
        self.assertEqual(failures, 3, "不存在、已認領、比對碼錯誤都必須累計")

    def test_pending_claim_cannot_be_overwritten_by_another_member(self):
        first = self._member("甲", "a@example.com", "0911111111")
        second = self._member("乙", "b@example.com", "0922222222")
        self._order("CLAIM-PENDING", "a@example.com", "0911111111")
        first_response, first_payload = self._claim(self._client(first), "CLAIM-PENDING")
        self.assertEqual(first_response.status_code, 200, first_payload)
        second_response, _ = self._claim(self._client(second), "CLAIM-PENDING")
        self.assertEqual(second_response.status_code, 400)
        audit = self._rows("SELECT member_id FROM order_claims WHERE id=%s",
                           (first_payload["claim_id"],))[0]
        self.assertEqual(audit["member_id"], first)

    def test_expired_pending_claim_can_be_taken_over_and_keeps_old_challenge(self):
        first = self._member("甲", "a@example.com", "0911111111")
        second = self._member("乙", "b@example.com", "0922222222")
        self._order("CLAIM-EXPIRED-PENDING", "a@example.com", "0911111111")
        _, first_payload = self._claim(self._client(first), "CLAIM-EXPIRED-PENDING")
        old_challenge = self._rows("SELECT challenge_id FROM order_claims WHERE id=%s",
                                   (first_payload["claim_id"],))[0]["challenge_id"]
        conn = self.A.get_db(); cur = conn.cursor()
        cur.execute("""UPDATE member_verification_challenges
                       SET expires_at=NOW()-INTERVAL '1 minute' WHERE id=%s""",
                    (old_challenge,))
        conn.commit(); cur.close(); conn.close()

        response, payload = self._claim(self._client(second), "CLAIM-EXPIRED-PENDING")
        self.assertEqual(response.status_code, 200, payload)
        audit = self._rows("SELECT member_id,claimed_at,challenge_id FROM order_claims WHERE id=%s",
                           (first_payload["claim_id"],))[0]
        self.assertEqual(audit["member_id"], second)
        self.assertIsNone(audit["claimed_at"])
        self.assertNotEqual(audit["challenge_id"], old_challenge)
        self.assertEqual(self._rows(
            "SELECT COUNT(*) AS n FROM member_verification_challenges WHERE id=%s",
            (old_challenge,))[0]["n"], 1, "舊 challenge 必須保留作為稽核紀錄")

    def test_used_pending_claim_can_be_taken_over(self):
        first = self._member("甲", "a@example.com", "0911111111")
        second = self._member("乙", "b@example.com", "0922222222")
        self._order("CLAIM-USED-PENDING", "a@example.com", "0911111111")
        _, first_payload = self._claim(self._client(first), "CLAIM-USED-PENDING")
        conn = self.A.get_db(); cur = conn.cursor()
        cur.execute("""UPDATE member_verification_challenges SET used_at=NOW()
                       WHERE id=(SELECT challenge_id FROM order_claims WHERE id=%s)""",
                    (first_payload["claim_id"],))
        conn.commit(); cur.close(); conn.close()
        response, payload = self._claim(self._client(second), "CLAIM-USED-PENDING")
        self.assertEqual(response.status_code, 200, payload)
        self.assertEqual(self._rows("SELECT member_id FROM order_claims WHERE id=%s",
                                    (first_payload["claim_id"],))[0]["member_id"], second)

    def test_same_member_can_refresh_a_pending_claim(self):
        member_id = self._member("甲", "a@example.com", "0911111111")
        self._order("CLAIM-REFRESH", "a@example.com", "0911111111")
        client = self._client(member_id)
        _, first_payload = self._claim(client, "CLAIM-REFRESH")
        first_challenge = self._rows("SELECT challenge_id FROM order_claims WHERE id=%s",
                                     (first_payload["claim_id"],))[0]["challenge_id"]
        second_response, second_payload = self._claim(client, "CLAIM-REFRESH")
        self.assertEqual(second_response.status_code, 200, second_payload)
        refreshed = self._rows("SELECT id,challenge_id FROM order_claims WHERE id=%s",
                               (first_payload["claim_id"],))[0]
        self.assertEqual(refreshed["id"], first_payload["claim_id"])
        self.assertNotEqual(refreshed["challenge_id"], first_challenge)

    def test_completed_claim_cannot_be_overwritten(self):
        first = self._member("甲", "a@example.com", "0911111111")
        second = self._member("乙", "b@example.com", "0922222222")
        self._order("CLAIM-COMPLETE", "a@example.com", "0911111111")
        first_client = self._client(first)
        _, payload = self._claim(first_client, "CLAIM-COMPLETE")
        first_client.post("/api/member/orders/claim/verify", json={
            "claim_id": payload["claim_id"], "code": self.sent[-1][1]})
        blocked, _ = self._claim(self._client(second), "CLAIM-COMPLETE")
        self.assertEqual(blocked.status_code, 400)
        audit = self._rows("SELECT member_id,claimed_at FROM order_claims WHERE id=%s",
                           (payload["claim_id"],))[0]
        self.assertEqual(audit["member_id"], first)
        self.assertIsNotNone(audit["claimed_at"])

    def test_claim_hint_failures_rate_limit_member_before_correct_attempt(self):
        member_id = self._member("甲", "a@example.com", "0911111111")
        self._order("CLAIM-MEMBER-LIMIT", "a@example.com", "0911111111")
        client = self._client(member_id)
        for _ in range(10):
            response, _ = self._claim(
                client, "CLAIM-MEMBER-LIMIT", verification_hint="wrong")
            self.assertEqual(response.status_code, 400)
        before_rows = self._rows("SELECT COUNT(*) AS n FROM member_verification_challenges")[0]["n"]
        before_sent = len(self.sent)
        blocked, payload = self._claim(client, "CLAIM-MEMBER-LIMIT")
        self.assertEqual(blocked.status_code, 429, payload)
        self.assertEqual(payload["error"], "嘗試次數過多，請稍後再試")
        self.assertEqual(
            self._rows("SELECT COUNT(*) AS n FROM member_verification_challenges")[0]["n"],
            before_rows, "被限流後不得建立 challenge")
        self.assertEqual(len(self.sent), before_sent, "被限流後不得寄信")

    def test_claim_hint_failures_rate_limit_booking_across_members(self):
        first = self._member("甲", "a@example.com", "0911111111")
        second = self._member("乙", "b@example.com", "0922222222")
        third = self._member("丙", "c@example.com", "0933333333")
        self._order("CLAIM-BOOKING-LIMIT", "a@example.com", "0911111111")
        for client in (self._client(first), self._client(second)):
            for _ in range(5):
                response, _ = self._claim(
                    client, "CLAIM-BOOKING-LIMIT", verification_hint="wrong")
                self.assertEqual(response.status_code, 400)
        blocked, payload = self._claim(self._client(third), "CLAIM-BOOKING-LIMIT")
        self.assertEqual(blocked.status_code, 429, payload)

    def test_concurrent_claim_hint_failures_cannot_bypass_member_limit(self):
        for round_no in range(5):
            member_id = self._member(
                f"甲{round_no}", f"same-member-{round_no}@example.com", f"0911111{round_no:03d}")
            booking_ref = f"CLAIM-CONCURRENT-MEMBER-{round_no}"
            self._order(booking_ref, "owner@example.com", "0911111111")
            barrier = threading.Barrier(30)

            def guess_wrong(_):
                client = self._client(member_id)
                barrier.wait(timeout=30)
                return self._claim(
                    client, booking_ref, verification_hint="wrong")[0].status_code

            with concurrent.futures.ThreadPoolExecutor(max_workers=30) as executor:
                statuses = list(executor.map(guess_wrong, range(30)))

            self.assertEqual(statuses.count(400), 10, (round_no, statuses))
            self.assertEqual(statuses.count(429), 20, (round_no, statuses))
            failures = self._rows("""SELECT COUNT(*) AS n
                                     FROM member_verification_challenges
                                     WHERE member_id=%s
                                       AND purpose='order_claim_hint_failure'""",
                                  (member_id,))[0]["n"]
            self.assertLessEqual(failures, 10)

    def test_concurrent_claim_hint_failures_cannot_bypass_booking_limit(self):
        for round_no in range(5):
            members = [
                self._member(f"會員{round_no}-{i}", f"member-{round_no}-{i}@example.com",
                             f"09{round_no:01d}{i:07d}")
                for i in range(30)
            ]
            booking_ref = f"CLAIM-CONCURRENT-BOOKING-{round_no}"
            self._order(booking_ref, "owner@example.com", "0911111111")
            barrier = threading.Barrier(30)

            def guess_wrong(member_id):
                client = self._client(member_id)
                barrier.wait(timeout=30)
                return self._claim(
                    client, booking_ref, verification_hint="wrong")[0].status_code

            with concurrent.futures.ThreadPoolExecutor(max_workers=30) as executor:
                statuses = list(executor.map(guess_wrong, members))

            self.assertEqual(statuses.count(400), 10, (round_no, statuses))
            self.assertEqual(statuses.count(429), 20, (round_no, statuses))
            booking_key = self._claim_hint_lock_keys(members[0], booking_ref)[2]
            failure_summary = self._rows("""SELECT COUNT(*) AS n,
                                            COUNT(DISTINCT destination_normalized) AS booking_keys
                                     FROM member_verification_challenges
                                     WHERE purpose='order_claim_hint_failure'
                                       AND destination_normalized=%s""", (booking_key,))[0]
            self.assertEqual(failure_summary["booking_keys"], 1)
            self.assertLessEqual(failure_summary["n"], 10)

    def test_claim_hint_member_and_booking_advisory_locks_block_requests(self):
        for scope in ("member", "booking"):
            with self.subTest(scope=scope):
                suffix = scope.upper()
                member_id = self._member(
                    f"鎖{scope}", f"lock-{scope}@example.com",
                    "0977000001" if scope == "member" else "0977000002")
                booking_ref = f"CLAIM-LOCK-{suffix}"
                self._order(booking_ref, "owner@example.com", "0911111111")
                member_lock, booking_lock, _ = self._claim_hint_lock_keys(
                    member_id, booking_ref)
                held_lock = member_lock if scope == "member" else booking_lock
                lock_conn = self.A.get_db(); lock_cur = lock_conn.cursor()
                lock_cur.execute("SELECT pg_advisory_xact_lock(%s)", (held_lock,))
                started = threading.Event()
                finished = threading.Event()

                def guess_wrong():
                    started.set()
                    try:
                        return self._claim(
                            self._client(member_id), booking_ref,
                            verification_hint="wrong")[0].status_code
                    finally:
                        finished.set()

                with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                    future = executor.submit(guess_wrong)
                    try:
                        self.assertTrue(started.wait(timeout=5))
                        self.assertFalse(
                            finished.wait(timeout=1.0),
                            f"{scope} advisory lock did not block the request")
                    finally:
                        lock_conn.rollback(); lock_cur.close(); lock_conn.close()
                    self.assertEqual(future.result(timeout=5), 400)
                    self.assertTrue(finished.is_set())

    def test_concurrent_correct_claim_requests_create_only_one_pending_claim(self):
        members = [
            self._member(f"會員{i}", f"claimant{i}@example.com", f"08{i:08d}")
            for i in range(3)
        ]
        booking_ref = "CLAIM-CONCURRENT-CORRECT"
        order_id = self._order(booking_ref, "owner@example.com", "0911111111")
        barrier = threading.Barrier(3)

        def claim(member_id):
            client = self._client(member_id)
            barrier.wait(timeout=30)
            return self._claim(client, booking_ref, verification_hint="own")[0].status_code

        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            statuses = list(executor.map(claim, members))

        self.assertEqual(statuses.count(200), 1, statuses)
        self.assertEqual(statuses.count(400), 2, statuses)
        claims = self._rows("""SELECT member_id FROM order_claims
                              WHERE order_type='preorder_order' AND order_id=%s""",
                            (order_id,))
        self.assertEqual(len(claims), 1)
        self.assertIn(claims[0]["member_id"], members)
        challenges = self._rows("""SELECT id FROM member_verification_challenges
                                  WHERE purpose='order_claim'""")
        self.assertEqual(len(challenges), 1, "losing claims must roll back their challenges")
        self.assertEqual(
            len([message for message in self.sent if message[2] == "order_claim"]), 1,
            "only the winning claim may send a verification email")

    def test_concurrent_claim_verification_credits_only_once(self):
        owner = self._member("甲", "a@example.com", "0911111111")
        self._order("CLAIM-CONCURRENT-VERIFY", "a@example.com", "0911111111", "completed")
        _, payload = self._claim(self._client(owner), "CLAIM-CONCURRENT-VERIFY")
        code = self.sent[-1][1]
        barrier = threading.Barrier(6)

        def verify(_):
            client = self._client(owner)
            barrier.wait(timeout=30)
            return client.post("/api/member/orders/claim/verify", json={
                "claim_id": payload["claim_id"], "code": code}).status_code

        with concurrent.futures.ThreadPoolExecutor(max_workers=6) as executor:
            statuses = list(executor.map(verify, range(6)))

        self.assertEqual(statuses.count(200), 1, statuses)
        self.assertEqual(statuses.count(404), 5, statuses)
        trips = self._rows("SELECT id FROM member_trips WHERE member_id=%s", (owner,))
        self.assertEqual(len(trips), 1)
        self.assertEqual(self._ledger(owner)["member_points"], self.A.points_per_trip())

    def test_concurrent_takeover_of_expired_pending_claim_has_one_winner(self):
        original = self._member("原始", "original@example.com", "0911111111")
        contenders = [
            self._member("接手一", "takeover-one@example.com", "0922222222"),
            self._member("接手二", "takeover-two@example.com", "0933333333"),
        ]
        booking_ref = "CLAIM-CONCURRENT-TAKEOVER"
        order_id = self._order(booking_ref, "owner@example.com", "0911111111")
        _, original_payload = self._claim(
            self._client(original), booking_ref, verification_hint="own")
        conn = self.A.get_db(); cur = conn.cursor()
        cur.execute("""UPDATE member_verification_challenges
                       SET expires_at=NOW()-INTERVAL '1 minute'
                       WHERE id=(SELECT challenge_id FROM order_claims WHERE id=%s)""",
                    (original_payload["claim_id"],))
        conn.commit(); cur.close(); conn.close()
        barrier = threading.Barrier(2)

        def take_over(member_id):
            client = self._client(member_id)
            barrier.wait(timeout=30)
            return self._claim(
                client, booking_ref, verification_hint="own")[0].status_code

        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            statuses = list(executor.map(take_over, contenders))

        self.assertEqual(statuses.count(200), 1, statuses)
        self.assertEqual(statuses.count(400), 1, statuses)
        claims = self._rows("""SELECT member_id FROM order_claims
                              WHERE order_type='preorder_order' AND order_id=%s""", (order_id,))
        self.assertEqual(len(claims), 1)
        self.assertIn(claims[0]["member_id"], contenders)

    def test_claim_hint_failure_window_expires_after_one_hour(self):
        member_id = self._member("甲", "a@example.com", "0911111111")
        self._order("CLAIM-WINDOW", "a@example.com", "0911111111")
        client = self._client(member_id)
        for _ in range(10):
            self._claim(client, "CLAIM-WINDOW", verification_hint="wrong")
        conn = self.A.get_db(); cur = conn.cursor()
        cur.execute("""UPDATE member_verification_challenges
                       SET created_at=NOW()-INTERVAL '61 minutes'
                       WHERE purpose='order_claim_hint_failure' AND member_id=%s""",
                    (member_id,))
        conn.commit(); cur.close(); conn.close()
        response, payload = self._claim(client, "CLAIM-WINDOW")
        self.assertEqual(response.status_code, 200, payload)

    def test_repeated_claim_does_not_double_credit(self):
        owner = self._member("甲", "a@example.com", "0911111111")
        self._order("CLAIM-DUP", "a@example.com", "0911111111", "completed")
        client = self._client(owner)
        _, payload = self._claim(client, "CLAIM-DUP")
        code = self.sent[-1][1]
        client.post("/api/member/orders/claim/verify",
                    json={"claim_id": payload["claim_id"], "code": code})
        after_first = self._ledger(owner)
        client.post("/api/member/orders/claim/verify",
                    json={"claim_id": payload["claim_id"], "code": code})
        self.assertEqual(self._ledger(owner)["member_points"], after_first["member_points"])
        self.assertEqual(after_first["member_points"], self.A.points_per_trip())

    def test_matching_contact_phone_alone_never_assigns_an_order(self):
        member_id = self._member("甲", "a@example.com", "0911111111")
        self._order("NO-AUTO", "a@example.com", "0911111111", "completed")
        self._sync("NO-AUTO", None, "completed")
        self.assertEqual(self._ledger(member_id)["member_points"], 0)

    # ── 六、點數帳本 ──
    def test_point_ledger_state_sequences(self):
        member_id = self._member("甲", "a@example.com", "0911111111")
        self._order("LEDGER-1", "a@example.com", "0911111111", "completed", member_id=member_id)
        per_trip = self.A.points_per_trip()

        self._sync("LEDGER-1", member_id, "pending_departure")
        self.assertEqual(self._ledger(member_id)["member_points"], 0, "未完成不得入點")

        self._sync("LEDGER-1", member_id, "completed")
        self.assertEqual(self._ledger(member_id)["member_points"], per_trip)

        self._sync("LEDGER-1", member_id, "completed")
        self.assertEqual(self._ledger(member_id)["member_points"], per_trip, "重跑不得重複入點")

        self._sync("LEDGER-1", member_id, "cancelled")
        self.assertEqual(self._ledger(member_id)["member_points"], 0)

        history = [(r["points"], r["transaction_type"]) for r in self._rows(
            "SELECT points,transaction_type FROM point_transactions WHERE member_id=%s ORDER BY id",
            (member_id,))]
        self.assertEqual(history, [(per_trip, "earn"), (-per_trip, "reversal")],
                         "沖銷必須是新的負向交易，不可刪改歷史")

    def test_wallet_stays_consistent_when_reversal_pushes_balance_negative(self):
        """兌換完點數後訂單才被取消：餘額真的會變負，三張表必須一起變負。"""
        member_id = self._member("甲", "a@example.com", "0911111111")
        self._order("NEG-1", "a@example.com", "0911111111", "completed", member_id=member_id)
        self._sync("NEG-1", member_id, "completed")
        per_trip = self.A.points_per_trip()
        conn = self.A.get_db(); cur = conn.cursor()
        cur.execute("""INSERT INTO member_points (member_id,delta,source)
                       VALUES (%s,%s,'兌換折抵') RETURNING id""", (member_id, -per_trip))
        legacy_id = cur.fetchone()["id"]
        cur.execute("""INSERT INTO point_transactions
                       (member_id,transaction_type,points,reason,idempotency_key)
                       VALUES (%s,'manual_adjustment',%s,'兌換折抵',%s)""",
                    (member_id, -per_trip, f"legacy-member-point:{legacy_id}"))
        self.A.recalculate_member(cur, member_id)
        conn.commit(); cur.close(); conn.close()
        self.assertEqual(self._ledger(member_id)["member_points"], 0)

        self._sync("NEG-1", member_id, "cancelled")
        after = self._ledger(member_id)
        self.assertEqual(after["member_points"], -per_trip)
        self.assertEqual(after["members"], -per_trip)
        self.assertEqual(after["point_transactions"], -per_trip)
        self.assertEqual(after["wallet_balance"], -per_trip,
                         "point_wallet 不可把負餘額 clamp 成 0")

    def test_wallet_lifetime_earned_matches_the_ledger_after_reinit(self):
        """賺→兌換→再賺：lifetime_earned 必須是累積獲得，且重跑 init_db 不會跳動。"""
        member_id = self._member("甲", "a@example.com", "0911111111")
        per_trip = self.A.points_per_trip()
        self._order("LIFE-1", "a@example.com", "0911111111", "completed", member_id=member_id)
        self._sync("LIFE-1", member_id, "completed")
        conn = self.A.get_db(); cur = conn.cursor()
        cur.execute("""INSERT INTO member_points (member_id,delta,source)
                       VALUES (%s,%s,'兌換折抵') RETURNING id""", (member_id, -per_trip))
        legacy_id = cur.fetchone()["id"]
        cur.execute("""INSERT INTO point_transactions
                       (member_id,transaction_type,points,reason,idempotency_key)
                       VALUES (%s,'manual_adjustment',%s,'兌換折抵',%s)""",
                    (member_id, -per_trip, f"legacy-member-point:{legacy_id}"))
        self.A.recalculate_member(cur, member_id)
        conn.commit(); cur.close(); conn.close()
        self._order("LIFE-2", "a@example.com", "0911111111", "completed", member_id=member_id)
        self._sync("LIFE-2", member_id, "completed")

        before = self._ledger(member_id)
        self.assertEqual(before["wallet_lifetime"], before["earned"], "應等於帳本正向合計")
        self.A.init_db()
        self.assertEqual(self._ledger(member_id)["wallet_lifetime"], before["wallet_lifetime"],
                         "重跑 init_db 不可改變 lifetime_earned")

    # ── 七、安全合併 ──
    def test_merge_needs_otp_on_the_source_accounts_verified_email(self):
        target = self._member("甲", "a@example.com", "0911111111")
        source = self._member("乙", "b@example.com", "0922222222")
        client = self._client(target)
        response = client.post("/api/member/merge/request", json={"source_email": "b@example.com"})
        payload = response.get_json()
        self.assertNotIn("request_id", payload, "回應不可洩漏是否真的建立了合併要求")
        self.assertEqual(self.sent[-1][0], "b@example.com", "驗證碼必須寄到來源帳號的已驗證 Email")
        wrong = client.post("/api/member/merge/confirm", json={"code": "000000"})
        self.assertEqual(wrong.status_code, 401)
        ok = client.post("/api/member/merge/confirm", json={"code": self.sent[-1][1]})
        self.assertEqual(ok.status_code, 200, ok.get_json())
        row = self._rows("SELECT is_active,merged_into_member_id FROM members WHERE id=%s", (source,))[0]
        self.assertFalse(row["is_active"])
        self.assertEqual(row["merged_into_member_id"], target)

    def test_merged_source_session_can_no_longer_use_member_apis(self):
        """合併前就登入的舊分頁不可以繼續操作已被併掉的帳號。"""
        target = self._member("甲", "a@example.com", "0911111111")
        source = self._member("乙", "b@example.com", "0922222222")
        stale = self._client(source)          # 來源帳號合併前就已登入
        client = self._client(target)
        payload = client.post("/api/member/merge/request",
                              json={"source_email": "b@example.com"}).get_json()
        client.post("/api/member/merge/confirm", json={"code": self.sent[-1][1]})

        for method, path, body in (("get", "/api/member/me", None),
                                   ("get", "/api/member/identities", None),
                                   ("get", "/api/member/orders", None),
                                   ("post", "/api/member/consents",
                                    {"consent_type": "marketing", "granted": True})):
            response = getattr(stale, method)(path, json=body)
            self.assertEqual(response.status_code, 401, path)
        self.assertEqual(
            self._rows("SELECT COUNT(*) n FROM member_consents WHERE member_id=%s", (source,))[0]["n"],
            0, "合併後的來源帳號不可再被寫入資料")

    def test_merge_request_response_does_not_reveal_account_existence(self):
        target = self._member("甲", "a@example.com", "0911111111")
        self._member("乙", "b@example.com", "0922222222")
        client = self._client(target)
        missing = client.post("/api/member/merge/request",
                              json={"source_email": "missing@example.com"})
        existing = client.post("/api/member/merge/request",
                               json={"source_email": "b@example.com"})
        self.assertEqual(missing.status_code, existing.status_code)
        self.assertEqual(missing.get_json(), existing.get_json())

    def test_merge_preserves_pending_claim_audit_and_fk_chain(self):
        target = self._member("目標", "target@example.com", "0911111111")
        source = self._member("來源", "source@example.com", "0922222222")
        self._order("CLAIM-AUDIT", "source@example.com", "0922222222")
        claim_response, claim_payload = self._claim(
            self._client(source), "CLAIM-AUDIT", verification_hint="sou")
        self.assertEqual(claim_response.status_code, 200, claim_payload)

        client = self._client(target)
        client.post("/api/member/merge/request", json={"source_email": "source@example.com"})
        merged = client.post("/api/member/merge/confirm", json={"code": self.sent[-1][1]})
        self.assertEqual(merged.status_code, 200, merged.get_json())
        audit = self._rows("""SELECT c.member_id,v.member_id AS challenge_member_id
                              FROM order_claims c JOIN member_verification_challenges v
                                ON v.id=c.challenge_id WHERE c.id=%s""",
                           (claim_payload["claim_id"],))[0]
        self.assertEqual(audit, {"member_id": target, "challenge_member_id": target})

    def test_consent_granted_requires_a_real_json_boolean(self):
        member_id = self._member("甲", "a@example.com", "0911111111")
        client = self._client(member_id)
        malformed = client.post("/api/member/consents", json={
            "consent_type": "marketing", "granted": "false"})
        self.assertEqual(malformed.status_code, 400)
        accepted = client.post("/api/member/consents", json={
            "consent_type": "marketing", "granted": False})
        self.assertEqual(accepted.status_code, 200, accepted.get_json())
        row = self._rows("""SELECT granted FROM member_consents
                            WHERE member_id=%s ORDER BY id DESC LIMIT 1""", (member_id,))[0]
        self.assertFalse(row["granted"])

    # ── 二、社群註冊 ──
    def test_oauth_signup_requires_a_verified_email(self):
        """不可拿別人的信箱＋自己的社群帳號開戶（account pre-hijacking）。"""
        client = self.A.app.test_client()
        with client.session_transaction() as sess:
            sess["pending_oauth_identity"] = {"provider": "google", "subject": "sub-unverified",
                                              "email": "", "name": "攻擊者", "at": int(time.time())}
        body = {"name": "攻擊者", "phone": "0955555555",
                "email": "victim@example.com", "consent": True}
        first = client.post("/api/member/oauth/complete", json=body)
        self.assertTrue((first.get_json() or {}).get("verify_required"))
        self.assertEqual(
            self._rows("SELECT id FROM members WHERE LOWER(email)='victim@example.com'"), [],
            "未通過 Email 驗證前不得建立會員")
        self.assertEqual(self.sent[-1][0], "victim@example.com")

        wrong = client.post("/api/member/oauth/complete", json={**body, "code": "000000"})
        self.assertEqual(wrong.status_code, 401)
        ok = client.post("/api/member/oauth/complete", json={**body, "code": self.sent[-1][1]})
        self.assertEqual(ok.status_code, 201, ok.get_json())
        providers = sorted(r["provider"] for r in self._rows(
            "SELECT provider FROM member_identities WHERE member_id=%s",
            (ok.get_json()["member"]["id"],)))
        self.assertEqual(providers, ["email", "google"])

    def test_oauth_signup_does_not_disclose_whether_a_phone_is_a_member(self):
        self._member("既有會員", "exists@example.com", "0966666666")
        client = self.A.app.test_client()
        with client.session_transaction() as sess:
            sess["pending_oauth_identity"] = {"provider": "google", "subject": "sub-probe",
                                              "email": "", "name": "探測者", "at": int(time.time())}
        response = client.post("/api/member/oauth/complete",
                               json={"name": "探測者", "phone": "0966666666",
                                     "email": "probe@example.com", "consent": True})
        self.assertNotEqual(response.status_code, 409,
                            "不可在通過 Email 驗證前就洩漏這支手機是不是會員")

    def test_provider_verified_email_skips_the_extra_otp(self):
        client = self.A.app.test_client()
        with client.session_transaction() as sess:
            sess["pending_oauth_identity"] = {"provider": "google", "subject": "sub-verified",
                                              "email": "verified@example.com", "name": "阿明",
                                              "at": int(time.time())}
        response = client.post("/api/member/oauth/complete",
                               json={"name": "阿明", "phone": "0912000333",
                                     "email": "typed@example.com", "consent": True})
        self.assertEqual(response.status_code, 201, response.get_json())
        self.assertEqual(response.get_json()["member"]["email"], "verified@example.com",
                         "應採用 provider 驗證過的 Email，忽略前端自填值")
        self.assertEqual(self.sent, [], "這條路徑不需要再寄一次 OTP")

    def test_provider_email_never_auto_links_an_existing_member(self):
        """即使 provider 驗證過同一 Email，也不可據此認領既有本站帳號。"""
        existing = self._member("既有會員", "existing@example.com", "0912888999")
        client = self.A.app.test_client()
        with client.session_transaction() as sess:
            sess["pending_oauth_identity"] = {
                "provider": "google", "subject": "attacker-subject",
                "email": "existing@example.com", "name": "攻擊者", "at": int(time.time())}
        response = client.post("/api/member/oauth/complete", json={
            "name": "攻擊者", "phone": "0955111222",
            "email": "existing@example.com", "consent": True})
        self.assertEqual(response.status_code, 409, response.get_json())
        self.assertEqual(self._rows(
            "SELECT id FROM member_identities WHERE provider='google' AND provider_subject=%s",
            ("attacker-subject",)), [])
        self.assertEqual(self._rows(
            "SELECT id FROM members WHERE id=%s", (existing,))[0]["id"], existing)

    def test_line_binding_needs_recent_email_otp_and_uses_verified_sub(self):
        member_id = self._member("LINE 綁定", "line-bind@example.com", "0912777000")
        client = self._client(member_id)

        def run_callback():
            started = client.get("/api/member/oauth/line/start")
            self.assertEqual(started.status_code, 302)
            with client.session_transaction() as sess:
                saved = dict(sess["member_oauth_state"])

            def oauth_response(url, data):
                if url.endswith("/token"):
                    return {"id_token": "signed.line.jwt", "access_token": "unused"}
                return {
                    "iss": "https://access.line.me", "aud": "test-line-channel",
                    "nonce": saved["nonce"], "exp": int(time.time()) + 300,
                    "sub": "Uverified-immutable", "name": "LINE 使用者",
                    "email": "provider@example.com",
                }

            with mock.patch.object(self.V1, "_post_form", side_effect=oauth_response):
                return client.get("/api/member/oauth/line/callback", query_string={
                    "state": saved["state"], "code": "authorization-code"})

        with mock.patch.dict(os.environ, {
                "LINE_OAUTH_CLIENT_ID": "test-line-channel",
                "LINE_OAUTH_CLIENT_SECRET": "test-line-secret"}):
            rejected = run_callback()
            self.assertIn("oauth_error=email_otp_required", rejected.location)
            self.assertEqual(self._rows(
                "SELECT id FROM member_identities WHERE provider='line' AND provider_subject=%s",
                ("Uverified-immutable",)), [])

            with client.session_transaction() as sess:
                sess["member_email_otp_proof"] = {
                    "member_id": member_id, "at": int(time.time())}
            bound = run_callback()
            self.assertIn("oauth=bound", bound.location)
            with client.session_transaction() as sess:
                self.assertNotIn("member_email_otp_proof", sess,
                                 "step-up proof 綁定成功後必須一次性消耗")

        identity = self._rows("""SELECT member_id,email_normalized FROM member_identities
                                 WHERE provider='line' AND provider_subject=%s""",
                              ("Uverified-immutable",))[0]
        self.assertEqual(identity["member_id"], member_id)
        self.assertIsNone(identity["email_normalized"],
                          "LINE email claim 預設不得視為本站已驗證 Email")

    # ── 四、OTP 上限 ──
    def test_challenge_has_attempt_and_request_limits(self):
        member_id = self._member("甲", "a@example.com", "0911111111")
        self._order("LIMIT-1", "a@example.com", "0911111111", "completed")
        client = self._client(member_id)
        _, payload = self._claim(client, "LIMIT-1")
        real_code = self.sent[-1][1]
        for _ in range(5):
            client.post("/api/member/orders/claim/verify",
                        json={"claim_id": payload["claim_id"], "code": "000000"})
        blocked = client.post("/api/member/orders/claim/verify",
                              json={"claim_id": payload["claim_id"], "code": real_code})
        self.assertEqual(blocked.status_code, 401, "超過嘗試上限後正確的驗證碼也必須失效")

        statuses = [self._claim(client, "LIMIT-1")[0].status_code for _ in range(6)]
        self.assertIn(429, statuses, "驗證碼要求必須有頻率上限")

    def test_phone_otp_rate_limit_is_bound_to_destination_across_members(self):
        statuses = []
        for index in range(6):
            member_id = self._member(
                f"會員{index}", f"phone-limit-{index}@example.com", f"09880000{index:02d}")
            response = self._client(member_id).post(
                "/api/member/phone/request", json={"phone": "0977555666"})
            statuses.append(response.status_code)
        self.assertEqual(statuses[:5], [200] * 5)
        self.assertEqual(statuses[5], 429)


if __name__ == "__main__":
    unittest.main()


class OAuthEntryVisibilityTests(unittest.TestCase):
    """憑證還沒設定時，前台不可以顯示社群登入入口。

    按鈕點下去只會拿到 503，等於把使用者送進死路；而且 V1 的社群登入
    尚未完成端到端驗證，入口不該先對外開放。
    """

    def setUp(self):
        app.config.update(TESTING=True)
        self.client = app.test_client()

    def test_providers_endpoint_reports_unconfigured_without_leaking_secrets(self):
        response = self.client.get("/api/member/oauth/providers")
        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertTrue(payload["ok"])
        # 未設定憑證的環境一律回 False，且 facebook 永遠是 False（V1 未啟用）。
        self.assertIn("line", payload["providers"])
        self.assertIn("google", payload["providers"])
        self.assertFalse(payload["providers"]["facebook"])
        body = response.get_data(as_text=True)
        for leaked in ("CLIENT_SECRET", "client_secret"):
            self.assertNotIn(leaked, body)

    def test_member_page_hides_oauth_entries_until_server_confirms(self):
        page = (ROOT / "member.html").read_text(encoding="utf-8")
        # 三個入口（註冊、登入、儀表板綁定）都必須預設隱藏。
        self.assertEqual(page.count('class="oauth-block" hidden'), 3)
        self.assertIn("/api/member/oauth/providers", page)
        # 必須是「確認後才顯示」，不是「先顯示再隱藏」。
        self.assertIn("el.hidden=false", page)
