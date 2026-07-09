# 潮旅近期更新記憶

更新時間：2026-07-09  
專案資料夾：`D:\phbay-travel`  
請固定使用這個資料夾，不要使用 C 槽重複 clone。  
目前 main 最新 commit：`118a30e 部落格分頁＋ItemList＋補齊 Twitter Card`

## 【必讀】文章發布與多代理協作約定（2026-07-09 起生效）

本專案由多個 AI 代理（Codex、Claude）與使用者共同編輯，且都直接推 `main`。
2026-07-09 一天內就發生三次 push 撞車（都已安全 rebase 整合），為避免衝突與文章不同步，一律遵守：

1. **push 前先 `git pull --rebase origin main`**，不要盲推。被拒絕（non-fast-forward）時也是先 rebase，不要用 merge commit、更不要 force push。
2. **文章一律走 JSON 流程發布**：`content/posts/*.json` → `python validate_repo_posts.py` → commit → push → Railway 部署時自動 sync 進 PostgreSQL。
   **不要用 admin 後台單獨建文章**——那會造成 DB 有文章但 repo 沒有（7/7 風櫃洞 404 事件的根因就是 repo 與 DB 分岔）。
3. **文章 JSON 必含 `published_at`**（格式如 `"2026-07-09T09:00:00+08:00"`，放在 `is_published` 之後）。缺這欄位時，發布日會變成部署當下時間，日期會錯。
4. **檔案結尾要有換行符（newline at EOF）**。7/8、7/9 兩篇都因缺結尾換行造成不必要的 diff/衝突。
5. sync 機制是 `ON CONFLICT (slug) DO NOTHING`：**只插入新 slug、絕不覆寫 DB 既有文章**。要改已發布文章的內容，得從 admin 後台改，repo JSON 改了也不會生效。
6. 未追蹤的設定筆記（Gmail/LINE/Meta/Railway 各 `.md`、`待辦清單_手動.md`）**不要混進 commit**。

## 2026-07-09 已完成（Claude）

- 7/7 風櫃洞、7/8 通梁古榕文章補 `published_at` 並發布（7/7 線上 404 → 200，sitemap 34 → 35）。
- `/preorder/festival` 補伺服器渲染可見內容：音樂節介紹＋4 題 FAQ＋`FAQPage` JSON-LD（`FESTIVAL_FAQ` 常數同時供可見 HTML 與 schema，兩者逐字一致，改 FAQ 只改這一處）。
- `/blog` 分頁（每頁 15 篇、rel prev/next）＋分類入口列（依 tag 頻率取前 8）＋`ItemList` JSON-LD；頁面從 342KB 降到 24KB。
- `_render_blog` 加 `image` 參數與 Twitter Card；`faq.html`、`tides.html` 補 Twitter Card。
- `tool-blog-topic-backlog.md` 與 README 說明已 commit 進 repo。

## 近期主線摘要

潮旅網站近期已從單純行程展示，逐步補齊成「SEO/AEO/GEO 內容站＋預購訂單系統＋後台管理＋社群導流工具」。

目前重點功能包含：

1. 轉換追蹤
   - Meta Pixel 已補事件。
   - 諮詢表單成功送出後觸發 `Lead`。
   - 通用預購 `/preorder/<slug>` 成功送出後觸發 `Lead`。
   - 行程詳情 modal 開啟會觸發 `ViewContent`。

2. SEO / AEO / GEO
   - 首頁品牌實體、公司資訊、旅行社證號、統編、地址、電話等已明確化。
   - `llms.txt`、`robots.txt`、`sitemap.xml` 已存在。
   - `/preorder/festival` 已補伺服器端 SEO、canonical、OG、Twitter Card、JSON-LD。
   - JSON-LD 包含 `TouristTrip`、`Event`、`BreadcrumbList`。
   - 部落格文章持續新增，近期有西衛麵線、小門鯨魚洞等澎湖知識型內容。

3. 行程診斷與社群導流
   - 首頁已加入/改版「30 秒澎湖旅行人格」行程診斷。
   - 後續 commit 已把診斷升級成 5 題 5 結果。
   - 有結果圖卡、CTA 轉換追蹤、領取行程建議表名單。
   - 目前適合作為社群貼文、Reels、LINE、IG 首頁連結的主要入口。

4. 預購訂單系統
   - 小城故事・內海巡禮與通用行程預購都已有前台表單與後台管理。
   - 通用預購可支援音樂節等 `/preorder/<slug>` 商品。
   - 預購訂單已補客人訂位確認信，Email 為選填。
   - 表單已加入旅遊定型化契約必勾確認。

5. 後台與權限
   - 後台已加入帳號密碼登入。
   - 角色分為 owner / orders / editor。
   - 船班預購開關、訂單管理、內容管理逐步分權限。

