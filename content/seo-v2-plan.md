# 潮旅網站 SEO/GEO/AEO V2 改造清單（2026-08-15 建）

> 給 Claude / Codex / Hermes 的工單總表。逐頁列「目前 → 要改什麼 → Title/H1 → Schema → FAQ → CTA」。
> 依 P0 → P1 → P2 順序做；每項做完在此檔打勾並註記 commit。
> **鐵則：所有新增的前端文案一律五國語言（繁中/en/ja/ko/zh-cn），流程見 skill `phbay-i18n`；伺服器渲染頁（pillar/商品頁）暫時繁中，但 Title/meta 要留 hreflang 擴充空間。**

## 0. 事實查核（2026-08-15，與外部健檢報告的出入）

- ✅ `blog.phbay.info`：**DNS 根本不存在（NXDOMAIN）**，不是 502。若 GoDaddy 端沒有這筆 CNAME，Google 也連不到，殘留索引會自然掉。處理方式見 P0-1。
- ✅ 首頁「敬請期待」：DB 其實已有 **20 筆行程**（featured 7、2d1n 2、3d2n 4、4d3n 3、north-sea 1、south-sea 5、main-island 5），只有 **east-sea 是 0 筆**。真正問題是：
  1. 行程區塊是**純前端 fetch('/api/tours') 渲染**——不執行 JS 的爬蟲（含多數 AI crawler）看到的是空殼＋佔位文案；
  2. **所有行程 price 皆為 None**，卡片沒有價格；
  3. **沒有單一行程的獨立頁面**（無 /tour/<id>，只有 /preorder/festival 與 /neihai-preorder 兩個預購頁）。
- ✅ 「先講結論」格式、快速答案、FAQ 100 問、pillar 4 頁、Event/FAQPage schema 都已上線——AEO 底子成立，報告評價正確。

---

## P0（本週）

### P0-1 blog.phbay.info 收尾
- 目前：NXDOMAIN。
- 要做：
  - [ ] 先查 GSC / Ahrefs-free / `site:blog.phbay.info` 確認是否還有已索引 URL 或 backlink。
  - [ ] 若有 → GoDaddy 加 CNAME `blog` → Railway，app.py 依 `Host` header 301 到 `www.phbay.info/blog/<對應路徑>`（找不到對應就 301 到 /blog）。
  - [ ] 若查無殘留 → 不建 DNS，記錄結論後關閉此項（沒有 DNS 就沒有 502 問題）。
- 負責：Claude（app.py 301 中介層）＋使用者（GoDaddy DNS）。

### P0-2 首頁行程區改伺服器渲染（讓爬蟲看得到 20 筆行程）
- 目前：`index.html` 靜態空 grid，script.js fetch /api/tours 填入；爬蟲看到「行程陸續上架中」。
- 要做：
  - [ ] app.py 首頁改為伺服器端注入行程卡 HTML（沿用現有 `get_tours()` 分組；做法比照 `/preorder/festival` 的 `<!--PREORDER_SEO_SECTION-->` 注入模式，前端 JS 改為增強而非唯一渲染）。
  - [ ] east-sea 分頁：後台補 1–2 筆（員貝/鳥嶼潮間帶類）或先隱藏該分頁，不要露出「敬請期待」。
  - [ ] 佔位文案「行程陸續上架中」只允許在真的 0 筆時出現。
- Schema：首頁加 `ItemList`（行程清單）。
- 注意：行程卡文字目前吃 DB（單語）；卡片 chrome（按鈕/標籤）仍走 i18n 五語。

### P0-3 每筆行程補「商品卡最小資訊」
- 目前：tours 表有 title/desc/tabs，**無價格、時數、成行人數、適合對象**。
- 要做：
  - [ ] tours 表加欄位（或沿用 JSONB）：`price_from`、`duration`、`min_pax`、`audience`（親子/情侶/長輩/員旅…）、`highlights[]`。
  - [ ] 後台行程編輯器補這些欄位。
  - [ ] 卡片模板：商品名稱 → 適合對象 → 時數/天數 → NT$ 價格起 → 成行人數 → 特色 → CTA（詳情/諮詢）。
  - [ ] 內容由使用者/訂位人員提供價格；未提供前顯示「兩人成行・線上詢價」不留空白。

