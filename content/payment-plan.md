# 潮旅網站 線上收款（結帳＋金流）工單（2026-09-02 建）

> 給 Claude / Codex / Hermes 的工單。依 P0 → P1 → P2 順序做；每項做完在此檔打勾並註記 commit。
> **鐵則 1：所有新增前端文案一律五國語言（繁中/en/ja/ko/zh-cn），流程見 skill `phbay-i18n`。**
> **鐵則 2：改 `app.py` 的 `CREATE TABLE` 加欄位時，必須同步加進該表的「舊資料庫補欄位」ALTER 清單。**
> （2026-08-26 contacts 表事故的教訓：`CREATE TABLE IF NOT EXISTS` 不會修改已存在的表，
> 正式站永遠不會有那個欄位，而且錯誤可能被靜默吞掉一個多月。）
> **鐵則 3：金額一律後端計算。前端送來的任何價格欄位一律忽略，只接受「商品 slug＋日期＋人數」。**

---

## 0. 現況盤點（2026-09-02 讀 code 查核）

### 已經有的（結帳流程的下半段其實蓋好了）

| 能力 | 位置 |
|---|---|
| 商品（行程）＋價格顯示字串 | `tours.price_display`、`tours.prices` JSONB |
| 預購商品／場次／名額上限 | `preorder_products`（capacity／min_people／max_party／date_start-end） |
| 訂單＋旅客資料 | `preorder_orders`＋`preorder_passengers`、`neihai_preorders`＋`neihai_passengers` |
| 訂單編號 | `booking_ref`（`NH202607050900-0012` 格式） |
| 名額動態計算 | `_preorder_availability()`（app.py:3708）、`_preorder_slot_status()` |
| 線下已售人數 | `preorder_manual_holds`（2026-08-27 建） |
| 後台訂單管理／修改紀錄 | `/admin` ＋ `preorder_order_logs` |
| 下單即時通知信 | `send_preorder_email()`，走 Gmail API（HTTPS，不受 Railway 封鎖 SMTP 影響） |
| 公開下單 API | `POST /api/preorder/<slug>/orders`（app.py:3783）、`POST /api/neihai/preorders`（app.py:2636） |

### 完全沒有的

- `preorder_orders` / `neihai_preorders` **沒有任何金額欄位**（只有 `passenger_count`）。
- **沒有任何付款狀態**（`status` 只有 pending_departure／confirmed_departure／cancelled 這類「成團狀態」）。
- **沒有任何金流串接** —— 全檔搜不到 ecpay／綠界／newebpay／藍新／stripe／linepay／payment 任何一個字。
- `requirements.txt` 只有 flask／psycopg2-binary／python-dotenv／gunicorn／google-api-python-client／google-auth。

### ⚠️ 收錢前必須先修的四個既有洞

**A. 預購頁的名額不扣「線下已售」，行程卡卻有扣 → 兩個入口數字不一致，預購頁可超賣。**
`preorder_manual_holds` 只在行程卡路徑用到（app.py:2229、2308），
但 `_preorder_availability()`（3708）與公開下單的容量檢查（3856 附近）**都只 SUM `preorder_orders`**。
結果：老闆在後台登記「線下已售 2 人」，行程卡顯示「剩 3」，預購頁卻仍願意收到 capacity 上限。
2026-08-27 的「單一名額來源」只做完了行程卡那一半。

**B.（2026-09-02 更正）後台「改期」完全沒有容量檢查——兩套系統都一樣。**
本文件初稿寫「內海公開下單沒有交易鎖」是**錯的**：`POST /api/neihai/preorders` 有
`SELECT * FROM neihai_sailings ... FOR UPDATE` 的列鎖（app.py:2688），順序也正確
（先鎖再數再寫），psycopg2 預設不 autocommit，所以鎖是有效的。內海匯入同樣有 FOR UPDATE。
真正的洞在別的地方：**兩套系統的後台 PATCH 都可以把訂單改到另一個日期／船班，
而那段程式完全沒有數過目標場次的人數**。一筆 13 人的單改期到已經滿的船班，
不會有任何警告。研判這才是 2026-07-05 那筆 16/13 的來源之一。

