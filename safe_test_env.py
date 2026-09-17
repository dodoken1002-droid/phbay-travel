# -*- coding: utf-8 -*-
"""測試環境防護：跑測試時絕不讓 `import app` 碰到正式資料庫。

背景（2026-09-17 事故）：根目錄 `.env` 的 DATABASE_URL 指向 Railway 正式庫，
每個測試檔都 `from app import app`，而 app.py 在 import 時會 load_dotenv() 並執行
init_db()（DDL＋資料修正）。沒設 SKIP_SCHEMA_INIT=1 跑一次 unittest，就直接改到正式庫。

app.py 在 load_dotenv() **之前**呼叫 `apply_if_testing()`：
  * 不是由測試載入（gunicorn、migrate.py、run_local.py…）→ 完全不做事。
  * 由測試載入 →
      1. 強制 SKIP_SCHEMA_INIT=1；
      2. DATABASE_URL 沒設就填本機 dev 庫，load_dotenv() 不覆蓋既有變數，
         `.env` 的正式庫網址因此不會被讀進來；
      3. DATABASE_URL／MEMBER_V1_TEST_DATABASE_URL 只要不是 localhost 就拋例外、拒絕載入。

其他測試執行器（未走 unittest/pytest、測試檔也不叫 test_*.py）可設 PHBAY_TESTING=1 強制套用。
"""
import os
import sys
from urllib.parse import parse_qs, urlsplit

LOCAL_TEST_DATABASE_URL = 'postgresql://phbay_dev@localhost:55432/phbay_dev'
_LOCAL_HOSTS = {'localhost', '127.0.0.1', '::1'}
_GUARDED_URL_VARS = ('DATABASE_URL', 'MEMBER_V1_TEST_DATABASE_URL')
_RUNNER_DIRS = ('unittest', '_pytest', 'pytest')


def _is_test_frame(filename):
    path = os.path.normcase(os.path.abspath(filename))
    base = os.path.basename(path)
    if base.startswith('test_') and base.endswith('.py'):
        return True
    parent = os.path.basename(os.path.dirname(path))
    return parent in _RUNNER_DIRS


def running_under_tests():
    """呼叫堆疊裡有測試檔或 unittest/pytest 的載入器，就視為測試情境。"""
    if os.environ.get('PHBAY_TESTING') == '1':
        return True
    frame = sys._getframe(1)
    while frame is not None:
        if _is_test_frame(frame.f_code.co_filename):
            return True
        frame = frame.f_back
    return False


def is_local_database_url(url):
    try:
        parts = urlsplit(url)
        host = parts.hostname
    except ValueError:
        return False
    if parts.scheme not in ('postgres', 'postgresql') or host not in _LOCAL_HOSTS:
        return False
    # libpq 允許用 ?host=／?hostaddr= 覆蓋網址裡的主機，一併檢查
    query = parse_qs(parts.query)
    overrides = query.get('host', []) + query.get('hostaddr', [])
    return all(h in _LOCAL_HOSTS for h in overrides)


def apply():
    os.environ['SKIP_SCHEMA_INIT'] = '1'
    if not os.environ.get('DATABASE_URL', '').strip():
        os.environ['DATABASE_URL'] = LOCAL_TEST_DATABASE_URL
    for name in _GUARDED_URL_VARS:
        url = os.environ.get(name, '').strip()
        if url and not is_local_database_url(url):
            raise RuntimeError(
                f'拒絕在測試中載入 app：{name} 不是本機資料庫（只接受 localhost）。'
                f'請改指本機 dev 庫，例如 {LOCAL_TEST_DATABASE_URL}')


def apply_if_testing():
    if running_under_tests():
        apply()
