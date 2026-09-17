# P1 行程診斷交接

## 基準與安全界線

- 基準：`main` / `0713e65f5097ff46b305440f95d827910bc8066d`
- 已確認歷史提交：`0713e65`、`983d016`、`dcdd437`
- 開發分支：`codex/itinerary-p1`
- 未部署 Production、未修改資料庫 schema、後台、會員登入或訂單 API。
- 既有預購成功後的 `gtag('event','generate_lead', { booking_ref: ... })` 保持不變；`PhbayAnalytics` 仍封鎖 `booking_ref`、日期與 PII。

## 已完成範圍

### P1-1 診斷結果帶入諮詢表單

- 結果頁點「請潮旅幫我微調」時，將診斷答案與推薦商品寫入 `sessionStorage` 的 `phbay_itinerary_prefill_v1`。
- 首頁填入出發日、依天數計算回程日、人數區間、交通、預算、商品 `tour_id` 與診斷摘要。
- 只有非 PII 的 `tour_id` 放在 URL；日期、人數與摘要不進 query string。
- 不填姓名電話、不勾契約、不自動送出表單。
- payload 兩小時過期；沿用既有 `?tour_id=` 動態商品預選，沒有診斷 payload 時不介入舊流程。

### P1-2 手機結果頁 CTA

- `max-width:760px` 時在結果 hero 下方直接顯示三個快捷 CTA。
- 使用 `data-ir-action`，沒有重複 element ID；同一動作共用事件參數。
- CTA 不採 fixed，避免遮住既有 WhatsApp 浮動按鈕；按鈕高度至少 46px，配色符合目前 AA 設計基準。
- 手機側欄保留「重新診斷」按鈕。

### P1-3 真實商品與規則推薦

商品設定集中在 `RECOMMENDED_PRODUCTS`，名稱、售價與上架狀態從 `/api/tours` 即時讀取，不在前端手抄價格。

| 旅型 | primary 商品 | item_id | 海上商品 | CTA |
|---|---|---|---|---|
| 親子安心慢遊 | 親子海島體驗行程 | `tour_3` | 是 | 查看行程與洽詢 |
| 經典初訪收藏 | 小城故事・內海巡禮 | `tour_21` | 是 | 直接預訂 |
| 跳島海洋冒險 | 南方四島＋七美深度遊 | `tour_12` | 是 | 查看行程與洽詢 |
| 海景拍照約會 | 花火船・海上賞澎湖花火 | `tour_17` | 是 | 查看行程與洽詢 |
| 聚落美食慢旅 | 澎湖慢旅 4 日 | `tour_67` | 是 | 查看行程與洽詢 |

- primary 不在 API 或非 active 時，依 `fallback` 順序選下一個 active 商品；一般流程的最終商品備援為內海巡禮。
- `seasick`、`long_boat` 或 `water` 任一避開條件成立時，不推薦 `boat:true` 商品。公開商品檢查後沒有能同時保證符合所有避水條件的現成商品，因此誠實改成 `land_itinerary_consultation`「陸上行程客製建議」，不硬推海上商品。
- `product_view`、點擊事件使用實際 `item_id` 與 API 商品名稱。

### P1-4 價格模型

`PRICE_MODEL.confirmed=false`，一般訪客只看到自己選的預算與 `/api/tours` 回傳的商品售價，不顯示推估總價。只有 `?price_preview=1` 顯示以下內部試算，且 preview 模式不送 GA4 事件。

| 項目 | V1 假設 | 來源狀態 |
|---|---:|---|
| 住宿 | NT$1,200–2,400／人／晚 | 規劃假設 |
| 餐食 | NT$600–1,000／人／日 | 規劃假設 |
| 島上交通 | NT$300–600／人／日 | 規劃假設 |
| 未訂機票 | NT$4,000–7,000／人 | 規劃假設 |
| 未訂船票 | NT$1,800–3,200／人 | 規劃假設 |
| 交通未定 | NT$1,800–7,000／人 | 規劃假設 |
| 交通已訂 | 試算不再加計 | 使用者狀態 |
| 推薦商品 | API `price_display` 的 `NT$` 金額 | 官網即時資料 |

- 試算依天數計算晚數與每日費用，並依成人＋兒童總人數呈現團體參考總額。
- 預算比對只說明是否有交集／高於／低於，不宣稱正式報價。
- `2026 試航價 NT$1,000` 會正確抓 `NT$1,000`，不會把年份當價格。

## GA4 與隱私

- 保留事件：`quiz_start`、`quiz_complete`、`itinerary_view`、`product_view`、預購頁 `checkout_start`、`line_click`、`preorder_created`。
- 匿名維度：`travel_days`、`party_type`、`children_age`、`budget_range`、`travel_style`、`avoid_preference`、`arrival_method`、`first_visit`。
- 不送姓名、電話、Email、日期、成人／兒童數、訂位代號或 transaction ID。
- 現有系統沒有付款成功 callback；預購成立不是付款，因此依既有安全決策不虛送 `purchase`。日後串付款時，應只在付款成功 callback 送出 `purchase`。

## 測試結果

- `node --check itinerary-quiz.js itinerary-prefill.js script.js`：通過。
- `node test_itinerary_quiz.js`：通過；含五旅型、active fallback、避船、即時商品價、年份解析、預算模型、回填映射與 GA4 PII 過濾。
- `python -m unittest discover -v`：`Ran 160 tests`，0 failure，18 skipped。18 項皆因本機沒有 `MEMBER_V1_TEST_DATABASE_URL`；原始 154 項與新增 6 項均通過。
- `python validate_repo_posts.py`：79 篇文章驗證通過。
- `git diff --check`：通過；僅 Windows 工作樹 LF/CRLF 提示。資產版本已升至 `20260917f`。
- 390×844 實機流程：五種旅型、hero 下 CTA、暈船陸上備案、一般／preview 價格、微調回填與未自動送出均已驗證。

## Staging 驗證清單

1. 用 staging 真實資料庫逐一跑五種旅型，確認商品名稱、價格、active fallback 與 CTA。
2. 驗證 `tour_21` 直接進內海預購；其他商品進 `/tours/<id>`，文案不宣稱可直接付款。
3. 390px、430px、768px 與桌面寬度檢查 CTA、WhatsApp 浮鈕、鍵盤焦點與對比。
4. 以實際日期完成診斷，點微調，確認日期、回程日、人數、交通、預算、商品與備註正確；確認表單未送出、姓名電話仍空白。
5. 直接開 `/?tour_id=<有效 id>#contact`，確認沒有 session payload 時仍只做舊有商品預選。
6. `?price_preview=1` 確認明細與假設；一般 result 不可出現試算總額；GA4 DebugView 不應收到 preview 的事件。
7. GA4 DebugView 核對匿名參數；確認沒有日期、party count、booking ref 或其他 PII。
8. LINE 登入、Google 登入、會員中心、內海預購、通用預購、聯絡表單、隱私權與使用條款做 smoke test。
9. Production 發布前再由 Claude／人工 reviewer 檢查差異；本分支不要直接合併或觸發 Railway。

## 未納入

- P2-1 tours 多語系不是本輪必要範圍，未實作。
- 未部署、未更動 Railway、未推送 `main`。
