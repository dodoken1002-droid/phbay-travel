# P0｜30 秒澎湖行程診斷 V1 交接

基準：GitHub `main` `98fc191188957b61988bff3a8c13afc87b68ca05`（2026-09-17 實作前重新查詢）。

狀態：程式與本機測試完成，尚未部署 Production。

## 完成範圍

- `/penghu-itinerary-recommendations`：10 題手機優先診斷，不先索取姓名、電話或 Email。
- `/penghu-itinerary-recommendations/result`：即時顯示旅行類型、逐日建議、適合原因、注意事項、價格區間，以及直接預訂／微調／LINE CTA。
- `itinerary-quiz.js`：可維護、可單元測試的 rule-based V1，不呼叫 LLM。
- 匿名答案只留在瀏覽器 `sessionStorage`；日期、成人／兒童實際人數不進 GA4。
- 預購頁事件鏈：`product_view`、`checkout_start`、`purchase`，並保留原有 `generate_lead` 與失敗追蹤。

## GA4 事件

- `quiz_start`
- `quiz_complete`
- `itinerary_view`
- `product_view`
- `checkout_start`
- `line_click`
- `purchase`

診斷漏斗只允許附帶以下匿名維度：`travel_days`、`party_type`、`children_age`、`budget_range`、`travel_style`、`avoid_preference`、`arrival_method`、`first_visit`。

## 測試

- Node 規則測試：`node test_itinerary_quiz.js`
- Python 全套 regression：`python -m unittest discover -p "test_*.py"`
- 本機視覺檢查：桌面版與 390 × 844 手機版，含 10 題完成後的結果頁。

## Staging 驗證清單

- [ ] 推薦頁 10 題可用鍵盤、觸控完成，返回上一題不遺失答案。
- [ ] 未填題目會停留並顯示繁中錯誤，不會前進。
- [ ] 0 位兒童自動採 `none`；有兒童時要求年齡區間。
- [ ] 親子＋幼兒＋避免長船程可得到「親子安心慢遊型」及短船程建議。
- [ ] 結果頁重新整理仍保留同一瀏覽器工作階段結果；新工作階段無答案時引導重新診斷。
- [ ] 直接預訂進入既有內海預購頁；微調進入既有首頁諮詢；LINE 開啟官方帳號。
- [ ] GA4 DebugView 依序收到 `quiz_start` → `quiz_complete` → `itinerary_view` → `product_view`。
- [ ] 從結果進預購後收到 `checkout_start`；預購 API 成功才收到 `purchase`。
- [ ] GA4 事件不得包含姓名、電話、Email、日期、成人數或兒童數。
- [ ] LINE／Google 會員登入、會員 dashboard 正常。
- [ ] 內海預購與通用 `/preorder/<slug>` 可選場次、驗證同意欄位並建立訂單。
- [ ] `/privacy`、`/terms`、FAQ、sitemap 與既有主題頁回應正常。
- [ ] iPhone Safari、Android Chrome 各走一次 390px 左右的完整診斷流程。
- [ ] 確認 staging GA4 資料串流或 DebugView，不把測試訂單混入正式報表。

## Production 前提醒

`purchase` 目前定義為「預購 API 成功建立訂單」，不是已收款。若日後接上線上付款，應把此事件移到付款成功 webhook／完成頁，預購成功改用 `generate_lead` 或自訂 `preorder_created`。