**C. 通用預購的鎖鍵用 Python 字串 hash，擴機會無聲失效。**
`lock_key = abs(hash((p['id'], str(dep_date), dep_time))) % (2 ** 31)`
Python 字串 hash 預設隨機化（未設 PYTHONHASHSEED）。
目前**有效**，因為 gunicorn `--workers 2` 的兩個 worker 是從同一個 master fork 出來、共用同一組 hash seed。
但一旦 Railway 擴成多個實例（不同容器＝不同 seed），同一場次會算出不同的鎖鍵，
**鎖會安靜地失去作用，不會報錯**。改用決定性雜湊（`zlib.crc32(f"{pid}|{date}|{time}".encode())`）。

**D. 後台建立／匯入訂單超額只警告不阻擋**（2026-08-27 已知）。
收錢之後這條要升級成「可強制但需二次確認＋寫入 `preorder_order_logs`」。

> 這四項不修就上金流的後果：客人刷完卡才發現沒位子。退款＋道歉＋商譽，成本遠高於先修。

---

## 1. 先決條件（非工程，需老闆／會計師決定，未定不動工）

| # | 待決 | 影響 | 建議 |
|---|---|---|---|
| D1 | 收**全額**還是**訂金**？訂金定額還是比例？ | 決定 `deposit_amount` 欄位與尾款流程 | 首階段建議**收全額**，尾款流程另外做，不要一次改太多 |
| D2 | **代收轉付收據 vs 電子發票**怎麼開？ | 旅行社團費開的是代收轉付收據，不是統一發票；綠界／藍新的電子發票模組預設走統一發票 | **先問記帳士／會計師再決定要不要開通電子發票模組。** 這是最容易做完才發現卡住的一環 |
| D3 | 退款政策（依定型化契約解約扣款比例） | 決定後台退款欄位與客服話術 | 條文要同步上架到結帳頁與 FAQ（五語） |
| D4 | 第一階段先上哪條行程？ | 決定測試範圍 | 建議**內海巡禮**：單價低、流程最單純、每日班次、出錯損失小 |
| D5 | 金流商選哪家？ | 決定串接工作量 | 首階段**綠界 ECPay**（信用卡＋ATM 虛擬帳號）；外語客第二階段加 Stripe |
| D6 | 誰去申請金流商帳號？ | 審核 1～2 週，是實際交期瓶頸 | 需備：旅行業執照、品保會員證明（品保澎字第0188號）、公司登記、負責人證件、網站網址 |

> 旅遊業在金流商屬**高風險行業**（預收款、履約風險），可能被要求保證金、保留款（roll reserve）或較高費率。
> 費率一律以簽約合約為準，本文件不寫死數字。

> **🚦 2026-09-02 使用者決定：先問記帳士 D2，之後再開 P0-1。**
> **在 D2 有答案之前不要動 P0-1**——Q2／Q6／Q7 的答案會直接改變 `preorder_orders`
> 與 `payments` 的欄位設計，先建表再改要多做一次遷移。
> 要問的題目見〈附錄 C〉，答案回填該表後再動工。

---

## 2. 架構決策（動工前先讀）

1. **不做傳統多商品購物車，做單品結帳（single-item checkout）。**
   旅遊商品不會「行程 A 加一件、行程 B 加兩件一起結帳」，而是「一條行程 → 選日期 → 選人數 → 填團員 → 付款」。
   現有 `/preorder/<slug>` 與 `/neihai-preorder` 就是這條流程，只差最後一步。
   真購物車留到未來要賣「行程＋租車＋伴手禮」組合時再說（見 P2）。

2. **卡號絕不落地。** 一律用綠界轉導頁或 Stripe Checkout Session，
   我們的伺服器不接觸卡號 → 不需要 PCI-DSS 稽核。任何「自己做刷卡表單」的提案直接否決。

3. **付款成功的唯一可信來源是 server-to-server webhook（綠界 `ReturnURL`）。**
   前端導回頁（`OrderResultURL`）**只能用來顯示畫面，不得用來改資料庫** —— 它可以被使用者偽造或中途關閉。

4. **名額必須在進入付款前暫扣。** 詳見 P0-3。

5. **既有的「未付款也算名額」對我們有利。** `_preorder_availability` 算 booked 的條件是
   `status <> 'cancelled'`，所以新增的 `pending_payment` 訂單會自動佔位，
   只要補一支逾時清掃把它轉成取消即可放行名額。

---

## P0（能收到第一筆錢）

