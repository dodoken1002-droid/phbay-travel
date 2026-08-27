# Claude 審查回覆與修正紀錄 — 2026-08-27

回應 `CLAUDE_REVIEW_20260827.md` 的八個審查點，並記錄實際動手修改的內容。
**所有變更仍在本機 working tree，尚未 commit、尚未 push、尚未部署。**

驗證狀態：`49` 個測試通過（原 22 ＋ 新增 27）、`py_compile` 全過、
`admin.html` 與 `member.html` 內嵌 JS 通過 `node --check`、`git diff --check` 無 whitespace 錯誤。

---

## 一、八個審查點的結論

| 點 | 結論 |
|---|---|
| 1 遷移可重複執行 | **通過**，`ADD/CREATE ... IF NOT EXISTS` 皆 PG 9.5+ 語法。但原本缺未來的欄位遷移路徑，已補（見 §2.5） |
| 2 授權邊界 | **通過**。公開路由走 session、後台 `has_role('orders')`、合併 owner-only，分層正確 |
| 3 Email OTP | **通過**。不洩漏存在性、10 分鐘效期、每小時 5 次、HMAC 綁 `member_id:purpose:code`、`compare_digest` ＋ `attempts<5` ＋ `FOR UPDATE` 均正確。惟註冊端點破壞防枚舉（列上線後） |
| 4 訂單狀態一致性 | **邏輯通過**：`trip_count` 一律由 completed＋counts_trip 重算，取消會正確回退；兩張表的 status 字彙都含 `completed`／`cancelled`，對應正確。另有三處已修（見 §2.2、§2.3） |
| 5 會員合併 | **通過**。UniqueViolation 回 409 並 rollback、旅次點數搬移、LINE 綁定保留皆正確 |
| 6 前端注入 | **member.html 通過**（全用 `textContent`）。**admin.html 不通過 → 已修**（見 §2.1） |
| 7 三個 workflow | **大致通過**。權限最小化、排程時間換算正確、無 `pull_request_target` 風險。三個小問題列上線後 |
| 8 P0 Critical 規則 | **符合營運期待**：`p3_blocked = bool(critical)`、warning 不擋；exit code 2 與 Issue 開關同源、訊號一致。惟門檻易誤爆（列上線後） |

### 一項更正

初次審查我判斷「代售行程會被自動認列、會員等級會灌水」屬即時風險，**這點過重了**。
代售行程（公會手冊 38 筆＋主題遊程 9 筆）全部存放在 `tours` 表，是純展示卡片，
不經過 `preorder_orders` 下單流程，因此不會被自動同步認列。
實際缺的是「每個預購商品沒有可否認列的政策開關」，這仍與規劃書要求不符，已補上。

同理，原本我說「旅行護照每筆永遠顯示 0 點」也不精確——該表格原本根本沒有點數欄位。
真正的問題是**完成旅次從來不會產生任何點數**，點數功能形同虛設。已一併解決。

---

## 二、上線前已修（8/27 第一批）

### 2.1 後台儲存型 XSS ⚠️ 最高優先

`admin.html` 的諮詢卡片走 `innerHTML`，13 處使用者可控欄位未經跳脫。
其中 `utm_source` 為本次新增，`c.name`／`c.phone`／`c.notes` 等為既有漏洞。

攻擊路徑：帶 `?utm_source=<img src=x onerror=...>` 進站後送出諮詢表單 →
管理員開啟後台「諮詢漏斗」時在其瀏覽器執行。後台 JS 持有 `ADMIN_KEY`，
一旦觸發等同整個後台被接管，含會員個資 CSV 匯出。

**修法**：13 處插值全部包上檔案內既有的 `memberEsc()`（涵蓋 `& < > " '`）。

### 2.2 旅次認列政策開關

`preorder_products` 新增 `counts_as_trip` 欄位（預設 `TRUE`，現有商品皆為潮旅自營）。
`_sync_completed_order_trip()` 不再硬寫 `TRUE`，改由呼叫端帶入：
預購端讀商品旗標、內海巡禮明示自營。
`ON CONFLICT` 仍不覆寫 `counts_trip`，**客服的人工判定永遠優先於自動同步**。

### 2.3 訂單同步的交易隔離

`_sync_completed_order_trip()` 整段以 `SAVEPOINT` 包住，任何失敗只記 log；
兩個呼叫端加上 `if synced:` 防 JOIN 失配（例如航次已刪）。
現在會員同步無論怎麼壞，都不會讓「改訂單狀態」這個核心訂位作業失敗。
（此為 2026-07 諮詢表單無聲失敗一個多月的教訓延伸。）

### 2.4 正式環境 secret key 防護

會員登入態（`session['member_id']`）與 Email OTP 的 HMAC 都繫於 `app.secret_key`，
而其 fallback 鏈為 `FLASK_SECRET_KEY` → `ADMIN_KEY` → 硬編碼 `'phbay-dev-secret'`。
若正式站落到硬編碼值，任何人都能偽造 cookie 以任意會員身分登入。

**修法**：正式環境（`RAILWAY_ENVIRONMENT_NAME` 有值）落到預設值即 `raise` 拒絕啟動；
僅設 `ADMIN_KEY` 而未設 `FLASK_SECRET_KEY` 時印警告（兩者耦合，輪換會讓全體會員登出）。

> ⚠️ **仍需站方確認**：Railway 上 `FLASK_SECRET_KEY` 是否確實已設定。
> `railway variables --service phbay-travel | grep -E "FLASK_SECRET_KEY|ADMIN_KEY"`

### 2.5 會員資料表遷移清單

