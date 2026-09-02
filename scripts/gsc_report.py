"""潮旅 GSC 固定檢查流程：sitemap 狀態＋重點頁收錄＋品牌詞成效。

用法（需先完成 Google_SearchConsole_API_設定步驟.md 的一次性設定）：

    python scripts/gsc_report.py            # 跑全部
    python scripts/gsc_report.py sitemaps   # 只看 sitemap
    python scripts/gsc_report.py inspect    # 只看重點頁收錄
    python scripts/gsc_report.py brand      # 只看品牌詞成效（近 28 天）
    python scripts/gsc_report.py money      # 20 個 Money Keywords 基準與 9 月 KPI

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
# （固定清單＋自動加上 content/posts 最新 3 篇，避免清單過期）
KEY_URLS = [
    f"{SITE}/",
    f"{SITE}/preorder/festival",
    f"{SITE}/neihai-preorder.html",
    f"{SITE}/penghu-3days-itinerary",
    f"{SITE}/penghu-family-travel",
    f"{SITE}/penghu-itinerary-recommendations",
    f"{SITE}/penghu-food-guide",
    f"{SITE}/penghu-2026-festival-guide",
]


def _latest_post_urls(n: int = 3) -> list:
    """從 content/posts/*.json 取最新 n 篇文章網址（檔名含日期，排序即時序）。"""
    import glob
    import json as _json

    posts_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                             "content", "posts")
    urls = []
    for path in sorted(glob.glob(os.path.join(posts_dir, "*.json")), reverse=True)[:n]:
        try:
            slug = _json.load(open(path, encoding="utf-8")).get("slug", "")
            if slug:
                urls.append(f"{SITE}/blog/{slug}")
        except Exception:
            continue
    return urls

BRAND_TERMS = ["潮旅", "phbay"]
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MONEY_KEYWORDS_FILE = os.path.join(ROOT, "content", "seo-money-keywords.json")
SNAPSHOT_DIR = os.path.join(ROOT, "content", "seo-money-snapshots")


def _service():
    load_dotenv()
    raw_json = (os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON") or
                os.environ.get("GSC_SERVICE_ACCOUNT_JSON") or "").strip()
    if raw_json:
        creds = service_account.Credentials.from_service_account_info(
            __import__('json').loads(raw_json),
            scopes=["https://www.googleapis.com/auth/webmasters"])
        return build("searchconsole", "v1", credentials=creds, cache_discovery=False)
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
        pending = "｜⏳ 提交排隊中" if s.get("isPending") else ""
        print(
            f"  {s.get('path')}\n"
            f"    最後下載：{s.get('lastDownloaded', '（尚未）')}"
            f"｜提交 {counts.get('submitted', '?')} 筆"
            f"｜已收錄 {counts.get('indexed', '?')} 筆"
            f"｜錯誤 {s.get('errors', 0)}｜警告 {s.get('warnings', 0)}{pending}"
        )


def report_inspect(svc) -> None:
    print("== 重點頁收錄狀態 ==")
    need_manual = []
    for url in KEY_URLS + _latest_post_urls():
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


def report_growth(svc, days: int = 28) -> None:
    """查詢詞與頁面成效，並與前一個等長期間比較總量。"""
    end = date.today() - timedelta(days=2)
    cur_start = end - timedelta(days=days - 1)
    prev_end = cur_start - timedelta(days=1)
    prev_start = prev_end - timedelta(days=days - 1)

    def query(start, finish, dimensions):
        body = {
            "startDate": start.isoformat(), "endDate": finish.isoformat(),
            "rowLimit": 25,
        }
        if dimensions:
            body["dimensions"] = dimensions
        return svc.searchanalytics().query(siteUrl=PROPERTY, body=body).execute().get("rows", [])

    current_total = query(cur_start, end, [])
    previous_total = query(prev_start, prev_end, [])
    cur = current_total[0] if current_total else {}
    prev = previous_total[0] if previous_total else {}
    print(f"== 搜尋成長（近 {days} 天 vs 前期）==")
    print(f"  點擊：{cur.get('clicks', 0)}（前期 {prev.get('clicks', 0)}）")
    print(f"  曝光：{cur.get('impressions', 0)}（前期 {prev.get('impressions', 0)}）")
    print(f"  CTR：{cur.get('ctr', 0):.1%}（前期 {prev.get('ctr', 0):.1%}）")
    print(f"  平均排名：{cur.get('position', 0):.1f}（前期 {prev.get('position', 0):.1f}）")
    for dimension, label in (("query", "熱門查詢"), ("page", "熱門頁面")):
        print(f"== {label} ==")
        for row in query(cur_start, end, [dimension])[:15]:
            print(f"  {row['keys'][0]}｜曝光 {row['impressions']}｜點擊 {row['clicks']}｜排名 {row['position']:.1f}")


def report_money(svc, days: int = 28) -> None:
    """固定 20 個 Money Keywords 的可重跑基準，避免每週換詞造成誤判。"""
    import json
    keywords = json.load(open(MONEY_KEYWORDS_FILE, encoding="utf-8"))
    end = date.today() - timedelta(days=2)
    start = end - timedelta(days=days - 1)
    rows = []
    for item in keywords:
        body = {
            "startDate": start.isoformat(), "endDate": end.isoformat(),
            "dimensions": ["query"],
            "dimensionFilterGroups": [{"filters": [{
                "dimension": "query", "operator": "equals",
                "expression": item["keyword"],
            }]}],
            "rowLimit": 1,
        }
        found = svc.searchanalytics().query(siteUrl=PROPERTY, body=body).execute().get("rows", [])
        metric = found[0] if found else {}
        rows.append({**item, "clicks": int(metric.get("clicks", 0)),
                     "impressions": int(metric.get("impressions", 0)),
                     "position": metric.get("position")})

    exposed = sum(r["impressions"] > 0 for r in rows)
    top30 = sum(r["position"] is not None and r["position"] <= 30 for r in rows)
    top20 = sum(r["position"] is not None and r["position"] <= 20 for r in rows)
    clicks = sum(r["clicks"] for r in rows)
    print(f"== 20 個 Money Keywords 基準（{start}～{end}）==")
    print("  關鍵字｜群組｜優先｜目標頁｜曝光｜點擊｜平均排名")
    for r in rows:
        pos = f'{r["position"]:.1f}' if r["position"] is not None else '—'
        print(f'  {r["keyword"]}｜{r["cluster"]}｜{r["priority"]}｜{r["target"]}｜'
              f'{r["impressions"]}｜{r["clicks"]}｜{pos}')

    # 精確詞在 0 曝光階段看不出進展，改用「群組 contains」當領先指標：
    # 只要相關長尾開始有曝光，就代表該主題頁已經被 Google 看見。
    clusters = {}
    for item in keywords:
        clusters.setdefault(item["cluster"], set()).add(item["keyword"])
    print("== 群組領先指標（contains 比對，含長尾）==")
    cluster_stat = {}
    for cluster in clusters:
        body = {
            "startDate": start.isoformat(), "endDate": end.isoformat(),
            "dimensions": ["query"],
            "dimensionFilterGroups": [{"filters": [{
                "dimension": "query", "operator": "contains", "expression": cluster,
            }]}],
            "rowLimit": 25,
        }
        found = svc.searchanalytics().query(siteUrl=PROPERTY, body=body).execute().get("rows", [])
        imp = sum(r["impressions"] for r in found)
        clk = sum(r["clicks"] for r in found)
        cluster_stat[cluster] = {"queries": len(found), "impressions": imp, "clicks": clk}
        print(f"  {cluster}｜相關查詢 {len(found)} 個｜曝光 {imp}｜點擊 {clk}")
        for r in found[:3]:
            print(f"      ↳ {r['keys'][0]}｜曝光 {r['impressions']}｜排名 {r['position']:.1f}")

    # 非品牌點擊：KPI 說的是「開始產生非品牌旅遊關鍵字點擊」，
    # 範圍是全站扣掉品牌詞，不只這 20 個精確詞。
    body = {"startDate": start.isoformat(), "endDate": end.isoformat(),
            "dimensions": ["query"], "rowLimit": 500}
    all_rows = svc.searchanalytics().query(siteUrl=PROPERTY, body=body).execute().get("rows", [])
    nonbrand = [r for r in all_rows
                if not any(b.lower() in r["keys"][0].lower() for b in BRAND_TERMS)]
    nonbrand_clicks = sum(r["clicks"] for r in nonbrand)
    nonbrand_imp = sum(r["impressions"] for r in nonbrand)

    print("== 9 月 KPI 漏斗 ==")
    print(f"  ① 已納入追蹤：{len(rows)}/20（目標 20）{'✅' if len(rows) >= 20 else '❌'}")
    print(f"  ② 有曝光：{exposed}/20（目標至少 10）{'✅' if exposed >= 10 else '❌'}")
    print(f"  ③ Top 30：{top30}/20（目標至少 5）{'✅' if top30 >= 5 else '❌'}")
    print(f"  ④ Top 20：{top20}/20（目標 2–3）{'✅' if top20 >= 2 else '❌'}")
    print(f"  ⑤ 非品牌點擊：{nonbrand_clicks}（目標開始產生）{'✅' if nonbrand_clicks > 0 else '❌'}"
          f"｜非品牌曝光 {nonbrand_imp}｜非品牌查詢 {len(nonbrand)} 個")
    print(f"     其中 Money Keywords 精確詞點擊：{clicks}")

    snapshot = {
        "run_date": date.today().isoformat(),
        "period": {"start": start.isoformat(), "end": end.isoformat()},
        "kpi": {"tracked": len(rows), "exposed": exposed, "top30": top30, "top20": top20,
                "nonbrand_clicks": nonbrand_clicks, "nonbrand_impressions": nonbrand_imp,
                "money_exact_clicks": clicks},
        "keywords": rows, "clusters": cluster_stat,
    }
    os.makedirs(SNAPSHOT_DIR, exist_ok=True)
    path = os.path.join(SNAPSHOT_DIR, f"{date.today().isoformat()}.json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(snapshot, fh, ensure_ascii=False, indent=2)
    print(f"  已寫入快照：{os.path.relpath(path, ROOT)}")
    _print_trend()


def _print_trend() -> None:
    """列出歷次快照的 KPI 走勢，讓每週重跑能直接看到有沒有前進。"""
    import glob
    import json
    paths = sorted(glob.glob(os.path.join(SNAPSHOT_DIR, "*.json")))
    if len(paths) < 2:
        return
    print("== KPI 走勢（歷次快照）==")
    print("  日期｜有曝光｜Top30｜Top20｜非品牌點擊")
    for p in paths:
        try:
            s = json.load(open(p, encoding="utf-8"))
        except Exception:
            continue
        k = s.get("kpi", {})
        print(f'  {s.get("run_date", "?")}｜{k.get("exposed", 0)}｜{k.get("top30", 0)}｜'
              f'{k.get("top20", 0)}｜{k.get("nonbrand_clicks", 0)}')


def main() -> None:
    cmd = sys.argv[1] if len(sys.argv) > 1 else "all"
    svc = _service()
    if cmd in ("all", "sitemaps"):
        report_sitemaps(svc)
    if cmd in ("all", "inspect"):
        report_inspect(svc)
    if cmd in ("all", "brand"):
        report_brand(svc)
    if cmd in ("all", "growth"):
        report_growth(svc)
    if cmd in ("all", "money"):
        report_money(svc)


if __name__ == "__main__":
    main()