### P0-4 建立獨立商品頁 `/tour/<slug>`（8–12 頁）
- 目前：無單品頁，SEO 只能靠首頁一個區塊。
- 要做：
  - [ ] app.py 新路由 `/tour/<slug>`，伺服器渲染，資料吃 tours 表＋新欄位。
  - [ ] 統一模板（= 報告第八節）：
    - H1：品牌名（例：小城故事・內海巡禮）
    - `<title>`：SEO 化長式（例：`2026 澎湖內海巡禮｜小城故事遊艇｜跨海大橋・大菓葉玄武岩・果凍海｜90 分鐘海上行程｜潮旅`）
    - Quick Answer 表：適合誰｜時數｜價格｜集合地點｜成行人數｜季節
    - 為什麼推薦（3–5 特色）／行程時間表／費用包含・不包含／適合對象／FAQ 6–10 題（可見＋FAQPage schema 同源一份資料，比照 `FESTIVAL_FAQ` 模式）／相關攻略 3–5 篇（用 `_pillar_link_for_tags()` 邏輯反向）／相關商品 3 個／CTA（立即預訂或預購頁、LINE 諮詢）
  - [ ] Schema：`TouristTrip` + `Product`（含 `offers.price`，有價格才放）+ `BreadcrumbList` + `FAQPage`。
  - [ ] 首批 8–12 頁優先序：內海巡禮、夜釣小管、花火船、南方四島＋七美、七美望安桶盤、北海吉貝、親子海島體驗（3天2夜）、望安生態、追風音樂節 3天2夜×2、SUP×浮潛、4天3夜深度。
  - [ ] sitemap.xml 加入 /tour/*（priority 0.8），首頁行程卡連到對應 /tour/<slug>。

### P0-5 商品 Title SEO 化（低成本先做）
- 目前：行程名多為品牌型（「跟著海龜漫旅」）。
- 要做：
  - [ ] tours 表加 `seo_title` 欄，`<title>`/og:title 用 seo_title，H1 保留品牌名。
  - [ ] 命名公式：`2026 澎湖{類型}｜{品牌名}｜{地標1・地標2・地標3}｜{時數/天數}`。
  - [ ] 20 筆行程逐筆補 seo_title（Claude 草擬 → 使用者過目）。

---

## P1（本月）

### P1-1 `/penghu/` Hub Page（Topic Authority 核心）
- 目前：pillar 4 頁各自獨立，無總入口。
- 要做：
  - [ ] 新路由 `/penghu`（pillar_pages.py 加一頁），H1「2026 澎湖自由行完整攻略」。
  - [ ] 五大群組連結矩陣（不是長文）：旅遊型態（第一次/3天2夜/4天3夜/親子/情侶/長輩）→ 景點（馬公/北環/南環/七美/望安/吉貝）→ 體驗（夜釣小管/SUP/浮潛/潮間帶/跳島/內海巡禮）→ 交通（各出發地/飛機/船）→ 季節（花火節/暑假/秋季音樂節/冬天）。
  - [ ] 每格連到：已有 pillar 頁或 blog 文 → 沒有的先連 /tour 商品頁或 FAQ 錨點；缺口記到 P1-2 清單。
  - [ ] Schema：`CollectionPage` + `BreadcrumbList`；全 pillar/blog 頁補「回澎湖攻略總覽」麵包屑。
  - [ ] 導覽列加「澎湖攻略」入口。

### P1-2 支柱頁補強（既有 4 頁 → 目標 7 頁）
- 已有：/penghu-3days-itinerary、/penghu-family-travel、/penghu-food-guide、/penghu-2026-festival-guide。
- 要做：
  - [ ] 新增「澎湖自由行總攻略」（=/penghu Hub 兼任或獨立長文擇一，避免自相蠶食）。
  - [ ] 新增「澎湖跳島攻略」pillar（現有 blog 跳島文升級或做 pillar 收編該文）。
  - [ ] 新增「澎湖交通全攻略」pillar（航班/船班/島上租車包車）。
  - [ ] 每頁文末固定接 2–3 張商品卡（內容→商品閉環）。

### P1-3 真實旅客評價（UGC 起步）
- 目前：/reviews 頁已存在（Codex 作），但首頁/商品頁沒有引用，量少。
- 要做：
  - [ ] reviews 資料表補欄位：出發日期、出發地、人數組成（2大2小）、參加行程 slug、星等。
  - [ ] 首頁加「最近出發的旅客」區塊（伺服器渲染 3–5 則）。
  - [ ] 商品頁模板引用該行程的評價（有才顯示）。
  - [ ] Schema：有評價的商品頁加 `aggregateRating`＋`review`（**只放真實資料，嚴禁生成假評價**）。
  - [ ] 營運面：出團後 LINE/WhatsApp 請客人留一句話＋同意刊登（使用者執行）。

### P1-4 「為什麼可以相信潮旅」信任頁
- 目前：證照資訊散在頁尾與 JSON-LD。
- 要做：
  - [ ] 新頁 `/about-trust`（或首頁區塊）：在地團隊照片/故事、交觀乙第1864號、品保澎字第0188號、旅行業責任保險、官方活動合作旅行社、真實旅客案例，連到觀光署可查證來源。
  - [ ] 首頁信任標章區連到此頁。

---

## P2（下一輪）

- [ ] **FAQ 擴充**：從 GSC 查詢詞挑 10–20 題補進 faq.html（維持 faq-i18n 四語同步）。
- [ ] **作者/嚮導頁**：`/guides` 在地嚮導介紹＋`Person` schema，blog 文章掛 author 連過去（E-E-A-T）。
- [ ] **文章去重**：盤點 content/posts 相近主題（風茹茶 6/20 vs 6/29 這類）→ 留強併弱＋301 或 canonical；建立「一個 keyword cluster＝一個主頁＋衛星頁」的發文規則，寫進 Codex 的發文 SOP（CLAUDE_HANDOFF.md）。**停止無差別日更**，改成先查 cluster 再決定寫新文或增修舊文。
- [ ] **內部連結自動化**：擴充 `_pillar_link_for_tags()` 成雙向（pillar/商品頁 ↔ blog），tag → 商品頁對照表。
- [ ] **hreflang / 多語 SSR**：評估 pillar/商品頁多語版（工程量大，先觀察國際流量再決定）。

---

## 分工建議

| 誰 | 負責 |
|---|---|
| Claude | P0-1 301、P0-2 SSR、P0-4 商品頁模板與路由、schema、sitemap、P1-1 Hub |
| Codex | P0-3 後台欄位＋編輯器、P1-3 評價系統欄位、依模板批量填 8–12 個商品頁內容、文章去重盤點 |
| 使用者 | 價格/時數/成行人數等商品資料、GoDaddy DNS、旅客評價蒐集、seo_title 定稿 |

## 進度記錄

- 2026-08-15：本清單建立（事實查核完成）。