### P0-0 修既有名額洞（**擋板項，未完成不得進 P0-3 以後**）✅ 2026-09-02 完成
- [x] 抽 `_slot_booked_pax(cur, product_id, date, time, exclude_order_id=None)`
      統一計算「訂單人數 ＋ `preorder_manual_holds` 線下已售」，
      與 `_manual_hold_pax()`、`_slot_lock_key()` 一起放在 `_preorder_slot_status` 前。
- [x] `_preorder_availability()` 與 `POST /api/preorder/<slug>/orders` 的容量檢查
      改走同一份算法，不再各自 SUM `preorder_orders`。
- [x] 鎖鍵改 `zlib.crc32`（`_slot_lock_key`），移除 `hash()`，並加註解說明為什麼。
- [x] 通用預購匯入補上 `pg_advisory_xact_lock`（原本沒有鎖；內海匯入本來就有 FOR UPDATE）。
- [x] 兩套後台匯入超額 → 整批 rollback ＋ 回 409 `needs_confirm`，
      前端跳確認框後帶 `confirm_overbook` 再送，並把超額場次寫進 `write_audit` 的 detail。
- [x] 兩套後台 PATCH 改期補容量檢查（原本完全沒有）→ 同樣 409 `needs_confirm`，
      確認後把「⚠️ 已確認超額改期」寫進 `preorder_order_logs`／`neihai_preorder_logs`。
- [x] **部署後對帳**（2026-09-02 16:35，deployment 718d635b SUCCESS）：
      `railway variables --service Postgres --json` 取 `DATABASE_PUBLIC_URL`，
      跑 `scripts/check_capacity_conflicts.py`。festival 共用池五個日期數字正確，
      【3】無仍用人工計數的梯次。唯一兩筆警示是**既有歷史資料**、非本次改動造成：
      內海 2026-07-05 09:00 為 16/13、2026-07-07 20:30 為 22/13（8/27 就已知，
      日期已過、船已開，程式修正不會回頭改資料。要不要清理是營運決定）。
      ⚠️ Windows 跑這支腳本要加 `PYTHONIOENCODING=utf-8`，否則 cp950 會在 `⚠` 字元炸掉。
- [x] **部署後端對端驗收**（線上實測，非本機）：`/api/preorder/festival/slots`（預購頁）
      與 `/api/slots`（行程卡）五個日期的 remaining **完全一致，0 筆不符**。
      **關鍵證據 2026-09-12：線上 2 ＋ 線下 3 ＝ 5/5，兩邊都顯示額滿。**
      修好之前預購頁只看線上訂單，會顯示「剩 3 位・確定成行」，
      等於把老闆已經在電話／LINE 賣掉的 3 個位子再賣一次。
- ⚠️ **新的操作注意事項**：匯入的容量檢查現在也把「線下已售」算進去。
      如果老闆把原本記在「線下已售」的那幾筆，之後又用 CSV 匯入成正式訂單，
      同一批人會被算兩次而跳出超額確認框。
      **正確做法：匯入線下訂單後，記得到後台把該日的「線下已售」人數往下調。**
      （沿用 2026-08-27 的換算規則：線下已售 = max(0, 總已售 − 預購訂單人數)。）
- 驗證：`python scripts/test_capacity_logic.py`（唯讀、不連 DB：以 AST 從 app.py 抽出
      改過的函式，配假 cursor 跑），11 項全過
      （含「9/19 remaining 從錯誤的 4 變成正確的 2」與「線下賣滿 → full」）。
- commit: `d267974`
  ⚠️ **這筆 commit 的訊息與內容不符。** 當時有另一個 agent 在同一個工作目錄併行作業，
  用 `git add -A`／`git commit -a` 把本次 P0-0 的改動、本工單與測試腳本，一起捲進了它
  自己那筆「修復後台儲存進度（conversion_value 型別不符）」的 commit 並推上去。
  兩邊改動並存無衝突、程式內容已驗證正確，但已推出去就不改寫歷史。
  **日後查 P0-0 的改動請直接看 `git show d267974` 的 diff，不要只看 commit message。**
  教訓：多個 agent 共用 `D:\phbay-travel` 時，一律 `git add <明確檔名>`，禁用 `-A`／`-a`。

