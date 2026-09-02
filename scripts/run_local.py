# -*- coding: utf-8 -*-
"""本機開發用啟動器：讀 dev.env 後啟動 Flask。

為什麼要這支而不是直接 `python app.py`：
app.py 內部呼叫 `load_dotenv()`，預設讀專案根目錄的 `.env`——那份是給
正式環境的範本（DATABASE_URL 是 localhost 佔位字串）。這支先以
override=True 載入 `dev.env`，再 import app，本機設定才會蓋過 `.env`。

`dev.env` 被 .gitignore 的 `*.env` 忽略，不會上傳；請自行建立，內容見
`content/local-dev-setup.md`。

用法：.venv/Scripts/python.exe scripts/run_local.py
"""
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
DEV_ENV = ROOT / 'dev.env'

if not DEV_ENV.exists():
    sys.exit(f'找不到 {DEV_ENV}。請先照 content/local-dev-setup.md 建立本機環境。')

# override=True：本機設定必須蓋過 app.py 之後 load_dotenv() 讀進來的 .env
load_dotenv(DEV_ENV, override=True)

os.chdir(ROOT)
sys.path.insert(0, str(ROOT))

import app  # noqa: E402  （必須在 load_dotenv 之後才 import）

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print(f'[dev] 本機站台 http://127.0.0.1:{port}  （資料庫：本機 dev cluster，非正式庫）')
    # use_reloader=False：reloader 會再 import 一次 app，init_db 也會再跑一次
    app.app.run(host='127.0.0.1', port=port, debug=False, use_reloader=False)
