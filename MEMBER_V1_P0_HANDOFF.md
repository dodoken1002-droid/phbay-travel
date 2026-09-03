# Member V1 P0 Security Fix — Claude 交接與重新審查報

更新時間：2026-09-03（Asia/Taipei）  
Repository：`dodoken1002-droid/phbay-travel`  
基準：`origin/main` at `911ee34`  
安全分支：`codex/member-v1-p0-security`  
P0 程式碼 snapshot：`ae3275762259407237304585e62c85147d212bd8`  
Pull Request：<https://github.com/dodoken1002-droid/phbay-travel/pull/9>  
Railway staging：<https://phbay-member-v1-staging-staging.up.railway.app/member.html>

## 結論先行

四項指定的 P0 安全修正已完成，已建立獨立 staging 並部署成功；production 沒有部署、沒有修改。

目前結論是：**可以進 staging 重新審查，不可直接進 production。**

真實 Email OTP、LINE Login、Google Login 的端到端測試仍需 staging 專用憑證。憑證未設定時，OAuth 入口會安全回傳 HTTP 503，不會退回不安全的 email 自動合併流程。

## 指定範圍與完成狀態

### 1. Account linking / email pre-hijacking

狀態：完成。

- Social identity 的主鍵使用 `(provider, provider_subject)`；LINE／Google 使用 provider 回傳的 immutable `sub`。
- Provider 回傳的 email 不會直接把 social identity 綁到既有潮旅會員。
- 若 email 對應既有會員，使用者必須先走潮旅自己的 Email OTP 登入。
- OTP 成功後 session 才會取得 10 分鐘有效的 `member_email_otp_proof`。
- 綁定完成即消耗 proof，避免同一份 step-up proof 被重複使用。
- UI 可辨識 `oauth_error=email_otp_required`，以繁中、英文、日文、韓文、簡中提示回到 Email OTP 登入。

主要位置：

- `app.py`：`member_login_verify()`、`member_email_otp_proof` 建立與清除。
- `member_v1.py`：`has_recent_email_otp()`、OAuth callback 的既有會員綁定判定。
- `member.html`：`oauthEmailOtpLabels` 與 `oauth_error=email_otp_required` 顯示。
- `member_program.py`：`member_identities` 的 `(provider, provider_subject)` unique constraint。

### 2. Session authorization

狀態：完成。

- `app.py` 提供唯一的 `require_member()` 授權邊界。
- Legacy 與 V1 routes 都透過同一 validator 驗證 `session['member_id']`。
- Validator 會查驗會員仍存在、`is_active=TRUE`，且沒有被 merge。
- 無效或過期會員 session 會同時移除 `member_id` 與 Email OTP proof。
- `/api/member/me`、`/api/member/identities`、`/api/member/orders`、order claim、merge、consents、phone binding，以及 legacy LINE binding 都使用相同判定。
- staging 未登入 smoke test 已確認上述受保護路徑一致回 HTTP 401。

主要位置：

- `app.py`：`require_member()`、`_checkout_member_id()`。
- `member_v1.py`：`current_member_id()` 只呼叫注入的 `require_member()`，沒有第二套 session 判定。

### 3. LINE identity verification

狀態：完成。

- LINE callback 以 LINE Login `id_token` 驗證為核心。
- 透過 LINE 官方 verify endpoint 驗證 token。
- 額外明確檢查 `iss=https://access.line.me`、`aud=LINE channel/client ID`、nonce、`exp` 與非空 `sub`。
- OAuth start 產生 state、nonce 與 PKCE verifier/challenge；callback 會比對並消耗 session state。
- 不呼叫 `/v2/profile` 取得 email。
- Email 僅在合法 token/scopes 實際提供時作輔助資料，不是 identity key，也不能單獨觸發帳號合併。

主要位置：

- `member_v1.py`：`_verify_line_id_token()`、`member_oauth_start()`、`member_oauth_callback()`。