### P0-1 資料表擴充
- [ ] `preorder_orders` 加：`unit_price INT`、`total_amount INT`、`deposit_amount INT DEFAULT 0`、
      `paid_amount INT DEFAULT 0`、`payment_status VARCHAR(20) DEFAULT 'unpaid'`、
      `payment_method VARCHAR(20)`、`paid_at TIMESTAMP`、`hold_expires_at TIMESTAMP`。
- [ ] `neihai_preorders` 同上（或評估把內海併入 `preorder_products` 統一一套，避免長期維護兩份）。
- [ ] 新表 `payments`：`id`、`order_kind`（preorder／neihai）、`order_id`、`provider`（ecpay／stripe）、
      `merchant_trade_no` UNIQUE、`provider_trade_no`、`amount`、
      `status`（pending／paid／failed／refunded／partial_refund）、`raw_callback JSONB`、
      `created_at`、`updated_at`。
- [ ] **每一個新欄位都要同時寫進 CREATE TABLE 與 ALTER 補欄位清單**（鐵則 2）。
- [ ] `payment_status` 值域：`unpaid` / `pending_payment` / `paid` / `refunded` / `expired`。
- 負責：Claude。commit: ______

### P0-2 價格引擎
- [ ] `preorder_products` 加 `price_adult INT`、`price_child INT`、`price_infant INT`，幣別固定 TWD。
- [ ] 後端 `_quote(product, date, pax_breakdown) -> {items[], total}`，**只吃商品 slug＋日期＋人數**。
- [ ] 後台商品編輯器補價格欄位。
- [ ] 未設價格的商品維持現況「線上詢價」，不顯示付款按鈕（不要露出 NT$0）。
- 負責：Claude（後端）＋使用者（各行程實際定價）。commit: ______

### P0-3 名額暫扣（防超賣的核心）
- [ ] 建單時 `payment_status='pending_payment'`、`hold_expires_at = now() + 15 min`，此時**已佔名額**。
- [ ] 逾時清掃：`payment_status='pending_payment' AND hold_expires_at < now()`
      → `payment_status='expired'` 且 `status='cancelled'`（讓既有的 booked 計算自動放行名額）。
- [ ] 清掃觸發方式：每次查名額時順手掃一次（lazy sweep），**不依賴排程**。
      Railway 建置佇列曾卡住數小時（2026-08-19），正確性不要押在排程上。
- [ ] 付款成功 webhook 進來時：清 `hold_expires_at`、`payment_status='paid'`、`paid_at=now()`。
- [ ] 邊界情況：webhook 在 hold 過期後才到（客人拖到第 16 分鐘才付）→ 名額已被別人買走。
      處理＝**收下款項但標記需人工處理，立刻寄警示信給訂位人員**，絕不自動退款也不自動確認。
- 負責：Claude。驗收：兩台裝置同時搶最後一個位子，只有一筆能進付款頁。commit: ______

### P0-4 綠界 ECPay 串接
- [ ] 免加新套件（`hashlib` ＋ `urllib.parse` 自行計算 CheckMacValue 即可）。
- [ ] 環境變數：`ECPAY_MERCHANT_ID`、`ECPAY_HASH_KEY`、`ECPAY_HASH_IV`、`ECPAY_ENV`（stage／prod）。
      **金鑰只進 Railway 環境變數與 `.env`，不得寫進任何檔案或 commit**（比照 admin key 的處理）。
- [ ] `POST /api/checkout/<order_ref>` → 產生 `MerchantTradeNo`（≤20 碼，用 booking_ref 去符號）、
      回傳綠界表單欄位，前端自動 submit 轉導。
- [ ] `POST /api/payment/ecpay/callback`（＝綠界 `ReturnURL`）：
      **先驗 CheckMacValue → 再比對金額與訂單 → 冪等處理（同一 `merchant_trade_no` 重送不得重複記帳）
      → 回傳純文字 `1|OK`**。沒回 `1|OK` 綠界會一直重送。
- [ ] `GET /payment/result`（＝ `OrderResultURL`）：只顯示畫面，**不寫 DB**。
- [ ] 整段包 try/except 並 **print traceback**（2026-08-26 表單事故的教訓：靜默吞例外會讓問題藏一個月）。
- [ ] **實作前先對照綠界官方最新文件核對欄位名稱與簽章規則**，不要憑記憶寫。
- 負責：Claude。驗收：綠界測試環境走完一筆信用卡＋一筆 ATM。commit: ______

