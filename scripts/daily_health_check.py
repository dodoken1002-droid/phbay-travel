"""潮旅正式站每日健康檢查。

不帶憑證也能檢查首頁、行程、五語、資料庫與部署版本；設定 GA4、GSC、
LINE 憑證後會自動啟用深度檢查。輸出 JSON 供 GitHub Actions 建立 P0 閘門。
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import hmac
import json
import os
import sys
import time
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SITE = "https://www.phbay.info"
LANGS = ("zh-tw", "en", "ja", "ko", "zh-cn")


@dataclass
class Check:
    key: str
    label: str
    status: str
    summary: str
    details: dict | None = None


def check(key, label, status, summary, **details):
    return Check(key, label, status, summary, details or None)


def fetch(url, *, method="GET", data=None, headers=None, timeout=20):
    request = urllib.request.Request(url, data=data, method=method, headers=headers or {})
    started = time.monotonic()
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.status, response.read(), round((time.monotonic() - started) * 1000)
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read(), round((time.monotonic() - started) * 1000)


def fetch_json(url, **kwargs):
    status, body, elapsed = fetch(url, **kwargs)
    try:
        payload = json.loads(body.decode("utf-8"))
    except Exception:
        payload = None
    return status, payload, elapsed


def _translated_post():
    candidates = sorted((ROOT / "content" / "posts").glob("*.json"), reverse=True)
    needed = set(LANGS) - {"zh-tw"}
    for path in candidates:
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        if needed.issubset((payload.get("i18n") or {}).keys()):
            return payload
    return None


def public_checks(site, expected_sha=""):
    results = []
    try:
        code, body, ms = fetch(f"{site}/")
        text = body.decode("utf-8", "replace")
        ok = code == 200 and "潮旅國際旅行社" in text
        results.append(check("homepage", "首頁", "ok" if ok else "critical",
                             f"HTTP {code}，{ms} ms" if ok else f"HTTP {code} 或品牌內容缺失",
                             http_status=code, latency_ms=ms))
    except Exception as exc:
        results.append(check("homepage", "首頁", "critical", str(exc)))

    try:
        code, payload, ms = fetch_json(f"{site}/api/tours")
        groups = (payload or {}).get("tours") or {}
        count = sum(len(rows) for rows in groups.values() if isinstance(rows, list))
        tour_path = os.environ.get("HEALTH_TOUR_PATH", "/preorder/festival")
        page_code, page_body, page_ms = fetch(f"{site}{tour_path}")
        page_ok = page_code == 200 and len(page_body) > 1000
        ok = code == 200 and (payload or {}).get("ok") and count > 0 and page_ok
        results.append(check("tours", "行程頁／行程 API", "ok" if ok else "critical",
                             f"行程頁 HTTP {page_code}；API HTTP {code}，{count} 筆啟用行程",
                             page_path=tour_path, page_http_status=page_code,
                             page_latency_ms=page_ms, api_http_status=code,
                             tour_count=count, api_latency_ms=ms))
    except Exception as exc:
        results.append(check("tours", "行程頁／行程 API", "critical", str(exc)))

    post = _translated_post()
    if not post:
        results.append(check("i18n", "五語頁", "critical", "找不到含五語翻譯的文章基準"))
    else:
        failures = []
        observations = {}
        slug = post["slug"]
        titles = {"zh-tw": post.get("title", "")}
        titles.update({lang: row.get("title", "") for lang, row in post["i18n"].items()})
        for lang in LANGS:
            try:
                code, body, _ = fetch(f"{site}/blog/{slug}?lang={lang}")
                expected = titles.get(lang, "")[:10]
                matched = bool(expected) and expected in body.decode("utf-8", "replace")
                observations[lang] = {"http_status": code, "title_matched": matched}
                if code != 200 or not matched:
                    failures.append(lang)
            except Exception as exc:
                observations[lang] = {"error": str(exc)}
                failures.append(lang)
        results.append(check("i18n", "五語頁", "critical" if failures else "ok",
                             f"{slug}：" + (f"失敗語言 {', '.join(failures)}" if failures else "五語皆為 200 且標題正確"),
                             slug=slug, languages=observations))

    try:
        code, payload, ms = fetch_json(f"{site}/api/health")
        healthy = code == 200 and (payload or {}).get("ok") is True
        release = (payload or {}).get("release_sha", "")
        if not healthy:
            status, summary = "critical", f"HTTP {code}，資料庫或 contacts 表異常"
        elif expected_sha and release and not expected_sha.startswith(release) and not release.startswith(expected_sha):
            status, summary = "critical", f"正式站版本 {release[:7]} 不等於 main {expected_sha[:7]}"
        elif expected_sha and not release:
            status, summary = "warning", "正式站正常，但 Railway 未提供部署 commit"
        else:
            status, summary = "ok", f"資料庫正常，部署版本 {release[:7] or '未提供'}，{ms} ms"
        results.append(check("railway", "Railway deploy／應用健康", status, summary,
                             http_status=code, latency_ms=ms, release_sha=release,
                             expected_sha=expected_sha, health=payload))
    except Exception as exc:
        results.append(check("railway", "Railway deploy／應用健康", "critical", str(exc)))
    return results


def line_check(site):
    secret = os.environ.get("LINE_CHANNEL_SECRET", "").strip()
    if not secret:
        return check("line", "LINE webhook", "skipped", "未提供 LINE_CHANNEL_SECRET")
    body = b'{"events":[]}'
    signature = base64.b64encode(hmac.new(secret.encode(), body, hashlib.sha256).digest()).decode()
    try:
        code, response, ms = fetch(f"{site}/api/line/webhook", method="POST", data=body,
                                   headers={"Content-Type": "application/json", "X-Line-Signature": signature})
        ok = code == 200 and response.decode("utf-8", "replace").strip() == "OK"
        return check("line", "LINE webhook", "ok" if ok else "critical",
                     f"簽章空事件測試 HTTP {code}，{ms} ms", http_status=code, latency_ms=ms)
    except Exception as exc:
        return check("line", "LINE webhook", "critical", str(exc))


def _google_credentials():
    raw = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON", "").strip()
    if not raw:
        raw = os.environ.get("GSC_SERVICE_ACCOUNT_JSON", "").strip()
    if not raw:
        return None
    from google.oauth2 import service_account
    return service_account.Credentials.from_service_account_info(
        json.loads(raw), scopes=[
            "https://www.googleapis.com/auth/analytics.readonly",
            "https://www.googleapis.com/auth/webmasters.readonly",
        ])


def _analytics_rows(service, start_date, end_date):
    prop = os.environ.get("GA4_PROPERTY_ID", "").strip()
    body = {"dateRanges": [{"startDate": start_date, "endDate": end_date}],
            "dimensions": [{"name": "eventName"}], "metrics": [{"name": "eventCount"}],
            "limit": 1000}
    response = service.properties().runReport(property=f"properties/{prop}", body=body).execute()
    return {row["dimensionValues"][0]["value"]: int(row["metricValues"][0]["value"])
            for row in response.get("rows", [])}


def ga4_checks():
    if not os.environ.get("GA4_PROPERTY_ID", "").strip():
        skipped = check("ga4", "GA4 異常", "skipped", "未提供 GA4_PROPERTY_ID／Google 服務帳戶")
        return [check("contact", "諮詢表單成功率", "skipped", skipped.summary),
                check("not_found", "404 是否增加", "skipped", skipped.summary), skipped]
    try:
        credentials = _google_credentials()
        if credentials is None:
            raise RuntimeError("未提供 GOOGLE_SERVICE_ACCOUNT_JSON")
        from googleapiclient.discovery import build
        service = build("analyticsdata", "v1beta", credentials=credentials, cache_discovery=False)
        yesterday = _analytics_rows(service, "yesterday", "yesterday")
        baseline = _analytics_rows(service, "8daysAgo", "2daysAgo")
    except Exception as exc:
        message = f"GA4 API 無法讀取：{exc}"
        return [check("contact", "諮詢表單成功率", "warning", message),
                check("not_found", "404 是否增加", "warning", message),
                check("ga4", "GA4 異常", "warning", message)]

    attempts = yesterday.get("contact_submit_attempt", 0)
    failures = yesterday.get("contact_submit_failed", 0)
    successes = max(0, attempts - failures)
    rate = successes / attempts if attempts else None
    if attempts and rate < 0.8:
        contact_status = "critical"
    elif attempts and rate < 0.95:
        contact_status = "warning"
    else:
        contact_status = "ok"
    contact_summary = (f"嘗試 {attempts}、失敗 {failures}、推定成功率 {rate:.1%}"
                       if rate is not None else "昨日沒有表單送出嘗試")

    not_found = yesterday.get("page_not_found", 0)
    not_found_avg = baseline.get("page_not_found", 0) / 7
    if not_found >= max(5, not_found_avg * 3):
        nf_status = "critical"
    elif not_found >= max(2, not_found_avg * 2):
        nf_status = "warning"
    else:
        nf_status = "ok"

    pageviews = yesterday.get("page_view", 0)
    pv_avg = baseline.get("page_view", 0) / 7
    ga_status = "warning" if pv_avg >= 20 and pageviews < pv_avg * 0.3 else "ok"
    return [
        check("contact", "諮詢表單成功率", contact_status, contact_summary,
              attempts=attempts, failures=failures, inferred_successes=successes, success_rate=rate),
        check("not_found", "404 是否增加", nf_status,
              f"昨日 {not_found} 次；前 7 日平均 {not_found_avg:.1f} 次／日",
              yesterday=not_found, previous_daily_average=not_found_avg),
        check("ga4", "GA4 異常", ga_status,
              f"昨日瀏覽 {pageviews}；前 7 日平均 {pv_avg:.1f} 次／日",
              yesterday_page_views=pageviews, previous_daily_average=pv_avg),
    ]


def gsc_check(site):
    try:
        credentials = _google_credentials()
        if credentials is None:
            return check("gsc", "Google Search Console 索引", "skipped", "未提供 Google 服務帳戶")
        from googleapiclient.discovery import build
        service = build("searchconsole", "v1", credentials=credentials, cache_discovery=False)
        property_url = os.environ.get("GSC_SITE_URL", "sc-domain:phbay.info").strip()
        sitemap_url = os.environ.get("GSC_SITEMAP_URL", f"{site}/sitemap.xml").strip()
        entries = service.sitemaps().list(siteUrl=property_url).execute().get("sitemap", [])
        sitemap = next((row for row in entries if row.get("path") == sitemap_url), None)
        if not sitemap:
            return check("gsc", "Google Search Console 索引", "critical", "正式 sitemap 尚未提交")
        content = (sitemap.get("contents") or [{}])[0]
        indexed = int(content.get("indexed") or 0)
        submitted = int(content.get("submitted") or 0)
        errors = int(sitemap.get("errors") or 0)
        baseline_raw = os.environ.get("GSC_INDEXED_BASELINE", "").strip()
        baseline = int(baseline_raw) if baseline_raw else None
        dropped = baseline is not None and indexed < baseline * 0.9
        status = "critical" if errors or dropped else "ok"
        if baseline is None and status == "ok":
            status = "warning"
        summary = f"已收錄 {indexed}／提交 {submitted}；錯誤 {errors}"
        if baseline is None:
            summary += "；尚未設定索引基準"
        else:
            summary += f"；基準 {baseline}"
        return check("gsc", "Google Search Console 索引", status, summary,
                     indexed=indexed, submitted=submitted, errors=errors, baseline=baseline)
    except Exception as exc:
        return check("gsc", "Google Search Console 索引", "warning", f"GSC API 無法讀取：{exc}")


def render_markdown(report):
    icon = {"ok": "✅", "warning": "⚠️", "critical": "🛑", "skipped": "⏭️"}
    lines = [f"# 潮旅每日健康報告 — {report['generated_at'][:10]}", "",
             f"P3 新功能：**{'暫停' if report['p3_blocked'] else '可繼續'}**", "",
             "| 檢查 | 狀態 | 結果 |", "|---|---|---|"]
    for row in report["checks"]:
        summary = str(row["summary"]).replace("|", "／").replace("\n", " ")
        lines.append(f"| {row['label']} | {icon[row['status']]} {row['status']} | {summary} |")
    return "\n".join(lines) + "\n"


def run(site, expected_sha=""):
    checks = public_checks(site.rstrip("/"), expected_sha)
    checks.append(line_check(site.rstrip("/")))
    checks.extend(ga4_checks())
    checks.append(gsc_check(site.rstrip("/")))
    critical = [row for row in checks if row.status == "critical"]
    return {"generated_at": datetime.now(timezone.utc).isoformat(), "site": site,
            "overall": "critical" if critical else ("warning" if any(row.status == "warning" for row in checks) else "ok"),
            "p3_blocked": bool(critical), "critical_keys": [row.key for row in critical],
            "checks": [asdict(row) for row in checks]}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--site", default=os.environ.get("HEALTH_SITE_URL", DEFAULT_SITE))
    parser.add_argument("--expected-sha", default=os.environ.get("EXPECTED_DEPLOY_SHA", ""))
    parser.add_argument("--output", default="health-report.json")
    parser.add_argument("--markdown", default="health-report.md")
    args = parser.parse_args()
    report = run(args.site, args.expected_sha)
    Path(args.output).write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    markdown = render_markdown(report)
    Path(args.markdown).write_text(markdown, encoding="utf-8")
    print(markdown)
    return 2 if report["p3_blocked"] else 0


if __name__ == "__main__":
    sys.exit(main())
