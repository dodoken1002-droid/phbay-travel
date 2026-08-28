# 監控憑證設定與首次基準驗證

> 對象：站方（需要 GitHub、GA4、GSC、LINE 的管理權限）。
> 目的：讓 P0／P1／P2 三個 workflow 第一次跑出正式基準。
> 最後更新：2026-08-28

---

## 一、已經設好的（不用再動）

`submit-gsc-sitemap.yml` 已成功執行 85 次，代表以下三個 **secrets 早就存在且值是對的**：

| 名稱 | 類型 | 應有的值 |
|---|---|---|
| `GSC_SERVICE_ACCOUNT_JSON` | Secret | Google 服務帳戶 JSON 全文 |
| `GSC_SITE_URL` | Secret | `sc-domain:phbay.info` |
| `GSC_SITEMAP_URL` | Secret | `https://www.phbay.info/sitemap.xml` |

新的 P0 workflow 原本讀 `vars.GSC_SITE_URL`／`vars.GSC_SITEMAP_URL`，
但 GitHub 的 secrets 與 variables 是**兩個不同的命名空間**，會拿到空字串。
已於 2026-08-28 改為讀同一組 secrets，因此**這三項不需要重設**。

三個新 workflow 也接受 `GOOGLE_SERVICE_ACCOUNT_JSON`，但 `_google_credentials()`
會自動回退到 `GSC_SERVICE_ACCOUNT_JSON`，所以沿用既有那把就好，不必新增。

---

## 二、還需要設定的

GitHub → 專案 → **Settings** → **Secrets and variables** → **Actions**

### Secrets（點 New repository secret）

| 名稱 | 從哪裡取得 |
|---|---|
| `LINE_CHANNEL_SECRET` | LINE Developers Console → 你的 Messaging API channel → **Basic settings** → Channel secret |
| `LINE_CHANNEL_ACCESS_TOKEN` | 同一個 channel → **Messaging API** 分頁 → Channel access token（long-lived，若沒有就按 Issue） |
| `LINE_OWNER_USER_ID` | 用你自己的 LINE 對潮旅官方帳號傳一則訊息，Railway log 會記下該則訊息的 `userId`（`U` 開頭的 33 碼）。這是 P0 critical 要推播的對象。 |

### Variables（點 Variables 分頁 → New repository variable）

| 名稱 | 值 |
|---|---|
| `GA4_PROPERTY_ID` | GA4 → 管理 → **資源設定** → 資源詳細資料 → **資源 ID**。純數字，例如 `398765432`。**不要**填 `G-47DV1VPF9J`，那是評估 ID，不是資源 ID。 |
| `GSC_INDEXED_BASELINE` | **第一次跑完 P0 之後才填**（見第四節） |

### 容易漏掉的一步：把服務帳戶加進 GA4

現有的服務帳戶是為 Search Console 建立的，**GA4 是另一套權限**。
沒有這一步，GA4 Data API 會回 403，諮詢成功率、404 趨勢、GA4 異常三項會一直是 warning。

1. 打開 `GSC_SERVICE_ACCOUNT_JSON` 的內容，找到 `client_email`（形如
   `xxx@yyy.iam.gserviceaccount.com`）。
2. GA4 → 管理 → **資源存取管理** → 右上角 **+** → 新增使用者。
3. 貼上該 email，角色選 **檢視者**，取消勾選「傳送電子郵件通知」。

### GA4 自訂維度（P1 週報需要）

GA4 → 管理 → **自訂定義** → 建立自訂維度：

- 維度名稱：`method`
- 範圍：**事件**
- 事件參數：`method`

這是 P1 用來把 contact／quiz／preorder 的轉換分流的依據。註冊後**要等 24–48 小時**
才會有資料，因此第一次跑 P1 週報若看到 method 是空的，先確認是不是還沒回填。

---

## 三、其他可選變數（都有合理預設，通常不用設）