`init_member_tables()` 原本只有 `CREATE TABLE IF NOT EXISTS`，
而該語句**不會修改已存在的資料表**——這正是 7/19 contacts 事故的同一個模式，
第一次部署沒事，下次改會員欄位就會靜默失敗。
且它位於 `init_db()` 中段，一旦丟例外，後面的 `qigui_daily_quota` 等表全都不會建立。

**修法**：以 `SAVEPOINT` 隔離建表段落；於 `member_program.py` 新增
`MEMBER_COLUMN_MIGRATIONS` 清單與 `_migrate_member_columns()` 掛勾，
註解直接寫明事故因果，供日後新增欄位使用。

---

## 三、本次新做的兩個功能（8/27 第二批）

### 3.1 預購行程・旅次認列設定頁

**位置**：後台 →「百旅會員」頁籤 → 最上方「預購行程・旅次認列設定」。

- `GET /api/admin/preorder/products` — `has_role('orders')` 可讀。
  逐項列出商品名稱、slug、啟用狀態、**完成訂單筆數**與**目前已認列筆數**，
  讓管理者在切換政策前先看到影響範圍。
- `PATCH /api/admin/preorder/products/<id>/counts-as-trip` — **僅 owner**。
  認列政策屬商業決策，訂位人員不得變更（與「合併會員」的權限界線一致）。

**切換時的行為**：預設一併校正該商品**既有**的旅次（`apply_to_existing`），
否則設錯之後只能人工逐筆改。點數走 `sync_trip_points()` 的差額沖銷，
不會竄改歷史紀錄。整個動作寫入 `audit_logs`，記錄影響的旅次數與會員數。

前端會依方向顯示不同的確認文字，並在完成後回報「校正既有旅次 N 筆／M 位會員」。

### 3.2 旅次點數自動給付

新增 `member_program.points_per_trip()` 與 `sync_trip_points(cur, trip_id)`。

**規則**：旅次為 `completed` 且 `counts_trip=TRUE` → 應得 `MEMBER_POINTS_PER_TRIP` 點
（環境變數可調，預設 100）；其餘狀態應得 0 點。

**冪等設計**：先算「這趟應得幾點」，再與帳本上已針對這趟給過的點數相比，**只補差額**。
因此重複執行不會重複給點；旅次改為取消或改為不計入時差額為負，
會自動產生一筆負向沖銷紀錄，而不是偷偷改掉歷史。

**接入點**共三處：後台新增旅次、後台更新旅次狀態、訂單狀態自動同步。

**會員端**：`/api/member/me` 新增回傳 `points_per_trip`；
`member.html` 的「旅行護照」表格新增「點數」欄，並補齊英／日／韓／簡中四語
（繁中走 HTML 預設值），符合規劃書「所有前台文案一律五國語言」的鐵則。

> 註：目前系統尚未上線，無既有資料，因此不需要回填。
> 若日後需要對歷史旅次補點，逐筆呼叫 `sync_trip_points()` 即可，該函式本身冪等。

---

## 四、新增的測試

| 檔案 | 內容 |
|---|---|
| `test_member_safety.py` | 12 項：後台跳脫、認列政策不得硬寫、`ON CONFLICT` 不得覆寫人工判定、SAVEPOINT 隔離、secret key 防護、遷移清單掛勾 |
| `test_trip_points.py` | 15 項：點數冪等性（重跑不重複給點）、取消走負向沖銷、代售不給點、`MEMBER_POINTS_PER_TRIP` 可設定與異常值處理、政策端點權限契約、護照點數欄與四語 |

特別保留了「自動同步不得覆寫人工 `counts_trip` 判定」與「重跑不得重複給點」兩條，
因為那是重構時最容易被改掉、且出錯後最難察覺的兩個地方。

---

## 五、仍待處理

完整清單見 `content/operations-backlog.md` 的「上線後第一批」。摘要：

**資料一致性**：自動認列不發升等 LINE 通知（只有後台手動 PATCH 會發）；
`ON CONFLICT` 不更新 `member_id`，訂單改綁他人後兩邊 `trip_count` 會失準。

**會員帳號安全**：註冊即發 session 且 Email 未驗證；409 訊息洩漏帳號存在性，
與 `login/request` 的防枚舉不一致；七個 admin 端點回傳原始 psycopg2 例外；
會員 CSV（含姓名手機 Email）目前 `orders` 角色即可匯出，建議收斂為 owner。

**監控門檻**：GSC「sitemap 尚未提交」與「errors > 0」都判 critical 會誤爆並暫停 P3；
健康檢查腳本硬崩潰時不會開 Issue 也不發 LINE；
`weekly-conversion-report.yml` 缺 `continue-on-error`／`if: always()`；
表單「昨日 0 次嘗試」判 ok 會漏掉前端 JS 整個壞掉的情況。

**既有問題**：`/api/health` 未驗證即回傳 `db_error` 原文；全站無 CSP；
`current_admin()` 在 `ADMIN_KEY` 未設時全開。

---

## 六、建議上線順序

1. 確認 Railway 的 `FLASK_SECRET_KEY`（§2.4），這是唯一無法由程式碼自行保證的前置條件。
2. 建立 commit，不直接修改 production DB。
3. push 後觀察 Railway migration／部署 log 與 `/api/health`。
4. 手動執行 P0 daily workflow；只在無 Critical 時繼續。
5. 進後台「百旅會員 → 預購行程・旅次認列設定」，逐項確認每個商品的認列政策。
6. 手動執行 P1、P2 workflow，核對 GA4／GSC 有資料而非 skipped。
7. 用測試會員完成註冊、OTP、LINE 綁定、訂單 completed 認列（確認點數入帳）、
   取消回退（確認產生負向沖銷）與帳號合併。
8. 最後再公告會員入口。
