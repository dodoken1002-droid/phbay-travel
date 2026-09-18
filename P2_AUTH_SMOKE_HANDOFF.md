# P2-1 LINE／Google 登入 smoke test 交接

## 基準與範圍

- 基準：`origin/main` / `66dfa87748e9917bd4a64160147af3f8adcb4902`
- 分支：`codex/p2-auth-smoke`
- 僅處理 OAuth 登入 smoke test、錯誤回饋與自動化 regression。
- 不建立會員、不修改資料庫 schema、不變更 Production／Railway 環境變數。

## 目前正式站狀態

2026-09-18 唯讀檢查 `/member/dashboard` 與 `/api/member/oauth/providers`：

- LINE OAuth：disabled，前台入口依安全設計移除。
- Google OAuth：disabled，前台入口依安全設計移除。
- 因兩個 provider 都未設定，真實授權、callback、登入、註冊及綁定流程尚不能做端到端 smoke test。

## 本分支完成內容

- 新增 `scripts/oauth_smoke_test.py`：
  - 不跟隨到第三方登入、不送 authorization code、不建立會員。
  - 檢查 provider availability。
  - provider 啟用時檢查 HTTPS、正確 authorize host、state、nonce、PKCE S256、scope 與 redirect URI。
  - 使用同一個短效 session 驗證「使用者取消授權」會安全回到 `oauth_error=denied`。
  - 不輸出 state、nonce、client ID、token 或使用者資料。
- 補強 LINE／Google route regression：OAuth state、nonce、PKCE、無效 state、取消授權與 state 單次消耗。
- 會員頁現在會以繁中、英文、日文、韓文與簡中顯示所有 OAuth callback 錯誤，不再取消或失敗後毫無提示。

## 啟用前必要設定

請在 LINE Developers／Google Cloud 建立或核對正式應用，callback 必須精確設定：

- `https://www.phbay.info/api/member/oauth/line/callback`
- `https://www.phbay.info/api/member/oauth/google/callback`

伺服器需要以下環境變數；值不得寫入 repo、log 或交接文件：

- `LINE_OAUTH_CLIENT_ID`
- `LINE_OAUTH_CLIENT_SECRET`
- `LINE_OAUTH_REDIRECT_URI`
- `GOOGLE_OAUTH_CLIENT_ID`
- `GOOGLE_OAUTH_CLIENT_SECRET`
- `GOOGLE_OAUTH_REDIRECT_URI`

## 執行方式

憑證尚未設定時，只確認安全降級：

```text
python scripts/oauth_smoke_test.py --base-url https://www.phbay.info --allow-disabled
```

Staging 啟用憑證後（disabled 應視為失敗）：

```text
python scripts/oauth_smoke_test.py \
  --base-url https://staging.example.com \
  --expected-redirect-base https://staging.example.com
```

## 待人工端到端驗證

每個 provider 使用專用測試帳號，逐項記錄但不得截錄 token、OTP 或完整 Email：

1. 新會員授權後補齊資料、同意個資並完成註冊。
2. 既有 provider identity 再登入後進入會員中心。
3. 已登入會員綁定新 provider 時，必須先完成 10 分鐘內的 Email OTP step-up。
4. provider Email 與既有會員相同時，不得自動連結或接管帳號。
5. 取消授權、失效 state、provider 錯誤及拒絕 scope 都有安全且可理解的訊息。
6. 登出後會員 API 回 401，舊 session 不可再使用。
7. 手機與桌面各跑一次；URL、console、GA4、server log 不得出現 token、OTP、完整 Email 或其他 PII。

## Gate

在 LINE／Google 憑證與專用測試帳號備妥、端到端項目全部通過前，不建議把 OAuth 按鈕對正式旅客開放。
