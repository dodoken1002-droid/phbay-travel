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
- [ ] 在 GitHub 設定監控用 Secrets／Variables，手動跑一次 workflow 建立基準（需站方憑證）。
- [x] Critical 除 GitHub Issue 閘門外，可選擇推送 LINE owner；未設定憑證時安全略過。

## P1 — 轉換追蹤

- [x] 將 contact、quiz、preorder 的轉換事件以 `method` 清楚分流，並記錄嘗試／成功／失敗。
- [x] 建立 GA4 每週轉換漏斗報告，區分裝置、來源、語言並與前期比較。
- [x] 表單與預購保留 UTM 歸因；前端事件統一由 GA4 事件層送出，避免同一處重複觸發。
- [x] 建立諮詢→聯繫→成單的後台狀態、金額、來源與可稽核報表。
- [ ] 使用正式 GA4 資料跑第一次報告，確認自訂維度 `method` 已註冊（需 GA4 權限）。

## P2 — SEO／GEO／AEO

- [x] 建立每週 GSC 收錄、曝光、點擊、查詢與重點頁報告。
- [x] 建立 pillar page、文章內鏈、FAQ／摘要、CTA 與五語內容缺口稽核。
- [x] 自動驗證 sitemap、canonical、hreflang、JSON-LD、llms.txt／llms-full.txt。
- [x] 每週 workflow 產生報告與 artifact，技術 SEO error 會阻擋通過。
- [ ] 正式部署後跑第一次 production audit 與 GSC 報告（需 GSC 權限）。

## P3 — 澎湖百旅會員

- [x] P0-3 前置資料：旅次、會員狀態、會員編號已進諮詢表單／後台／CSV。
- [x] 定義會員資格、完成旅次認定、重複帳號合併與個資最小化保存規則；等級門檻可由環境變數調整。
- [x] 會員中心 `/member/dashboard`、Email 一次性登入碼、LINE 綁定、旅行護照、旅次與點數帳本。
- [x] 首頁、行程卡／行程詳情、諮詢資料與 LINE 文字指令完成會員整合。
- [x] 依未參加行程提供下一趟推薦，並加入會員註冊、登入、綁定與推薦點擊事件。
- [x] 後台可建立／搜尋／匯出會員、認列旅次、調整點數與合併重複帳號。
- [ ] 上線前確認正式會員條款、點數用途與各等級權益文案（營運決策，不影響系統運作）。

## 上線後第一批（2026-08-27 Claude 審查待辦）

審查中已於上線前修掉的項目：後台諮詢卡片儲存型 XSS、旅次認列政策旗標、
訂單同步交易隔離、正式環境預設 secret key 防護、會員資料表遷移清單掛勾。
以下為評估後判定「不阻擋上線、但需盡快處理」的項目。

### 資料一致性

- [x] `member_trips.points_awarded` 已接上：完成且可認列的旅次自動給點（`MEMBER_POINTS_PER_TRIP`，預設 100），
      取消走負向沖銷；旅行護照新增「點數」欄並補齊五語。2026-08-27 完成。
- [x] 自動認列（`_sync_completed_order_trip`，最常見路徑）不發升等 LINE 通知，
      只有後台手動 PATCH 才發，多數會員升等收不到訊息。
      （2026-08-28 完成：升等通知改在訂單 commit 之後推送，網路呼叫不佔交易鎖）
- [x] `ON CONFLICT` 不更新 `member_id`：訂單聯絡電話改綁另一位會員後，
      旅次仍掛在原會員，兩邊 `trip_count` 都會失準。
      （2026-08-28 完成：旅次與點數帳本一起改掛新會員，新舊雙方都重算）
- [x] `preorder_products.counts_as_trip` 後台介面已完成（百旅會員頁籤 →「預購行程・旅次認列設定」），
      owner 專屬，切換時一併校正既有旅次與點數並寫稽核。2026-08-27 完成。

### 會員帳號安全

- [x] 註冊即發 session、Email 未經驗證；且 409「此手機或 Email 已加入」會洩漏帳號存在性，
      與 `login/request` 刻意做的防枚舉不一致。請統一策略。
      （2026-08-28 完成：一律回相同訊息並寄驗證碼，驗證後才發 session）
- [x] 合併會員的 `WHERE id IN (%s,%s) FOR UPDATE` 沒有固定鎖順序，
      並發合併理論上可 deadlock（owner-only、機率低）。
      （2026-08-28 完成：改為依 id 由小到大逐筆鎖定）
- [x] 七個 `/api/admin/member*` 端點用 `error=str(exc)` 回傳原始 psycopg2 例外，
      與前台一律回通用訊息的做法不一致。
      （2026-08-28 完成：8 處改為通用訊息＋伺服器端記錄，含 conversion_summary）
- [x] 會員名單 CSV（含姓名、手機、Email）目前 `orders` 角色即可匯出，
      合併卻是 owner-only。請確認匯出權限是否也該收斂為 owner。
      （2026-08-28 完成：收斂為 owner 專屬）

### 監控門檻校準

- [x] GSC「sitemap 尚未提交」與「errors > 0」都判 critical，會直接暫停 P3。
      `GSC_SITEMAP_URL` 只要與 GSC 註冊路徑字串不完全一致（www／非 www）就會變成永久假 critical。
      建議降為 warning，或改用 suffix 比對。
      （2026-08-28 完成：改為 warning＋結尾比對；只有收錄數跌破基準才 critical）
- [x] `daily_health_check.py` 若硬崩潰而未產出 `health-report.json`，
      gate step 的 `readFileSync` 會丟例外 → run 變紅但不開 Issue、也不發 LINE。建議加 `hashFiles()` 保護。
      （2026-08-28 完成：閘門步驟加 hashFiles 保護，並另發 error 註記）
- [x] `weekly-conversion-report.yml` 缺 `continue-on-error` 與 `if: always()`，
      腳本一失敗就拿不到 summary 與 artifact，與另外兩個 workflow 不一致。
      （2026-08-28 完成：補上並加獨立的失敗閘門）
- [x] 表單「昨日 0 次嘗試」判 ok。若前端 JS 整個壞掉導致完全沒有 attempt 事件，
      這個檢查看不出來——正是本次想堵的盲區。建議「attempt=0 但 pageview 正常」連續 N 天升 warning。
      （2026-08-28 完成：瀏覽量 ≥100 卻 0 次嘗試改判 warning）
- [x] `EXPECTED_DEPLOY_SHA` 用 `github.sha`，部署延遲會產生假 critical，建議給 30 分鐘寬限。
      （2026-08-28 完成：main 最新 commit 未滿 30 分鐘時降為 warning）

### 既有問題（非本次引入，但建議一併處理）

- [x] `/api/health` 未經驗證即回傳 `db_error` 原文，會洩漏資料庫連線細節。
      （2026-08-28 完成：只回 connection_failed，詳情留在 Railway log）
- [x] 全站沒有 CSP，XSS 沒有第二道防線。
      （2026-08-28 完成：已上 Report-Only；觀察無誤報後設 CSP_ENFORCE=1 轉強制）
- [ ] `current_admin()` 在 `ADMIN_KEY` 未設時回傳 owner（開發模式全開）。
