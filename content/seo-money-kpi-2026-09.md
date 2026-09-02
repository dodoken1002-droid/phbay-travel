# 9 月 Money Keywords KPI 執行計畫

建立日：2026-09-03（KPI 起算日）
資料來源：`python scripts/gsc_report.py money`，快照存 `content/seo-money-snapshots/`

## 目標

| # | KPI | 目標 | 2026-09-03 起點 |
|---|---|---|---:|
| ① | 20 個 Money Keywords 全部納入追蹤 | 20 | **20 ✅ 已達成** |
| ② | 至少 10 個開始曝光 | ≥10 | 0 |
| ③ | 進入 Top 30 | ≥5 | 0 |
| ④ | 進入 Top 20 | 2–3 | 0 |
| ⑤ | 開始產生非品牌旅遊關鍵字點擊 | >0 | 0（非品牌曝光 386、80 個查詢，但 0 點擊）|

## 真正的瓶頸：不是內容，是收錄

2026-09-03 用 GSC URL Inspection 逐頁查證，結果如下：

| 網址 | 收錄狀態 | 最後爬取 |
|---|---|---|
| `/` | Submitted and indexed | **2026-06-21** |
| `/faq.html` | Submitted and indexed | 2026-08-16 |
| `/penghu-3days-itinerary` | URL is unknown to Google | 從未 |
| `/penghu-family-travel` | URL is unknown to Google | 從未 |
| `/penghu-itinerary-recommendations` | URL is unknown to Google | 從未 |
| `/penghu-food-guide`、`/penghu-2026-festival-guide` | URL is unknown to Google | 從未 |
| `/blog`、`/tides`、`/reviews`、兩個預購頁 | URL is unknown to Google | 從未 |
| `sitemap.xml` | 提交後從未被下載 | 從未 |

**Google 只認得這個網站的兩個網址。** 三個 Money Pages 一頁都沒被抓過，
所以 KPI ②③④ 目前不是「排名不夠好」，而是**根本沒有東西可以排名**。

技術面已排除的可能原因（2026-09-03 實測）：

- `robots.txt` 200、`Allow: /`，Googlebot UA 可正常抓取
- `sitemap.xml` 200、`application/xml`、89 筆網址、含三個 Money Pages
- 首頁對 Googlebot 回 200、無 `noindex`、51 個 `<a href>` 內含三個 Money Pages 連結
- `faq.html` 也已內鏈三個 Money Pages（爬取路徑存在）
- DNS 無失效的 AAAA 記錄（www 只有 A record → Railway）

結論：站台技術健康，問題是**整個網域的爬取意願極低**（外部權重不足）。
首頁 Google 的副本停在 2026-06-21，比三個攻略頁上線（7/19、9/02）還早，
所以 Google 手上那份首頁 HTML 裡根本沒有這些連結。

## 已完成（2026-09-03，commit 2d5416d）

盤點發現 **20 個關鍵字裡有 13 個在指定目標頁全文出現 0 次**——就算明天全部收錄，
這 13 個詞也不可能有排名。已補齊：

| 目標頁 | 補上的關鍵字 | 做法 |
|---|---|---|
| `/penghu-3days-itinerary` | 澎湖三天兩夜費用、澎湖三天兩夜自由行 | 新增費用拆解表（往返交通／住宿／島上交通／海上活動／餐食）＋自由行 vs 套裝比較段落與 2 則 FAQ |
| `/penghu-family-travel` | 澎湖親子行程、澎湖親子三天兩夜、澎湖親子景點 | 新增親子景點挑選表（7 個點，全部內鏈既有文章）＋親子三天兩夜逐日動線＋改寫 3 則 FAQ |
| `/penghu-itinerary-recommendations` | 澎湖自由行行程、澎湖自由行三天兩夜、澎湖自由行套裝行程、澎湖旅遊行程、澎湖旅遊推薦 | 新增「澎湖自由行怎麼安排」兩個 H3＋「不同旅客的澎湖旅遊推薦」比較表，title 補上自由行 |
| `/`（首頁） | 澎湖深度旅行、澎湖在地體驗、澎湖秘境行程 | 新增 `#deep-travel` 區塊三張卡，`deep.*` 鍵五語同步（i18n.js 版本升至 20260903）|

