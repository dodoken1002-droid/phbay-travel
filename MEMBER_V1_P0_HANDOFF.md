# 潮旅 Member V1 P0 — 最終進度、部署狀態與後續交接

更新時間：2026-09-03（Asia/Taipei）

Repository：`dodoken1002-droid/phbay-travel`

目前 main：`b1d6c1c`（Merge pull request #9）

Claude migration runner：`86af5e5`

Pull Request：<https://github.com/dodoken1002-droid/phbay-travel/pull/9>（已合併）

Railway staging：<https://phbay-member-v1-staging-staging.up.railway.app/member.html>

## 最終結論

Member V1 P0 Security Fix 已完成 Claude 獨立重新審查、追加 migration hardening、合併 main，並部署 production 驗證通過。

- PR #9：**已完整審查並合併**。
- Main merge commit：`b1d6c1c`。
- Production deployment：`4d357aa1`，狀態 **SUCCESS**。
- Production schema：已完成 migration 與必要結構驗證。
- P0 account linking、session authorization、LINE ID token verification、legacy regression：**通過審查**。
- OAuth：在缺少 provider credentials 時依設計 fail closed；尚未開放真實 LINE／Google 登入。

本文件取代先前「待 re-review／production NO-GO」的狀態。此 repository 的 Railway production 會自動部署 main，因此「合併 main」與「部署 production」不是可分離的兩個人工關卡：**merge main 即會觸發 production deployment**。

## 歷史事故與修復基線

`d5c0643` 曾把 Member V1 的部分 `app.py` 程式碼夾帶進 SEO commit，但會員建表 SQL 沒有進版控，造成 production 下列五條流程整筆交易失敗：

- register
- login / verify
- admin points
- 後台會員合併
- LINE 綁定 callback

當時 production 的 `members` 與 `member_auth_codes` 都是 0 筆，沒有留下成功註冊的會員。`661bf67` 已先補齊缺少 schema，PR #9 的 base 已包含這項修復。

## 四項 P0 修正的最終狀態

### 1. Account linking / email pre-hijacking

狀態：**完成、審查通過、已上 production**。

- Social identity 使用 `(provider, provider_subject)`；LINE／Google 以 immutable `sub` 為 identity key。
- Provider email 不會直接把 identity 自動合併到既有潮旅會員。
- 綁定既有帳號必須同時具備 verified email identity 與 10 分鐘內的潮旅 Email OTP step-up proof。
- OTP proof 必須屬於相同 member ID；綁定後立即消耗。
- Social login 本身會主動清掉舊 proof，避免 proof 重用或跨流程殘留。
- `oauth_error=email_otp_required` 已有繁中、英文、日文、韓文、簡中 UI 提示。

### 2. Session authorization

狀態：**完成、審查通過、已上 production**。

- Legacy 與 Member V1 routes 共用 `app.py` 的 `require_member()`。
- Validator 會確認會員存在、`is_active=TRUE` 且尚未被 merge。
- 無效會員 session 會清除 `member_id` 與 Email OTP proof。
- `/me`、identities、orders、order claim、merge、consents、phone binding 與 legacy LINE binding 沒有繞過 validator 的 route。
- Claude grep 全部 session 用法後，未發現第二套或可繞過的授權判定。

### 3. LINE identity verification

狀態：**完成、審查通過、已上 production；provider credentials 尚未設定**。

- LINE Login callback 以 `id_token` 驗證為核心，不依賴 `/v2/profile` email。
- 明確驗證 issuer、audience、nonce、expiration 與非空 `sub`。
- Nonce 使用常數時間比對。
- OAuth start 使用 state、nonce 與 PKCE；callback 驗證並消耗對應 session state。
- Email 只在合法 scope／consent 且 token 提供時作輔助資料，不是唯一身分依據。

### 4. Production legacy regression

狀態：**自動測試與 production smoke 驗證通過；真實會員 Email OTP E2E 尚待執行**。

已涵蓋：

