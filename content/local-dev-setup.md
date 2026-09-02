# 本機開發環境（2026-09-02 建）

線上驗證只能測到公開的 GET；**後台的流程（匯入、改期、超額確認）不可能在正式站練**——
會寫進真資料。這份是本機可安全實跑全部流程的環境。

## 組成

| 項目 | 位置 | 備註 |
|---|---|---|
| Python 虛擬環境 | `D:\phbay-travel\.venv`（Python 3.11） | `.gitignore` 已忽略 |
| 本機資料庫 | `D:\phbay-devdb\data`，**port 55432** | 與你原本 5432 的 Postgres **完全分開**，互不影響 |
| 連線設定 | `D:\phbay-travel\dev.env` | 被 `.gitignore` 的 `*.env` 忽略，**不會上傳** |
| 啟動器 | `scripts/run_local.py` | 站台跑在 http://127.0.0.1:5001 |
| 測試資料 | `scripts/seed_dev_data.py` | 可重複執行 |

用的是系統既有的 PostgreSQL 18.3 執行檔（`C:\Program Files\PostgreSQL\18\bin`），
只是另外 `initdb` 一份獨立的資料目錄，沒有動到原本那座 cluster 的任何資料。

## 啟動

```bash
"C:/Program Files/PostgreSQL/18/bin/pg_ctl.exe" -D "D:/phbay-devdb/data" -l "D:/phbay-devdb/server.log" start
```

```bash
cd /d/phbay-travel && .venv/Scripts/python.exe scripts/run_local.py
```

停止資料庫：把上面的 `start` 換成 `stop`。

## 重建測試資料

```bash
cd /d/phbay-travel && .venv/Scripts/python.exe scripts/seed_dev_data.py
```

種出來的情境（複製正式站 festival，capacity 5）：

- `2026-09-12` 線上 2 ＋ 線下已售 3 ＝ 5/5 → 額滿
- `2026-09-19` 線上 2 ＝ 2/5 → 剩 3

`test_p0_0_live.py` 會在開頭自動呼叫這支重種——它本身會下單／匯入／改期改變資料庫狀態，
不重種的話第二次跑會冒出一堆假失敗。

`seed_dev_data.py` 會拒絕對非 `localhost:55432` 的連線字串執行，手滑打到正式庫會直接中止。

## 換一台機器要重做的事

`dev.env` 不在 git 裡，需自行建立：

```
DATABASE_URL=postgresql://phbay_dev:<密碼>@localhost:55432/phbay_dev
FLASK_DEBUG=1
ADMIN_KEY=devkey-local-only
FLASK_SECRET_KEY=dev-secret-local-only
PORT=5001
```

## 為什麼要 `run_local.py` 而不是直接 `python app.py`

`app.py` 內部呼叫 `load_dotenv()`，預設讀根目錄的 `.env`——那份的 `DATABASE_URL`
是 localhost 佔位字串。`run_local.py` 先用 `override=True` 載入 `dev.env` 再 import app，
本機設定才蓋得過去。

---

## 順手抓到的 bug（2026-09-02，架環境時發現並修掉）

**全新資料庫跑 `init_db()` 會自我清空，永遠建不起來。**

`app.py` 有一段「放寬 `preorder_passengers.birth_date` 可為空」的補丁：

```python
try:
    cur.execute("ALTER TABLE preorder_passengers ALTER COLUMN birth_date DROP NOT NULL")
except Exception:
    conn.rollback()          # ← 問題在這
```

這支 ALTER 寫在 `CREATE TABLE preorder_passengers` **上面**，全新資料庫必定失敗；
而 `conn.rollback()` 回捲的是**整個交易**，把它前面所有 `CREATE TABLE` 一起丟掉。
於是下一句 `ALTER TABLE tours ...` 直接噴 `relation "tours" does not exist`，
init_db 整個中止，而且只印一行警告不會讓程式停下來。

**正式站沒事**，因為那些表早就存在、ALTER 會成功、根本不會走到 rollback。
但代表**任何全新環境（新開發機、災難復原重建）都裝不起來**，而且症狀看起來像連線問題。

已修：
1. 改用 `SAVEPOINT`，失敗只回捲那一句，其餘建表結果保留。
2. `CREATE TABLE preorder_passengers` 的 `birth_date` 直接建成可空，
   新舊資料庫 schema 才一致（沿用 2026-08-26 contacts 事故的教訓：
   **建表語句與補欄位清單不同步，正式站與新環境就會長得不一樣**）。

修完驗證：全新資料庫 `init_db()` 成功建出 22 張表，
`preorder_passengers.birth_date` nullable = YES。

---

## P0-0 的四條防線：本機實跑結果（2026-09-02，14 項全過）

線上只能驗到第一項，其餘三項都是這個環境才測得到的。

**B. 公開下單**
- 額滿的 9/12 下單 → 400「此場次剩餘 0 位」（線下已售確實佔住位子）
- 9/19 收滿 3 位 → 成立，`FESTIV20260919-0005`
- 9/19 再收 1 位 → 400 擋下

**C. 後台匯入超額**
- 第一次送 → 409 `needs_confirm`，列出「2026 澎湖追風音樂燈光節主題行程 2026-09-26」
- 此時查訂單 → **0 筆**（整批 rollback 確實生效）
- 帶 `confirm_overbook` 再送 → 200，兩筆都寫入

**D. 後台改期超額**
- 改到額滿的 9/12 → 409「改到 2026-09-12 後共 7 人，超過上限 5，確定仍要改期嗎？」
- 被擋下時日期**沒有**被改掉（仍是 2026-09-19）
- 帶 `confirm_overbook` → 200，日期改成 9/12，修改紀錄留下
  `出發日期：2026-09-19 → 2026-09-12；⚠️ 已確認超額改期：2026-09-12 共 7 人（上限 5）`

伺服器 log 無任何 error。