6. 訂單匯入 / 匯出 / 編輯
   - 匯出已加日期篩選。
   - 匯出日期改成下拉選單，只列當月實際有訂單的日期。
   - 匯入表頭容錯比對。
   - 匯入支援民國年、同單只填第一列、時段容錯、花火字尾。
   - 匯入日期/時段已強化，可處理純數字民國年、全形字元、時段正規化。
   - 匯入新增「覆蓋既有訂單」模式，可用匯入更新舊單。
   - 訂單可刪除、改日期/時段。
   - 行程結束可封存。
   - 同日班次可用樹狀收合。
   - 行程預購與內海預購都已補修改紀錄，匯入/編輯都留痕。

7. 個資稽核
   - 最新 commit `f1592f1` 加入個資稽核功能。
   - 匯出 / 匯入事件會記錄。
   - 後台已有管理者專屬稽核頁。
   - 後續碰到旅客姓名、身分證字號、生日、電話等資料時，要特別注意權限與稽核紀錄。

## 近期 commit 參考

- `f1592f1`：個資稽核功能：記錄匯出/匯入事件＋管理者專屬稽核頁
- `4390b68`：行程預購也補上修改紀錄，匯入/編輯都留痕
- `5266c94`：匯入新增「覆蓋既有訂單」模式
- `768c746`：匯入日期/時段再強化
- `65b88b3`：匯入強化，支援民國年、同單只填第一列、時段容錯花火字尾
- `f1f39f9`：首頁再精簡，行程自動隱藏空分頁、聯絡表單選填欄位收合
- `46eb575`：首頁版型精簡，去除重複診斷 teaser、測驗上移、關於我們縮短
- `bd6201c`：行程診斷改版：30 秒澎湖旅行人格＋5 題 5 結果＋領取行程建議表名單
- `144ec65`：行程診斷補曝光鏈路：結果圖卡＋CTA 轉換追蹤＋部落格內部連結
- `40b56b9`：提升曝光導流與預購頁 SEO
- `4c6a942`：預購訂單加客人訂位確認信（選填 Email）
- `9225143`：後台船班預購開關＋預訂表單加旅遊定型化契約必勾確認

## 目前本機狀態提醒

截至 2026-07-09 檢查：

- `main` / `origin/main` 指到 `118a30e`。
- `content/posts/README.md` 與 `content/posts/tool-blog-topic-backlog.md` 已 commit 進 repo。
- `CLAUDE_HANDOFF.md` 已 push（供遠端協作代理閱讀）。
- 下列設定/說明檔仍是未追蹤狀態：
  - `Gmail_API_寄信設定步驟.md`
  - `LINE_MessagingAPI_設定步驟.md`
  - `Meta像素_事件接線清單.md`
  - `Railway_Email設定步驟.md`
  - `待辦清單_手動.md`

除非使用者明確要求，不要把上述文件混進功能 commit。

## 建議下一步

1. 部署後優先驗證
   - `https://www.phbay.info/`
   - `https://www.phbay.info/preorder/festival`
   - `https://www.phbay.info/neihai-preorder.html`
   - 後台個資稽核頁
   - 預購匯入 / 匯出 / 覆蓋模式

2. 社群導流策略
   - 使用近期真實出團素材做 Reels / 限動。
   - 主要導流入口建議放「30 秒澎湖旅行人格」行程診斷。
   - 每支短影音只放一個 CTA：
     - 內海巡禮 → `/neihai-preorder.html`
     - 音樂節 → `/preorder/festival`
     - 不知道怎麼選 → `/#quiz`
   - 所有社群連結建議加 UTM。

3. 內容策略
   - 可使用 `content/posts/tool-blog-topic-backlog.md` 的 P0 / P1 主題建立工具型文章。
   - 優先補「交通住宿」「幾月去最好」「雨天玩法」「三天兩夜」「自由行或跟團」。
   - 每篇文章保留快速答案、FAQ、CTA，方便 SEO / AEO / GEO 擷取。

4. 隱私與個資
   - 後續任何匯出旅客資料、批次匯入、修改訂單，都要保留稽核概念。
   - 不要在前端或公開頁暴露身分證字號、生日、電話等完整個資。

## 給接手者的一句話

這個專案目前已進入「能導流、能接單、能管理訂單、能稽核個資」的階段。後續優先順序應該是：穩定訂單資料與個資安全，其次把真實出團素材轉成社群流量，再把流量導回行程診斷、預購頁與 LINE 諮詢。

## 發文協作規則

為了減少 Codex 與 Claude 發布 repository-managed blog posts 時互相撞車：

1. 建立或推送任何新的 `content/posts/*.json` 文章前，先在 `main` 執行 `git pull --rebase`。
2. 新文章 JSON 必須包含台灣時區的 `published_at`，例如 `2026-07-09T09:00:00+08:00`。
3. 新文章 JSON 必須保留檔尾換行。
4. 除非任務明確要求，發文時只提交單一新增文章 JSON。
5. 如果 push 與另一個 agent 的 commit 撞車，先安全 rebase，再重新確認只發布預期的文章 JSON。