- register 在 Email 驗證前不直接建立登入 session。
- Email OTP verify/login 建立 legacy 與 V1 共用 session，以及 verified email identity。
- member center `/me`。
- legacy LINE binding。
- identities、orders、consents、order claim、merge 的授權邊界。
- admin points、merge、order claim 與點數帳本同步。
- inactive／merged member 的舊 cookie 不可繼續讀寫 API，也不可把新訂單寫到死帳號。
- `lifetime_earned` 改為所有正向交易合計，避免平常更新與 `init_db` 回填產生不同結果。

## Claude 對 PR #9 的獨立審查結果

Claude 沒有直接採信舊交接文件，而是重新逐項驗證：

- 使用拋棄式 PostgreSQL 18.3 實跑整合測試。
- 確認退款功能已從最終程式 diff 移除；只剩歷史說明文字。
- 逐一執行 staging smoke，HTTP 200／401／503／404 與聲明一致。
- 搜尋全部 session 用法，確認受保護 route 沒有繞過 `require_member()`。
- 確認 LINE `id_token` 的 iss／aud／nonce／exp／sub 驗證齊備。
- 確認 email pre-hijacking 防線需 verified identity 加近期 Email OTP proof，proof 使用後即消耗。
- 確認 PR 可乾淨合併，且 base 已含 `661bf67`。

審查結論：P0 安全聲明屬實，程式碼品質良好。

## 測試執行的必要前置條件

整合測試結果不能脫離環境變數解讀。

### 完整 P0 整合測試

必須先設定：

```text
MEMBER_V1_TEST_DATABASE_URL=<disposable PostgreSQL URL>
```

在拋棄式 PostgreSQL 18.3 並包含 `86af5e5` 後的最終結果：

- **114 passed、3 skipped**。
- 3 個 skipped 是 optional PyYAML workflow 靜態檢查。
- 全新 DB migration 成功且可重複執行。
- 不完整 schema 會讓 migration exit 1，阻止 deployment。
- `SKIP_SCHEMA_INIT=1` import app 後資料表數仍為 0，確認 worker 不再執行 DDL。

### 預設直接跑測試

若沒有設定 `MEMBER_V1_TEST_DATABASE_URL`：

- 會顯示 **21 skipped**。
- 其中 18 個正是 PostgreSQL P0 security integration tests。
- 包含 `test_provider_email_never_auto_links_an_existing_member`、`test_line_binding_needs_recent_email_otp_and_uses_verified_sub` 等關鍵測試。

因此，看到預設 suite 綠燈不能解讀成完整 P0 security integration tests 已執行。CI 或人工驗證必須明確提供 disposable PostgreSQL URL，並在測試報告中標示該條件。

## Migration runner hardening（86af5e5）

Claude 在 PR #9 追加 `86af5e5`，移除多 worker 啟動時競爭執行 DDL 的問題。

### `migrate.py`

- 成為唯一 DDL 入口。
- 執行 `init_db()` 後再查詢 `information_schema` 驗證必要資料表與欄位。
- 因 `init_db()` 的會員表區塊原本使用 SAVEPOINT fail-open，不能只以「函式跑完」視為 migration 成功。
- 缺任何必要結構即以非零 exit code 結束。

### `app.py`

- `SKIP_SCHEMA_INIT=1` 時，模組層級不再建表。
- 同時把 `_db_initialized` 設為 true，關閉 `before_request` 的補建行為。
- Request workers 不再執行 DDL。

### `railway.json` / `Procfile`

啟動順序為：

```text
export SKIP_SCHEMA_INIT=1 && python migrate.py && python sync_repo_posts_cli.py && gunicorn ...
```

- Migration 失敗即不啟動 Gunicorn。
- Railway deployment 失敗時保留上一個成功版本繼續服務。
- DB 被重建時不再由 request path 自動補 schema，必須重新部署；這是刻意的安全取捨。

### Regression tests

`test_post_launch_hardening.py` 新增 `SchemaMigrationRunnerTests`，覆蓋：