現在 20 個關鍵字在各自目標頁的全文出現次數皆 ≥1，且 title 命中 5 個主詞。

同時做的技術補強：

- 攻略頁 `dateModified` 統一由 `pillar_pages.LAST_MODIFIED` 控制，sitemap 對四個攻略頁輸出 `<lastmod>`——給 Google 明確的「這頁更新了」訊號
- `gsc_report.py money` 加了三項：群組 `contains` 領先指標（精確詞還是 0 時，可先看到長尾有沒有動）、全站非品牌點擊、每次執行自動寫快照並列出歷次 KPI 走勢

## ⚠️ 只有你能做的事（API 不開放，必須人工）

**這是目前唯一能解開 KPI ②③④ 的動作。** 到 GSC 網址審查逐一按「要求建立索引」：

1. https://search.google.com/search-console/inspect?resource_id=sc-domain:phbay.info&id=https://www.phbay.info/
   （**首頁優先**——重新爬首頁才會讓 Google 看到通往其他頁的連結）
2. …&id=https://www.phbay.info/penghu-itinerary-recommendations
3. …&id=https://www.phbay.info/penghu-3days-itinerary
4. …&id=https://www.phbay.info/penghu-family-travel

操作提醒（先前踩過）：搜尋框要先點到出現歷史下拉再輸入；成功提交後對話框未關時
按 Enter 會誤觸「再次提出要求」。每天配額約 10–12 個網址。

### 外部訊號（治本，決定 10 月以後能不能持續）

- `phbay.com.tw`（老站）加一個連到 `https://www.phbay.info` 的連結——這是目前
  最現成、最有效的外部訊號，老站已在首頁 JSON-LD 的 `sameAs` 裡，但沒有反向連結
- Google 商家檔案（2026-08-11 已通過審核）貼文帶上三個 Money Pages 網址
- FB／IG 個人簡介與貼文放攻略頁連結，不要只放首頁

## 各 KPI 的誠實評估

- **①（20 個納入追蹤）**：已達成，且已自動化。
- **②（10 個有曝光）**：只要首頁與三個攻略頁被重新爬取並收錄，20 個詞裡有 16 個
  現在有實質內容，達成 10 個曝光是合理的。**完全卡在人工要求索引這一步。**
- **③④（Top 30／Top 20）**：`澎湖親子三天兩夜`、`澎湖三天兩夜費用`、
  `澎湖自由行套裝行程`、`澎湖秘境行程` 這類長尾競爭較低，是最可能先進榜的；
  `澎湖自由行`、`澎湖三天兩夜` 這種大詞 9 月內進 Top 20 不切實際，不要用它們判斷成敗。
- **⑤（非品牌點擊）**：**這一項不必等收錄。** 站上已有 386 次非品牌曝光、
  80 個非品牌查詢、平均排名 4.8，但點擊是 0——全部集中在 `/faq.html` 的
  「幾月去澎湖／澎湖天氣」類查詢。排名沒問題，是**點閱率問題**。
  下一步應該針對這批已經有排名的查詢優化 `faq.html` 的 title 與 description，
  這是 9 月內最快能拿到第一個非品牌點擊的路徑。

## 每週節奏

固定每週同一天執行，不更換關鍵字清單：

```bash
cd /d/phbay-travel && .venv/Scripts/python.exe scripts/gsc_report.py money
```

每次會自動寫入 `content/seo-money-snapshots/<日期>.json` 並印出歷次走勢。
另外每週跑一次 `gsc_report.py inspect` 確認收錄狀態有沒有改變——
在「⑤ 已收錄頁數 > 2」之前，②③④ 的數字不會動，不需要反覆調整內容。