### P0-5 結帳頁 UI（五語）
- [ ] `/preorder/<slug>` 送出後不再是「專人聯繫」，改為金額確認 → 付款按鈕。
- [ ] 顯示：單價、人數、總額、成團與退款條款連結、付款方式選擇。
- [ ] 倒數計時（配合 15 分鐘 hold），逾時提示重新下單。
- [ ] 付款失敗／取消的回頭路徑，沿用 2026-08-26 建的常駐備援區塊（LINE／WhatsApp／電話／Email）。
- [ ] **五語**（走 `phbay-i18n` skill）。
- 負責：Claude。commit: ______

### P0-6 後台付款狀態與對帳
- [ ] 訂單列表加付款狀態欄與篩選（未付／已付／逾時／已退）。
- [ ] 訂單詳情顯示 `payments` 交易紀錄。
- [ ] 對帳頁：依日期列出「系統已付訂單總額 vs 金流商入帳」，差額標紅。
- [ ] 權限：付款相關頁面限 `owner` 與 `orders` 角色。
- 負責：Claude。commit: ______

### P0-7 通知信改版
- [ ] 現行「新訂單通知」拆成兩封：`pending_payment` 時寄內部提醒（不寄客人），
      `paid` 時才寄客人「訂單確認信」＋內部通知。
- [ ] 確認信含 booking_ref、行程、日期、人數、金額、集合資訊、退改條款。
      **不得含完整身分證**（沿用現行遮蔽原則）。
- 負責：Claude。commit: ______

---

## P1（上線後一個月內）

- [ ] **Stripe Checkout**：給五語系的境外客（日／韓／英／簡中）。Apple Pay／Google Pay／境外卡體驗最好。
- [ ] **退款登記**：後台按鈕呼叫綠界／Stripe 退款 API，寫 `payments.status='refunded'`。
      ATM／超商不能原路退 → 標記為「需人工匯款」並記錄匯款帳號
      （**帳號屬個資，比照身分證做遮蔽**）。
- [ ] **GA4 電商事件**：`begin_checkout` / `add_payment_info` / `purchase`（含 value、currency、transaction_id）。
      比照 2026-08-26 表單防護的做法，`begin_checkout` 與 `purchase` 的落差＝結帳失敗率，
      付款一壞當天就看得出來。
- [ ] **月結對帳報表**（CSV 匯出）。
- [ ] **`/neihai-preorder` 也上金流**（若第一階段先做通用預購）。
- [ ] **結帳頁 Schema**：商品頁 `Product.offers` 補上真實 price 與 `availability`。

---

## P2（有需求再做）

- [ ] 真・購物車（行程＋租車＋伴手禮組合結帳）。
- [ ] LINE Pay（配合 LINE @phbay2018 導流）。
- [ ] 澎湖百旅會員點數折抵（見 `content/member-program-plan.md`；折抵金額一律後端算）。
- [ ] 訂金／尾款兩段式收款。
- [ ] 分期付款。

---

## 附錄 A：禁止事項

1. ❌ 自建刷卡表單、在自家 DB 存卡號或 CVV。
2. ❌ 相信前端送來的金額。金額一律後端依商品定價重算。
3. ❌ 用 `OrderResultURL`（前端導回）當作付款成功依據。
4. ❌ webhook 不驗簽章就寫 DB。
5. ❌ 金流金鑰寫進任何 commit 的檔案。
6. ❌ 靜默吞掉例外（`except: pass`）。付款流程的每個 except 都要 print traceback。
7. ❌ 在名額洞（P0-0）修完之前開放線上付款。

## 附錄 B：上線前測試清單

- [ ] 綠界測試環境：信用卡成功／失敗／取消，ATM 取號後付款／逾時未付。
- [ ] webhook 重送同一筆 → 不重複記帳（冪等）。
- [ ] webhook 竄改金額 → 驗簽擋下。
- [ ] 兩台裝置搶最後一個位子 → 只有一筆進得了付款頁。
- [ ] hold 逾時 → 名額確實釋放，行程卡與預購頁數字同步。
- [ ] 付款成功後 → 客人收到確認信、後台狀態正確、行程卡名額減少。
- [ ] 五語結帳頁全部檢查（繁中／en／ja／ko／zh-cn）。
- [ ] 正式站切換後**先自己刷一筆小額真卡**再開放
      （2026-08-26 的教訓：沒有端對端測試，表單壞了一個多月沒人知道）。