- 全新 DB migration 與重跑冪等。
- 半套 migration／結構不符會阻擋部署。
- `verify_schema()` 正確列出缺少的 table／column。
- `SKIP_SCHEMA_INIT=1` 時 app worker 不建表。

## 合併與部署紀錄

- Staging 先驗證新的啟動路徑，log 出現 `[MIGRATE] schema 初始化與驗證完成`，沒有 worker DDL。
- PR #9 完整合併為 `b1d6c1c`。
- 沒有 cherry-pick 單一 commit，也沒有使用 `codex/member-v1-review`。
- Production deployment `4d357aa1`：SUCCESS。
- `codex/member-v1-p0-security` 已合併，不得再繼續推送；後續工作從最新 `origin/main` 開新分支。

## Production 已查證狀態

- Log 有 `[MIGRATE] schema 初始化與驗證完成`。
- 沒有 `[DB INIT]` 錯誤。
- 必要會員資料表均存在。
- `members.merged_into_member_id`：存在。
- `point_wallet.balance` 的非負 CHECK 已依設計移除；只保留 `lifetime_earned_check`。
- `/api/member/identities` 從 404 變為未登入 401，確認 Member V1 已掛載。
- LINE／Google OAuth start 在缺少 credentials 時回 503。
- Facebook 回 404，V1 未啟用。
- `EMAIL_USER`／`EMAIL_PASS` 已設定；Email OTP 路徑理論上可用，但尚未做真實收信 E2E。
- `LINE_OAUTH_*`、`GOOGLE_OAUTH_*`、`SMS_OTP_WEBHOOK_URL` 尚未設定。
- `FLASK_SECRET_KEY` 尚未設定，app 目前沿用 `ADMIN_KEY` 當 session key。

## 目前待辦

1. 刪除誤建的 Railway 專案 `fix9`。刪除屬破壞性操作，必須確認精確 project ID 並取得明確授權後再做。
2. 為 staging 與 production 設定獨立、隨機且持久的 `FLASK_SECRET_KEY`。目前輪換 `ADMIN_KEY` 會讓全部會員 session 失效。
3. 補 LINE／Google staging 與 production credentials，完成真實 provider E2E。
4. 實跑 production register → Email OTP → member center。這會建立真實會員並寄信，執行前需指定測試 Email 並確認授權。
5. `posts.faq` fresh-DB migration 另開 issue，不混入 Member V1 P0。
6. 將 CI 配置成提供 disposable PostgreSQL，避免 18 個 P0 tests 被預設 skip。

## 操作注意事項

- 不要恢復模組層級或 request path 的 `init_db()` DDL。
- 不要移除 `railway.json`／`Procfile` 的 `migrate.py` 步驟。
- 不要 revert `86af5e5`。
- Production 自動部署 main；任何 merge main 都應視為 production release。
- `D:\phbay-travel` 的 Railway CLI 目前 link 到 staging。操作 production 時必須明確加 `-e production`，並指定正確 service／project。
- `D:\phbay-travel` 已於本次狀態同步 fast-forward 到 `b1d6c1c`。
- Main checkout 的 `CLAUDE_REVIEW.md`、設定步驟文件、images、scripts、scratch 與其他 untracked files 是刻意保留的其他工作；不得 reset、刪除或納入無關 commit。
- Railway `fix9` 的刪除與 production 設定變更不得因本文件而自動執行。

## Current Go / No-Go

- PR #9 security re-review：**PASS**。
- Merge main：**DONE**（`b1d6c1c`）。
- Production deployment：**DONE / SUCCESS**（`4d357aa1`）。
- Member V1 核心 API 與 fail-closed protection：**LIVE**。
- 真實 Email OTP E2E：**待執行**。
- LINE／Google OAuth 對外啟用：**NO-GO，等待 credentials 與 provider E2E**。
- 其他 Member V1 新功能擴充：**不屬於本 P0，需另開範圍與分支**。
