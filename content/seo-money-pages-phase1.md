# Money Pages 第一階段執行規格

更新日：2026-09-02

## 盤點與去重決策

| 主題 | 唯一 canonical Money Page | 決策 | 既有內容角色 |
|---|---|---|---|
| 澎湖親子旅遊 | `/penghu-family-travel` | 更新既有 Pillar，不新增相近頁 | 親子景點、雨天、潮間帶文章只做衛星頁並內鏈回本頁 |
| 澎湖三天兩夜 | `/penghu-3days-itinerary` | 更新既有 Pillar，不新增相近頁 | 景點與交通文章提供單點資訊並內鏈回本頁 |
| 澎湖行程推薦 | `/penghu-itinerary-recommendations` | 新增；站內原無同意圖 Pillar | 首頁 `#tours` 保留商品瀏覽，不與本頁競爭資訊型查詢 |
| 澎湖自由行 | `/penghu-itinerary-recommendations` | 第一階段作為次要查詢，不另開頁 | 後續若 GSC 顯示穩定需求再評估獨立 Pillar |
| 澎湖深度旅遊 | `/` | 保留首頁既有定位，不另開頁 | 深度景點文章為衛星頁 |
| 澎湖天氣／季節 | `/faq.html#cat-season` | 保留既有高曝光入口 | 以情境式 CTA 導向三個第一階段 Money Pages，不改寫成交易頁 |

同一個關鍵字只指定一個 target URL。部落格文章不得以三個 Pillar 的完整主關鍵字作為 Title/H1；新文章發佈前先檢查 `content/seo-money-keywords.json`。

## 9 月 KPI

- 20 個 Money Keywords 全部進入固定 GSC 報表。
- 至少 10 個關鍵字有曝光。
- 至少 5 個關鍵字進 Top 30。
- 2–3 個關鍵字進 Top 20。
- 開始產生非品牌旅遊關鍵字點擊。

執行 `python scripts/gsc_report.py money` 取得近 28 天基準；每週固定同一天重跑，不更換關鍵字清單。
