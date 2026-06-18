"""Publish repository-managed posts before the Railway web process starts."""

import os

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
        print(f"[BLOG] Synced {count} repository post(s)")
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


if __name__ == "__main__":
    main()