| 名稱 | 預設值 |
|---|---|
| `HEALTH_SITE_URL` | `https://www.phbay.info` |
| `HEALTH_TOUR_PATH` | `/preorder/festival` |
| `MEMBER_POINTS_PER_TRIP`（Railway） | `100` |
| `MEMBER_NO_PREFIX`（Railway） | `PH` |
| `MEMBER_LEVELS_JSON`（Railway） | 1／2／5／10／20／100 六級 |
| `CSP_ENFORCE`（Railway） | 未設＝Report-Only；設為 `1` 轉強制 |

---

## 四、首次基準驗證

三個 workflow 都有 `workflow_dispatch`，**不要等排程**。
GitHub → **Actions** → 左側選 workflow → 右上 **Run workflow** → 選 `main` → 執行。

### 步驟

1. **先跑 P0**（`P0 daily website health`）。
2. 打開該次執行的 **Summary**，逐項確認狀態。
3. 把 GSC 項目回報的 **已收錄數字**填進 Variables 的 `GSC_INDEXED_BASELINE`。
   這是之後判斷「收錄數大跌」的基準，沒填的話該項會一直是 warning。
4. 再跑 **P1**（`P1 weekly conversion report`）與 **P2**（`P2 weekly SEO GEO AEO audit`）。
5. 三份報告都會存成 artifact（P0 保留 30 天、P1／P2 保留 90 天）。

### 第一次跑的預期結果

| 檢查項 | 預期 | 若不符代表 |
|---|---|---|
| 首頁 | ok | — |
| 行程 API | ok | — |
| 五語頁 | ok | — |
| Railway deploy／應用健康 | ok | 版本不符且 main 最新 commit 已超過 30 分鐘 → 部署真的卡住 |
| LINE webhook | ok | critical＝簽章驗證失敗，檢查 `LINE_CHANNEL_SECRET` 是否貼錯 |
| 諮詢表單成功率 | ok 或 warning | warning 且訊息提到「0 次嘗試但有 N 次瀏覽」→ 前端事件可能壞了，要查 |
| 404 趨勢 | ok | — |
| GA4 異常 | ok | warning 且訊息是「GA4 API 無法讀取」→ 服務帳戶還沒加進 GA4（見第二節） |
| GSC 索引 | warning | warning 是正常的，因為 `GSC_INDEXED_BASELINE` 還沒填 |

**只要沒有任何 critical，就不會開「暫停 P3 新功能開發」的 Issue。**
warning 不擋開發，這是刻意設計。

### 門檻說明（2026-08-28 校準過）

- GSC 找不到 sitemap → **warning**（設定問題，不該擋開發），並會列出 GSC 上實際註冊的路徑供比對。
- sitemap errors → **warning**；只有**收錄數跌破基準 10%** 才是 critical。
- 部署版本不符，但 main 最新 commit 未滿 30 分鐘 → **warning**（還在部署中）。
- 瀏覽量 ≥100 卻 0 次表單送出嘗試 → **warning**（前端可能壞了）。
- 腳本崩潰沒產出報告 → 該次 run 會標記 error 並跳過閘門步驟，不會靜默。

---

## 五、部署後還要盯的兩件事

### CSP 觀察期（自 2026-08-28 起算一週）

目前是 `Content-Security-Policy-Report-Only`，**只回報不攔截**。
請在這一週內用桌機與手機各走一次：首頁、行程頁、預購頁、乞龜頁、會員頁、後台，
打開瀏覽器開發者工具的 Console，看有沒有 CSP 違規訊息。

- 沒有違規 → Railway 設 `CSP_ENFORCE=1`，重新部署即轉為強制模式。
- 有違規 → 把違規的網域回報，補進 `app.py` 的 `_CSP` 白名單後再轉強制。

### 註冊流程行為變更

填完註冊表單**不會**再直接進入會員中心，改為要求輸入 Email 收到的六位數驗證碼。
這是為了修掉「拿別人的 Email 開帳號就能立刻取得登入態」的問題。

請用一個真實可收信的信箱親手走一次：
註冊 → 畫面轉為驗證碼欄位 → 收信 → 輸入六位數 → 進入會員中心。
接著**用同一組資料再送一次註冊**，應該得到**一模一樣**的訊息，
不會出現「已加入」之類的提示——這就是防枚舉生效的樣子。

對外的操作說明與客服話術需同步更新。
