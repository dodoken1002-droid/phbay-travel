# 潮旅網站營運 Backlog

固定優先順序：**P0 營運健康 → P1 轉換追蹤 → P2 SEO/GEO/AEO → P3 澎湖百旅會員**。

## 開發閘門

- 每日健康報告只要出現任一 `critical`，自動開啟 `[P0 Critical] 暫停 P3 新功能開發` Issue。
- Critical 未排除前，不合併任何 P3 新功能；僅允許 P0 修復及避免資料流失的緊急變更。
- 健康報告恢復後，排程會自動關閉閘門 Issue，才恢復 P3。

## P0 — 網站營運健康檢查

- [x] 首頁 HTTP 200、品牌內容與延遲。
- [x] 行程 API 可用且至少有一筆啟用行程。
- [x] 最新完整翻譯文章的繁中、英、日、韓、簡中皆為 200 且標題正確。
- [x] 諮詢表單昨日嘗試、失敗與推定成功率（GA4）。
- [x] LINE webhook 使用合法簽章的空事件做無副作用檢查。
- [x] 404 `page_not_found` 昨日次數與前七日平均比較。
- [x] Railway 正式站資料庫健康、contacts 表及部署 commit 對照。
- [x] GA4 昨日 page views 與前七日平均比較。
- [x] GSC sitemap 索引數、錯誤及索引基準跌幅。
- [ ] 在 GitHub 設定監控用 Secrets／Variables，手動跑一次 workflow 建立基準。
- [ ] 決定告警通知管道（GitHub Issue 之外是否加 LINE owner 通知）。

## P1 — 轉換追蹤

- [ ] 將 contact、quiz、preorder 的 `generate_lead` 以 `method` 清楚分流。
- [ ] GA4 建立轉換漏斗與每日／每週基準，區分裝置、來源、語言。
- [ ] 驗證 Meta Pixel 與 GA4 不重複、不漏記，補 UTM 命名規則。
- [ ] 建立諮詢→聯繫→成單的後台狀態與可稽核報表。

## P2 — SEO／GEO／AEO

- [ ] 逐週追蹤 GSC 收錄、曝光、點擊、查詢與重點頁排名。
- [ ] 補齊 pillar pages、文章內鏈、FAQ／摘要與五語內容缺口。
- [ ] 驗證 sitemap、canonical、hreflang、JSON-LD、llms.txt／llms-full.txt。
- [ ] 建立內容更新節奏與索引下降處置流程。

## P3 — 澎湖百旅會員

- [x] P0-3 前置資料：旅次、會員狀態、會員編號已進諮詢表單／後台／CSV。
- [ ] 定義會員資格、旅次認定、重複帳號合併與個資保存規則。
- [ ] 會員中心 `/member/dashboard`、登入／綁定與旅程紀錄。
- [ ] 行程頁、首頁、諮詢與 LINE 的會員權益整合。
- [ ] 個人化推薦與會員成效追蹤。
