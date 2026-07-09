"""潮旅 GSC 固定檢查流程：sitemap 狀態＋重點頁收錄＋品牌詞成效。

用法（需先完成 Google_SearchConsole_API_設定步驟.md 的一次性設定）：

    python scripts/gsc_report.py            # 跑全部
    python scripts/gsc_report.py sitemaps   # 只看 sitemap
    python scripts/gsc_report.py inspect    # 只看重點頁收錄
    python scripts/gsc_report.py brand      # 只看品牌詞成效（近 28 天）

金鑰路徑從環境變數 GSC_KEY_FILE 讀（建議放 .env，不要 commit 金鑰檔）。
"""

import os
import sys
from datetime import date, timedelta

# Windows 主控台預設 cp950,直接印中文會亂碼
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from dotenv import load_dotenv
from google.oauth2 import service_account
from googleapiclient.discovery import build

PROPERTY = "sc-domain:phbay.info"
SITE = "https://www.phbay.info"
SITEMAP_URL = f"{SITE}/sitemap.xml"

# 重點頁：商業價值最高、最需要確認收錄的網址
KEY_URLS = [
    f"{SITE}/preorder/festival",
    f"{SITE}/neihai-preorder.html",
    f"{SITE}/blog/2026-07-07-penghu-fenggui-cave-sound-guide",
    f"{SITE}/blog/2026-07-08-penghu-tongliang-banyan-north-ring-guide",
]

BRAND_TERMS = ["潮旅", "phbay"]


def _service():
    load_dotenv()
    key_file = os.environ.get("GSC_KEY_FILE", "")
    if not key_file or not os.path.exists(key_file):
        sys.exit(
            "找不到服務帳戶金鑰。請在 .env 設定 GSC_KEY_FILE=<金鑰json路徑>，"
            "設定步驟見 Google_SearchConsole_API_設定步驟.md"
        )
    creds = service_account.Credentials.from_service_account_file(
        key_file, scopes=["https://www.googleapis.com/auth/webmasters"]
    )
    return build("searchconsole", "v1", credentials=creds, cache_discovery=False)


def report_sitemaps(svc) -> None:
    print("== Sitemap 狀態 ==")
    entries = svc.sitemaps().list(siteUrl=PROPERTY).execute().get("sitemap", [])
    mine = next((s for s in entries if s.get("path") == SITEMAP_URL), None)
    # 沒提交過、或 Google 從未成功下載 → (重新)提交以觸發重抓
    if mine is None or not mine.get("lastDownloaded"):
        print(f"  {SITEMAP_URL} {'尚未提交' if mine is None else 'Google 尚未成功抓取'}，(重新)提交…")
        svc.sitemaps().submit(siteUrl=PROPERTY, feedpath=SITEMAP_URL).execute()
        print("  已提交，Google 會在數小時～數天內排程抓取。")
        entries = svc.sitemaps().list(siteUrl=PROPERTY).execute().get("sitemap", [])
    for s in entries:
        counts = s.get("contents", [{}])[0]
        print(
            f"  {s.get('path')}\n"
            f"    最後下載：{s.get('lastDownloaded', '（尚未）')}"
            f"｜提交 {counts.get('submitted', '?')} 筆"
            f"｜已收錄 {counts.get('indexed', '?')} 筆"
            f"｜錯誤 {s.get('errors', 0)}｜警告 {s.get('warnings', 0)}"
        )


def report_inspect(svc) -> None:
    print("== 重點頁收錄狀態 ==")
    need_manual = []
    for url in KEY_URLS:
        resp = (
            svc.urlInspection()
            .index()
            .inspect(body={"inspectionUrl": url, "siteUrl": PROPERTY})
            .execute()
        )
        result = resp["inspectionResult"]["indexStatusResult"]
        verdict = result.get("verdict", "?")
        state = result.get("coverageState", "?")
        crawled = result.get("lastCrawlTime", "（尚未爬取）")
        print(f"  {url}\n    判定：{verdict}｜狀態：{state}｜最後爬取：{crawled}")
        if verdict != "PASS":
            need_manual.append(url)
    if need_manual:
        print("  ↑ 未收錄的頁面，請手動到 GSC 網址審查按「要求建立索引」（API 不開放此動作）：")
        for u in need_manual:
            print(f"    https://search.google.com/search-console/inspect"
                  f"?resource_id={PROPERTY}&id={u}")


def report_brand(svc, days: int = 28) -> None:
    print(f"== 品牌詞成效（近 {days} 天）==")
    end = date.today() - timedelta(days=2)  # GSC 資料延遲約 2 天
    start = end - timedelta(days=days)
    # GSC API 的 filter group 只支援 and，OR 語意得逐詞查再合併
    merged = {}
    for term in BRAND_TERMS:
        body = {
            "startDate": start.isoformat(),
            "endDate": end.isoformat(),
            "dimensions": ["query"],
            "dimensionFilterGroups": [{
                "filters": [{"dimension": "query", "operator": "contains",
                             "expression": term}],
            }],
            "rowLimit": 25,
        }
        for r in (svc.searchanalytics().query(siteUrl=PROPERTY, body=body)
                  .execute().get("rows", [])):
            merged[r["keys"][0]] = r
    rows = sorted(merged.values(), key=lambda r: -r["impressions"])
    if not rows:
        print("  （沒有品牌詞資料——品牌搜尋還沒有曝光，符合先前診斷）")
        return
    print(f"  {'查詢字詞':<30}曝光    點擊    平均排名")
    for r in rows:
        q = r["keys"][0]
        print(f"  {q:<30}{r['impressions']:<8}{r['clicks']:<8}{r['position']:.1f}")


def main() -> None:
    cmd = sys.argv[1] if len(sys.argv) > 1 else "all"
    svc = _service()
    if cmd in ("all", "sitemaps"):
        report_sitemaps(svc)
    if cmd in ("all", "inspect"):
        report_inspect(svc)
    if cmd in ("all", "brand"):
        report_brand(svc)


if __name__ == "__main__":
    main()
