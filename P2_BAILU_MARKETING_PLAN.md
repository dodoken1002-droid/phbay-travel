# P2-3 澎湖百旅整體加入與行銷活動規劃

更新日期：2026-09-18

## 結論

不重建會員系統。現有網站已具備會員註冊、Email OTP、LINE／Google OAuth 開關、會員中心、旅次與點數帳本、舊訂單認領、後台管理、首頁與行程入口、五語文案及 LINE 指令。

本階段採用「旅行護照啟程計畫」作為第一個可衡量活動，先讓新客建立旅行護照、舊客認領過去訂單；在點數折抵與福利成本尚未定案前，不承諾現金價值、折扣或贈品。

活動識別：`passport_launch_2026q4`

## 旅客動線

1. 在首頁、會員頁、完成訂單後通知或 LINE 官方帳號看見「建立旅行護照」。
2. 新客以 Email 驗證建立會員；已是會員者登入。
3. 舊客登入後使用「認領過去訂單」，以遮罩目的地收到 OTP，不在 GA4 傳送訂單號、Email、手機或會員編號。
4. 經潮旅報名且完成、並符合認列政策的旅程，才會寫入旅行護照與當期點數。
5. 會員可查看下一趟推薦，再進入既有諮詢流程。

## 活動文案原則

- 主標：把走過的澎湖，收進你的旅行護照。
- 新客 CTA：建立我的旅行護照。
- 舊客 CTA：登入並認領過去訂單。
- 固定揭露：點數用途與會員活動依當期公告；不預先承諾固定現金折抵或未公告優惠。
- 不使用「免費送點」「現折」「保證升等」等未經成本與法務確認的說法。
- 所有渠道都寫清楚「經潮旅報名並完成、經確認後認列」。

## 推進階段

### Gate 0：上線前

- 完成 Email OTP 新會員、既有會員登入、舊訂單認領與登出 smoke test。
- LINE／Google OAuth 憑證未設定時維持按鈕隱藏；補齊憑證與測試帳號後再宣傳社群登入。
- 確認後台每個預購商品的 `counts_as_trip` 政策。
- DebugView 確認事件沒有姓名、Email、手機、會員編號、訂單編號或驗證碼。

### 第一週：站內 soft launch

- 只開會員頁活動區與既有首頁百旅入口，不投放廣告、不群發。
- 建立 GA4 基準：瀏覽 → CTA → 註冊開始 → 註冊送出 → 登入完成 → 訂單認領完成。
- 每日查看 API error log、OTP 寄送失敗、認領失敗原因與客服負擔。

### 第二週：舊客喚回

- 由營運人員先選可確認訂單的舊客名單，透過既有且已取得同意的 LINE／Email 渠道分批發送。
- 第一批採小量，不匯出或另建含 PII 的行銷名單；連結使用活動 UTM，但網站 GA4 事件仍不送 PII。
- 內容主打「找回過去旅程」，不以折扣作誘因。

### 第三週：新客承接

- 在訂單成立頁、出發前通知、旅程完成後通知加入旅行護照 CTA。
- 旅程完成後才提醒認列，避免把預購誤說成已取得點數。
- 根據前兩週漏斗與客服回饋決定是否擴大首頁曝光。

## GA4 事件

共同匿名參數：`campaign_id`、`language`、`auth_state`。允許額外參數僅限 `cta`、`method`、`provider`、`order_type`。

| 事件 | 時機 |
|---|---|
| `member_program_view` | 會員頁載入 |
| `member_campaign_cta_click` | 新客／舊客活動 CTA |
| `member_signup_start` | 首次操作註冊表單 |
| `member_register_submitted` | 註冊資料通過伺服器、等待 Email OTP |
| `member_signup_complete` | OAuth 補資料完成 |
| `member_login_start` | 首次操作登入表單 |
| `member_login_code_requested` | 登入碼請求成功 |
| `member_login_complete` | Email OTP 登入成功 |
| `member_dashboard_view` | 已登入會員中心載入成功 |
| `member_oauth_click` | 點選已啟用的 LINE／Google 登入 |
| `member_order_claim_start` | 開始認領舊訂單 |
| `member_order_claim_code_requested` | 認領驗證碼請求成功 |
| `member_order_claim_complete` | 舊訂單認領完成 |
| `member_line_bind_start` | 開始綁定 LINE OA |
| `member_line_bind_code_created` | 綁定碼建立成功 |

不得傳送：姓名、Email、手機、會員編號、訂單編號、OTP、LINE user ID、Google subject、完整錯誤訊息。

## 判讀指標

第一週先建立基準，不預設不可信的轉換率目標。之後每週比較：

- CTA 點擊率＝`member_campaign_cta_click / member_program_view`
- 註冊送出率＝`member_register_submitted / member_signup_start`
- Email 登入完成率＝`member_login_complete / member_login_code_requested`
- 舊單認領完成率＝`member_order_claim_complete / member_order_claim_start`
- LINE 綁定碼建立率＝`member_line_bind_code_created / member_line_bind_start`

若 OTP 或認領完成率突然下降，先暫停外部導流，處理流程問題；不要用更多投放掩蓋故障。

## Staging 驗證清單

1. 390、430、768 px 下活動區、三步驟卡片與 CTA 不水平溢出。
2. 五語切換後活動區無缺字；重新整理仍保留語言。
3. 未設定 OAuth provider 時按鈕保持隱藏，Email OTP 仍可使用。
4. 新會員註冊送出後不直接登入，完成 Email OTP 才建立登入狀態。
5. 已登入會員可看到舊訂單認領；未登入者不可呼叫認領 API。
6. 認領碼目的地只顯示遮罩；頁面與 GA4 不出現訂單號、Email、手機、會員編號或 OTP。
7. GA4 DebugView 的事件名稱與允許參數符合本文件。
8. 取消、錯誤碼、重試不會誤送 `member_order_claim_complete`。
9. LINE 綁定只在後端建立綁定碼成功後送完成事件。
10. 隱私權、使用條款、會員中心、預購與 P1 診斷 smoke test 正常。

## 本機驗證結果

- `python -m unittest discover`：165 項通過，18 項因未設定 `MEMBER_V1_TEST_DATABASE_URL` 跳過。
- 會員活動合約測試：5 項通過。
- 會員頁 inline JavaScript、`script.js` 語法檢查通過。
- P1 診斷規則測試、79 篇文章驗證、`git diff --check` 通過。
- 本機桌面預覽：活動區無水平溢出、三步驟與雙 CTA 正常；英文切換與揭露文案正常；瀏覽器 console 無錯誤。
- 手機 390／430／768 px 與真實會員 API 流程仍保留於 staging 清單，不以靜態預覽假裝完成。

## 後續需營運決定

- 點數兌換價值、到期規則與會計處理。
- 各等級的實際福利、成本上限與適用商品。
- 是否允許補登多年前的人工訂單，以及需提供的證明。
- LINE／Email 行銷名單的同意來源、退訂與發送頻率。
- 第一批舊客喚回名單與客服承接量。

在上述決策完成前，程式維持「記錄旅次＋當期點數」而不顯示固定折抵承諾。