### 4. Production legacy regression

狀態：程式與自動測試完成；真實寄信／OAuth E2E 尚待 staging 憑證。

已覆蓋或驗證：

- register 不會在驗證 Email 前直接建立登入 session。
- Email OTP verify/login 建立 legacy 與 V1 共用 session，並建立 verified email identity。
- member center `/me`。
- legacy LINE binding。
- identities、orders、consents、order claim 與 merge 的授權邊界。
- admin points、merge、order claim 與點數帳本同步相關 regression tests。
- 已停用／合併會員的舊 cookie 不可再讀寫會員 API，也不可把新訂單寫到死帳號。
- staging 實際呼叫 `/api/member/register` 成功，證明會員、consent、login-code 寫入路徑可運作。

## 最終差異範圍

相對 `origin/main`：7 個檔案，1,512 insertions、22 deletions。

- `.env.example`：OAuth、SMS OTP 與 callback 設定範例，不含密鑰。
- `app.py`：共用 member validator、OTP proof、V1 掛載與 legacy 相容調整。
- `member.html`：OAuth 入口、訂單認領 UI，以及 Email OTP required 五語提示。
- `member_program.py`：Member V1 tables、identity／consent／wallet／claim／merge schema 與可重跑 migration。
- `member_v1.py`：Member V1 API 模組。此檔在 base branch 不存在，所以 PR 顯示為完整新增，Claude 必須審查整個檔案。
- `test_member_v1.py`：P0 security、session、OAuth、order claim、merge 及 PostgreSQL integration tests。
- `test_trip_points.py`：必要的既有點數行為 regression coverage。

## 測試證據

乾淨 worktree 的最終結果：

- 完整 Python test suite：**111 passed，3 skipped**。
- 3 個 skipped 是環境未安裝 optional PyYAML，僅影響 workflow YAML 靜態檢查。
- Disposable PostgreSQL integration tests：通過。
- `python -m py_compile`：通過。
- JavaScript syntax check：通過。
- `git diff --check origin/main...HEAD`：通過。
- 最終安全 worktree：clean。

Railway staging smoke test：

- Deployment `5e71ebbf-8c34-46a6-b45a-3123f5fd33f0`：SUCCESS。
- `/api/health`：200，database connected。
- `/member.html`：200。
- `/api/member/register`：200，回傳 `verify_required=true`。
- 未登入 `/api/member/me`：401。
- 未登入 `/api/member/identities`：401。
- 未登入 `/api/member/orders`：401。
- 未登入 `/api/member/consents`：401。
- 未登入 legacy `/api/member/line-bind-code`：401。
- 缺少 OAuth credentials 時 LINE start：503。
- 缺少 OAuth credentials 時 Google start：503。
- smoke test 後 error-level runtime logs：沒有新增錯誤。

## Staging 配置

Railway project：`aware-heart`  
Staging environment ID：`1aa2016b-957a-4cd2-aff4-d1ffd98160ee`  
Staging web service：`phbay-member-v1-staging` (`b2dfc369-a9da-40e9-b059-02442f478064`)  
Staging PostgreSQL：`Postgres-KG5T` (`9e1b6dfa-e629-4c0b-92f6-0829c88db4bf`)

已設定：

- 獨立 staging PostgreSQL；沒有複製 production database 或 production secrets。
- 新產生的 staging-only `FLASK_SECRET_KEY`。
- `DATABASE_URL` 指向獨立 staging PostgreSQL。
- `MEMBER_PRIVACY_POLICY_VERSION=v1`。
- `RAILPACK_PYTHON_VERSION=3.11`。未固定時 Railway 預設 Python 3.13，與目前 `psycopg2-binary==2.9.9` 不相容；固定後部署成功。
- LINE／Google callback URI 已指向 staging domain。

尚未設定，且不得由程式作者自行杜撰或複製 production secrets：

