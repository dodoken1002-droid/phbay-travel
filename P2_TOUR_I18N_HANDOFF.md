# P2-2 行程頁多語系交接

更新日期：2026-09-18

## 範圍

- `/tours` 與 `/tours/<id>` 支援 `zh-tw`、`en`、`ja`、`ko`、`zh-cn`。
- 沿用既有 `tours.i18n` JSONB 與後台翻譯編輯器，不新增資料表或第二套翻譯來源。
- 翻譯缺少時逐欄位回退繁中，頁面不會空白。
- 列表、詳細頁、CTA、篩選、麵包屑、導覽、頁尾、結構化資料與語言網址同步切換。
- 非預設語言使用 `?lang=`；篩選頁保留 `type`，例如 `/tours?type=south-sea&lang=en`。
- 列表頁輸出所有支援語言的 `hreflang`；詳細頁只替實際有內容的翻譯輸出 `hreflang`，並保留繁中與 `x-default`。
- 後台多語編輯器新增 `badge_text`，首頁動態卡片與獨立行程頁共用該翻譯。
- 靜態資源版本更新為 `20260918a`，確保瀏覽器載入新的首頁標籤翻譯邏輯。

## 資料規則

每種語言可維護：

- `title`
- `badge_text`
- `description`
- `suitable_for`
- `duration`
- `price_display`
- `prices`（API 已支援；現有後台未提供逐列價格翻譯欄位）
- `modal_data.highlights`
- `modal_data.dates`
- `modal_data.days`
- `modal_data.includes`
- `modal_data.notes`

`modal_data.contact`、圖片、海報與其他非翻譯資料會保留繁中主資料中的值。翻譯物件不會覆寫原始資料。

## 自動驗證

- `python -m unittest discover`：168 項通過，18 項因未設定 `MEMBER_V1_TEST_DATABASE_URL` 跳過。
- 行程頁專項：17 項通過（含原有回歸、逐欄回退、XSS 跳脫、語言 URL、hreflang、404/503 與內海預購連結）。
- Python 語法檢查。
- `script.js` JavaScript 語法檢查。
- P1 診斷 JavaScript 規則測試通過。
- 79 篇文章資料驗證通過。
- `git diff --check` 通過（僅 Windows LF/CRLF 提示）。

## Staging 驗證清單

1. `/tours` 語言選單可切換五種語言，手機寬度 390、430、768 px 不溢出。
2. `/tours?type=south-sea&lang=en` 保留篩選與語言；切換其他語言後 `type` 不遺失。
3. 一個有完整英文翻譯的行程：卡片、標籤、詳細頁、日程、CTA 與 SEO title 顯示英文。
4. 一個只有部分翻譯的行程：已翻欄位顯示目標語言，缺少欄位安全回退繁中，不出現空標題或空區塊。
5. 詳細頁切換語言後，所有同類行程與相關文章連結保留 `lang`。
6. 檢查頁面原始碼：canonical、`html lang`、`og:locale`、JSON-LD 與 hreflang 正確。
7. 後台編輯英文 `badge_text` 後，首頁與 `/tours` 卡片都顯示相同翻譯；繁中資料不被改寫。
8. 未填翻譯的語言仍可開啟，並以翻譯介面＋繁中內容回退呈現。
9. 繁中 `/tours`、預購連結、LINE、線上諮詢與既有 `/blog` smoke test 正常。

## 尚未包含

- 不代填所有現有行程的翻譯文案；需由內容維護者逐筆確認後發布。
- P2-3「百旅整體加入與行銷活動」不在此分支。
- 本分支不部署 Production。
