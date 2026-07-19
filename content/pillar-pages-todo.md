# Pillar Pages 規格（SEO/AEO/GEO 第二輪）— ✅ 已於 2026-07-19 實作完成

> 2026-07-19 由 Claude 建立規格，同日第二輪實作完成（pillar_pages.py＋app.py 路由）。本檔保留作規格紀錄。
> 實作方式建議：app.py 伺服器渲染路由（沿用 `_render_blog()` 外殼），非靜態 HTML，方便共用導覽與追蹤碼。

## 共通要求（每頁）

- 單一 H1、清楚 H2 結構、開頭「先講結論」段落
- FAQPage schema（3–5 題，內容需與頁面可見文字一致）
- BreadcrumbList schema、canonical、OG/Twitter meta（用主題圖，勿共用 festival-poster）
- 內鏈：至少各 1 連到相關預購頁、部落格相關文章 2–3 篇、行程診斷（/#quiz）、諮詢 CTA
- 上線後：加進 sitemap（app.py `dynamic_sitemap()`）、llms.txt / llms-full.txt 重要頁面清單、GSC 手動要求建立索引
- 內容規範：勿捏造價格、名額、交通時刻；價格一律「約 NT$X 起，以報價為準」

## 頁面清單

1. `/penghu-3days-itinerary` — 澎湖三天兩夜行程規劃｜第一次來澎湖怎麼排
   - Day1/2/3 範例動線（北環、南環、離島擇一）、季節建議、預算區間、常見排法錯誤
   - 可大量內鏈既有景點/美食文章（通梁古榕、大菓葉、風櫃洞、黑糖糕…）
2. `/penghu-family-travel` — 澎湖親子旅遊攻略｜適合小孩的海島、生態與輕鬆行程
   - 按年齡層建議（嬰幼兒/學齡/長輩同行）、潮間帶與 DIY、雨天備案（生活博物館文章內鏈）
3. `/penghu-food-guide` — 澎湖美食地圖｜早餐、小吃、海鮮與在地家常味
   - 依「早餐／小吃／海鮮／伴手禮」分區，直接彙整既有 10+ 篇美食文章成 hub
4. `/penghu-2026-festival-guide` — 2026 澎湖追風音樂燈光節攻略｜日期、交通、住宿與行程安排
   - 官方檔期資訊（觀音亭園區、9/12–10/11）、交通與住宿建議、內鏈 /preorder/festival
   - 注意：活動細節僅寫官方已公布內容
