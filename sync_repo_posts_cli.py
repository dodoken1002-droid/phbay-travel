"""Publish repository-managed posts before the Railway web process starts.

This runs as the first half of the Railway start command
(``python sync_repo_posts_cli.py && gunicorn ...``). It is deliberately
best-effort: publishing a new blog post must never be allowed to block the web
server from booting. A transient database hiccup at startup should leave the
site serving the posts already in PostgreSQL, not take the whole site down. So
``main`` may raise, but the ``__main__`` entry point swallows every failure,
logs it loudly, and exits 0 so gunicorn always starts.
"""

import os
import sys
import traceback

import psycopg2
import psycopg2.extras
from dotenv import load_dotenv

from repo_posts import sync_repo_posts


POSTS_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS posts (
    id           SERIAL PRIMARY KEY,
    slug         VARCHAR(180) UNIQUE NOT NULL,
    title        VARCHAR(200) NOT NULL,
    summary      TEXT,
    content      TEXT,
    cover_image  TEXT,
    tags         VARCHAR(200),
    author       VARCHAR(80) DEFAULT '潮旅國際旅行社',
    is_published BOOLEAN DEFAULT FALSE,
    published_at TIMESTAMP,
    created_at   TIMESTAMP DEFAULT NOW(),
    updated_at   TIMESTAMP DEFAULT NOW()
)
"""


def main() -> None:
    load_dotenv()
    database_url = os.environ.get("DATABASE_URL", "")
    if not database_url:
        raise RuntimeError("DATABASE_URL is not set")
    if database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql://", 1)

    connection = psycopg2.connect(
        database_url,
        cursor_factory=psycopg2.extras.RealDictCursor,
    )
    try:
        cursor = connection.cursor()
        cursor.execute(POSTS_TABLE_SQL)
        count = sync_repo_posts(cursor)
        connection.commit()
        cursor.close()
        print(f"[BLOG] Inserted {count} new repository post(s); existing posts preserved")
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


if __name__ == "__main__":
    try:
        main()
    except Exception:  # noqa: BLE001 - boot must never fail because of the sync step
        print(
            "[BLOG] sync_repo_posts failed; continuing to start the web server. "
            "New repository posts may not appear until the next successful deploy.",
            file=sys.stderr,
        )
        traceback.print_exc()
        # Exit 0 so the Railway start command's `&& gunicorn ...` still runs.
        sys.exit(0)