---

## 交期估算

| 階段 | 內容 | 估時 |
|---|---|---|
| 前置 | 老闆／會計師決定 D1–D6、申請金流商 | 1–2 週（可與工程平行） |
| P0-0 | 修既有名額洞 | 1–2 天 |
| P0-1～P0-7 | 資料表、價格、hold、綠界、結帳頁、後台、通知信 | 2–3 週 |
| 測試 | 附錄 B 全清單 | 3–5 天 |

**金流商審核與工程可以平行**，所以實際交期取決於審核。

---

## 附錄 C：D2 要問記帳士的題目（2026-09-02 建，答案回填此表）

> ⚠️ 以下是**要問的問題**，不是答案。我不是稅務或會計專業，任何一題都以記帳士的回覆為準。
> 每一題後面的「影響什麼」是給工程端看的：答案會直接決定 P0-1 的資料表與 P0-4 的金流模組怎麼開。

### 先給記帳士的背景（三句話）

潮旅（交觀乙第1864號／品保澎字第0188號）想在官網 www.phbay.info 讓客人**線上刷卡付團費**，
第一階段規劃用綠界 ECPay（信用卡＋ATM 虛擬帳號），首波先上單價最低的「內海巡禮」試水溫。
現在完全沒有線上收款，全部是線下收。想先確認憑證與稅務怎麼處理再動工。

### 題目

| # | 問題 | 影響什麼 | 記帳士回覆 |
|---|---|---|---|
| Q1 | 團費收入，我們現在開的是**代收轉付收據**還是統一發票？兩種都有的話，哪些項目歸哪一種？ | 決定要不要開通金流商的電子發票模組 | |
| Q2 | 一筆團費裡，**代收轉付**（機票、住宿、船票、代訂）與**旅行社自己的服務費／毛利**如何切分？切分基準是什麼？ | 決定 `preorder_orders` 要不要拆「代收轉付金額／服務費金額」兩欄 | |
| Q3 | 營業稅上，代收轉付部分不計入銷售額、只就毛利課稅——這個理解對嗎？線上收款會改變這件事嗎？ | 影響金額欄位設計與報表 | |
| Q4 | 客人**線上刷卡當下**就要開憑證，還是可以等**出團後**再開？法規上的時點怎麼算？ | 決定憑證是綁「付款成功 webhook」還是「行程完成」 | |
| Q5 | **代收轉付收據可以電子化嗎？** 有沒有主管機關認可的電子格式，還是一定要紙本？ | 決定要不要做線上寄送收據，或維持人工開立 | |
| Q6 | 綠界／藍新的電子發票模組開的是**統一發票**。以我們的情況，這個模組**該開還是不該開**？ | **這題是 D2 的核心**，決定 P0-4 要不要接發票 API | |
| Q7 | 金流商撥款是**淨額**（已扣手續費）。帳上收入認列要用**總額**還是淨額？手續費列什麼科目？ | 決定 `payments` 表要不要存 `fee` 與 `net_amount` | |
| Q8 | 客人**退款／取消**時，已開的憑證怎麼處理（作廢、折讓、還是另開）？部分退款呢？ | 決定 P1 退款登記要記哪些欄位 | |
| Q9 | 如果分成**訂金＋尾款**兩次收，憑證是各開一次還是最後一次開全額？ | 決定 D1 收全額或訂金的實務成本 | |
| Q10 | 開始線上收款，需要先向國稅局**報備或變更營業項目**嗎？有沒有其他前置申報？ | 可能是動工前的硬性前置 | |
| Q11 | 金流商入帳到公司帳戶後，跟現在的帳務流程怎麼銜接？需要我們每月提供什麼對帳資料？ | 決定 P0-6 對帳頁與 P1 月結報表要匯出什麼欄位 | |

### 回覆後要做的事

- [ ] 把答案填進上表，並更新 D2 那一列的結論。
- [ ] 若 Q6 = 該開電子發票模組 → P0-4 增加發票 API 串接（工時往上加）。
- [ ] 若 Q2 需要拆代收轉付／服務費 → P0-1 的 `preorder_orders` 要多兩個金額欄位。
- [ ] 若 Q7 要記淨額與手續費 → `payments` 表加 `fee`、`net_amount`。
- [ ] 若 Q10 有前置申報 → 排在 D6 申請金流商之前。
