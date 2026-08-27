# Claude 上傳前審查交接 — P0 至 P3

> 狀態：所有本次變更只在本機 working tree，尚未 commit、尚未 push、尚未部署。請先完成本文件的審查，再決定是否提交。

## 本次完成範圍

- P0：每日檢查首頁、行程、五語頁、諮詢成功率、LINE webhook、404、Railway／資料庫、GA4、GSC；Critical 自動開啟 GitHub Issue 並阻擋 P3，可選擇 LINE owner 告警。
- P1：contact／一般預購／內海預購的嘗試、成功、失敗與 `method`；UTM 保存；後台 lead funnel、成單金額、來源與 30 日摘要；GA4 每週報告。
- P2：production sitemap、核心頁、最新文章、canonical、hreflang、JSON-LD、meta、llms 檔與內容缺口稽核；GSC 近 28 日與前期比較。
- P3：會員資料表、可設定等級、Email OTP、LINE 綁定、旅行護照、訂單完成自動認列、點數帳本、推薦、五語會員頁與後台管理／合併／匯出。

## Claude 優先審查點

1. `app.py` 的 schema migration 能否在目前 Railway PostgreSQL 版本重複安全執行。
2. 會員 API 的授權邊界：公開路由、會員 session、`orders` 角色與 owner-only 合併。
3. Email OTP 是否不洩漏會員存在性、10 分鐘效期、每小時 5 次限制及 HMAC scope。
4. 訂單狀態在 planned／completed／cancelled 間切換時，`member_trips` 與 `trip_count` 是否一致。
5. 會員合併的 unique conflict、點數／旅次移轉與 LINE 綁定保留。
6. 前端所有使用者資料皆以 `textContent` 呈現，避免注入；確認 CSP／既有 GA4 行為未被破壞。
7. 三個 workflow 在 GitHub Actions 的權限、排程、失敗閘門及 artifact 行為。
8. P0 Critical 規則是否符合營運期待：任一 critical 都暫停 P3，warning 不暫停。

## 已執行驗證

- `22` 個 Python 單元／契約測試通過。
- `app.py`、會員規則及四支監控／報表腳本通過 Python compile。
- `script.js`、`i18n.js` 通過 Node syntax check。
- `git diff --check` 無 whitespace error。
- 本機瀏覽器驗證：首頁會員入口、`/penghu-100`、英文切換、`/admin` 與「百旅會員」頁籤均可載入，桌面寬度無水平溢出。
- 本機 P0 runner 可正常產生 JSON／Markdown 與 P3 gate；因本機未接正式 DB／GA4／GSC／LINE，對應項目會 Critical 或 skipped，屬預期結果。

## 建議 Claude 重跑

```powershell
& '.\.venv\Scripts\python.exe' -m unittest discover -v
& '.\.venv\Scripts\python.exe' -m py_compile app.py member_program.py scripts\daily_health_check.py scripts\conversion_report.py scripts\gsc_report.py scripts\seo_audit.py
& 'C:\Users\rhuser\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe' --check script.js
& 'C:\Users\rhuser\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe' --check i18n.js
git diff --check
git diff --stat
```

## 上線前需由站方設定

- GitHub／Railway secret：`GOOGLE_SERVICE_ACCOUNT_JSON`（或 `GSC_SERVICE_ACCOUNT_JSON`）、`LINE_CHANNEL_SECRET`、`LINE_CHANNEL_ACCESS_TOKEN`、`LINE_OWNER_USER_ID`。
- GitHub variable：`GA4_PROPERTY_ID`、`GSC_SITE_URL`、`GSC_SITEMAP_URL`、首次量測後的 `GSC_INDEXED_BASELINE`。
- Railway：確認既有 `DATABASE_URL`、`FLASK_SECRET_KEY`、`EMAIL_USER` 與 Gmail service account／`EMAIL_PASS` 可供會員 OTP 使用。
- 選配：`MEMBER_NO_PREFIX`、`MEMBER_LEVELS_JSON`。未設定時使用 PH 編號與 1／2／5／10／20／100 旅次預設等級。
- GA4 管理介面註冊 event-scoped custom dimension `method`，再將需要的成功事件標記為 key event。
- 確認會員個資告知、點數用途、等級權益與退會／刪除資料 SOP 的正式營運文案。

## 審查通過後的建議順序

1. 先建立 commit，不直接修改 production DB。
2. push 後觀察 Railway migration／部署 log 與 `/health`。
3. 手動執行 P0 daily workflow；只在無 Critical 時繼續。
4. 手動執行 P1、P2 workflow，核對 GA4／GSC 有資料而非 skipped。
5. 用測試會員完成註冊、OTP、LINE 綁定、訂單 completed 認列、取消回退與帳號合併。
6. 最後再公告會員入口。
