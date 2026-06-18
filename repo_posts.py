"""Load and publish version-controlled blog posts from content/posts/*.json."""

from __future__ import annotations

import json
import re
from pathlib import Path


POSTS_DIR = Path(__file__).resolve().parent / "content" / "posts"
SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
FORBIDDEN_HTML_RE = re.compile(
    r"<(?:script|iframe|object|embed|form)\b|\son[a-z]+\s*=|javascript\s*:",
    re.IGNORECASE,
)
REQUIRED_FIELDS = ("slug", "title", "summary", "content", "tags", "author")


def load_repo_posts(posts_dir: Path | str = POSTS_DIR) -> list[dict]:
    """Read and validate repository-managed posts in deterministic order."""
    directory = Path(posts_dir)
    if not directory.exists():
        return []

    posts: list[dict] = []
    seen_slugs: set[str] = set()
    for path in sorted(directory.glob("*.json")):
        try:
            post = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise ValueError(f"Invalid post file {path.name}: {exc}") from exc

        if not isinstance(post, dict):
            raise ValueError(f"Invalid post file {path.name}: root must be an object")

        missing = [field for field in REQUIRED_FIELDS if not str(post.get(field, "")).strip()]
        if missing:
            raise ValueError(f"Invalid post file {path.name}: missing {', '.join(missing)}")

        slug = str(post["slug"]).strip()
        if not SLUG_RE.fullmatch(slug):
            raise ValueError(f"Invalid post file {path.name}: invalid slug {slug!r}")
        if slug in seen_slugs:
            raise ValueError(f"Duplicate repository post slug: {slug}")
        if len(str(post["title"])) > 200:
            raise ValueError(f"Invalid post file {path.name}: title exceeds 200 characters")
        if len(str(post["tags"])) > 200:
            raise ValueError(f"Invalid post file {path.name}: tags exceed 200 characters")
        if len(str(post["author"])) > 80:
            raise ValueError(f"Invalid post file {path.name}: author exceeds 80 characters")
        if FORBIDDEN_HTML_RE.search(str(post["content"])):
            raise ValueError(f"Invalid post file {path.name}: unsafe HTML detected")
        if post.get("is_published") is not True:
            raise ValueError(f"Invalid post file {path.name}: is_published must be true")

        post["slug"] = slug
        seen_slugs.add(slug)
        posts.append(post)

    return posts


def sync_repo_posts(cursor, posts_dir: Path | str = POSTS_DIR) -> int:
    """Upsert repository posts into PostgreSQL and return the synced count."""
    posts = load_repo_posts(posts_dir)
    for post in posts:
        cursor.execute(
            """INSERT INTO posts
               (slug, title, summary, content, cover_image, tags, author,
                is_published, published_at)
               VALUES (%s, %s, %s, %s, %s, %s, %s, TRUE, NOW())
               ON CONFLICT (slug) DO UPDATE SET
                   title=EXCLUDED.title,
                   summary=EXCLUDED.summary,
                   content=EXCLUDED.content,
                   cover_image=EXCLUDED.cover_image,
                   tags=EXCLUDED.tags,
                   author=EXCLUDED.author,
                   is_published=TRUE,
                   published_at=COALESCE(posts.published_at, NOW()),
                   updated_at=NOW()""",
            (
                post["slug"],
                post["title"],
                post["summary"],
                post["content"],
                post.get("cover_image", ""),
                post["tags"],
                post["author"],
            ),
        )
    return len(posts)

