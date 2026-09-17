# 旅客評價（遊客心得）

真實旅客評價放在 `content/reviews.json`，由 `/reviews` 頁面讀取並輸出
`Review` + `AggregateRating` 結構化資料（schema.org）。有真實資料時，
Google 可能在搜尋結果顯示星等，AI 引擎也會引用來回答「澎湖旅行社推薦哪家」。

## ⚠️ 重要：不可造假

捏造評分或評價違反 Google 政策，會被撤銷 rich result 星等，並可能影響整站
排名。每一筆都必須是**真實旅客**留下的內容（姓名可化名，例如「王小姐」）。

## 格式

`reviews` 是陣列，每筆物件欄位：

| 欄位 | 必填 | 說明 |
|---|---|---|
| `author` | ✅ | 旅客姓名或化名，例：`林先生` |
| `rating` | ✅ | 1–5 的數字（可小數），例：`5` |
| `body` | ✅ | 評價內容，越具體越好（提到行程、嚮導、體驗） |
| `date` | 建議 | 評價日期 `YYYY-MM-DD` |
| `tour` | 建議 | 對應行程名稱，例：`望安兩天一夜` |
| `source` | 選填 | 來源，例：`Google`、`LINE`、`問卷` |

## 範例

```json
{
  "_comment": "真實旅客評價資料。請勿造假。",
  "reviews": [
    {
      "author": "林小姐",
      "rating": 5,
      "date": "2026-05-18",
      "tour": "望安兩天一夜",
      "body": "嚮導對望安超熟，帶我們避開人潮看綠蠵龜保育區，孩子玩得很開心，步調舒服不趕。",
      "source": "Google"
    }
  ]
}
```

只放真實內容；空陣列時 `/reviews` 會顯示邀稿狀態、且不輸出星等 schema。

## 目前狀態：入口已隱藏（2026-09-17）

`reviews` 是空陣列時，`/reviews` 會輸出 `noindex`、不進 sitemap，伺服器端頁面
（部落格、行程、攻略頁）的導覽列與頁尾也不會出現「旅客評價」。

加入第一筆真實評價後，伺服器端頁面會自動恢復入口，但**靜態頁要手動加回**：
`index.html`（導覽列「旅遊大小事」子選單＋頁尾快速連結）、`faq.html`、`tides.html`、
`privacy.html`、`terms.html`、`preorder.html`、`neihai-preorder.html`，以及 `llms.txt`、`llms-full.txt`。