- `LINE_OAUTH_CLIENT_ID`
- `LINE_OAUTH_CLIENT_SECRET`
- `GOOGLE_OAUTH_CLIENT_ID`
- `GOOGLE_OAUTH_CLIENT_SECRET`
- staging Email delivery credentials/configuration

## 已知風險與未完成的外部驗證

1. 因缺少 staging Email delivery credentials，尚未完成「實際收到 Email → 輸入 OTP → 登入」的 staging E2E。
2. 因缺少 LINE／Google staging client credentials，尚未完成真實 provider callback E2E；目前只完成自動化 token/security tests 與缺憑證 fail-closed 驗證。
3. 首次全新 staging DB 啟動時，兩個 Gunicorn workers 同時呼叫 `init_db()`，其中一個曾記錄 PostgreSQL type 建立競態；另一個成功完成，health 與實際 register 都成功。正式 production rollout 前建議把 schema migration 移到單一 pre-deploy migration，而不是由多 worker 啟動時競爭執行。
4. 全新 DB 首次啟動曾出現 repo post sync 查詢 `posts.faq` 欄位不存在；web server 有 fail-open 繼續啟動。這不是本次 Member V1 P0 變更，但應另開 migration issue，不要混入本 PR。
5. GitHub PR 目前沒有自動 CI status checks；本文件列出的測試是在乾淨本機 worktree 與獨立 staging 執行。
6. staging 留有一筆名稱為 `P0 Staging Smoke` 的測試會員，production 沒有這筆資料。

## Claude 整併注意事項

1. 請以 PR #9 的 **最終整體 diff** 審查與整併，不要只 cherry-pick 第一筆 commit。
2. 第一筆 commit `a1c5aa3` 的歷史訊息曾提到 refunded status；最終 cleanup commit `ae32757` 已移除該 unrelated refund 功能。只拿第一筆會把不在本次範圍的退款功能帶回來。
3. 不要從 `codex/member-v1-review` 整併；該分支曾混入另一個 session 的退款修改。正確分支是 `codex/member-v1-p0-security`。
4. 原始 `D:\phbay-travel` main checkout 仍有其他 session 的 untracked files，例如 `CLAUDE_REVIEW.md`、設定步驟文件、圖片與 scratch scripts。這些檔案已完整保留，本工作沒有刪除、reset 或覆蓋；不要為了讓 main 乾淨而擅自清掉。
5. `member_v1.py` 在 `origin/main` 不存在，因此 PR 看起來包含完整 V1 模組。這是讓 security fix 可測、可掛載所必需，但仍應逐段審查是否只保留已核准的 V1 範圍。
6. 不要在重新審查通過前合併 main，也不要直接部署 production。

## 建議重新審查清單

- [ ] 以兩個帳號重放 provider email 相同但 `sub` 不同的情境，確認不會自動合併。
- [ ] 確認既有會員只有在本站 Email OTP proof 有效且 member ID 相符時才能綁定 social identity。
- [ ] 確認 proof 在綁定後被消耗，登出／無效 session 時也會被清除。
- [ ] 確認 LINE invalid issuer、audience、nonce、expired token、missing sub 全部 fail closed。
- [ ] 確認所有受保護 Member V1 routes 只依賴 `require_member()`。
- [ ] 確認 merged／inactive member 的舊 session 在 `/me`、identities、orders、consents、claim、merge 全部失效。
- [ ] 在補齊 staging Email credentials 後完成 register → Email OTP verify/login → member center。
- [ ] 在補齊 LINE／Google credentials 後完成新會員與既有會員 linking E2E。
- [ ] 另開 issue 處理單一 migration runner 與 `posts.faq` fresh-DB migration，不混入本 P0 PR。

## Go / No-Go

- 進 staging：**GO**。
- 合併 main：**待 Claude/security re-review 與真實 Email/OAuth E2E**。
- 部署 production：**NO-GO**，直到上述 re-review、staging credentials 與 E2E 完成。
