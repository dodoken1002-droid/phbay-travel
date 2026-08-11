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

        faq = post.get("faq")
        if faq is not None:
            if (not isinstance(faq, list) or not faq
                    or not all(isinstance(x, dict)
                               and str(x.get("q", "")).strip()
                               and str(x.get("a", "")).strip() for x in faq)):
                raise ValueError(
                    f"Invalid post file {path.name}: faq must be a non-empty list of {{q, a}} objects")
        info_box = post.get("info_box")
        if info_box is not None:
            if (not isinstance(info_box, dict) or not info_box
                    or not all(str(k).strip() and str(v).strip() for k, v in info_box.items())):
                raise ValueError(
                    f"Invalid post file {path.name}: info_box must be a non-empty object of label:value")

        # 多語系翻譯（選填）：{lang:{title?,summary?,content?,faq?,info_box?}}
        i18n = post.get("i18n")
        if i18n is not None:
            if not isinstance(i18n, dict):
                raise ValueError(f"Invalid post file {path.name}: i18n must be an object of lang:fields")
            for lg, tr in i18n.items():
                if lg not in ("en", "ja", "ko", "zh-cn"):
                    raise ValueError(f"Invalid post file {path.name}: unsupported i18n lang {lg!r}")
                if not isinstance(tr, dict):
                    raise ValueError(f"Invalid post file {path.name}: i18n[{lg}] must be an object")
                if "content" in tr and FORBIDDEN_HTML_RE.search(str(tr["content"])):
                    raise ValueError(f"Invalid post file {path.name}: i18n[{lg}] unsafe HTML detected")

        post["slug"] = slug
        seen_slugs.add(slug)
        posts.append(post)

    return posts


def sync_repo_posts(cursor, posts_dir: Path | str = POSTS_DIR) -> int:
    """Insert new repository posts without modifying articles already in PostgreSQL.

    Repository files are publication inputs, not a permanent source of truth. After
    the first insert an editor may correct the article or replace its cover image in
    the admin UI, so later deployments must leave the existing row untouched.
    """
    posts = load_repo_posts(posts_dir)
    inserted = 0
    for post in posts:
        cursor.execute(
            """INSERT INTO posts
               (slug, title, summary, content, cover_image, tags, author,
                is_published, published_at, faq, info_box, i18n)
               VALUES (%s, %s, %s, %s, %s, %s, %s, TRUE,
                       COALESCE(%s::timestamptz, NOW()), %s::jsonb, %s::jsonb, %s::jsonb)
               ON CONFLICT (slug) DO NOTHING""",
            (
                post["slug"],
                post["title"],
                post["summary"],
                post["content"],
                post.get("cover_image", ""),
                post["tags"],
                post["author"],
                (str(post["published_at"]).strip() or None) if post.get("published_at") else None,
                json.dumps(post["faq"], ensure_ascii=False) if post.get("faq") else None,
                json.dumps(post["info_box"], ensure_ascii=False) if post.get("info_box") else None,
                json.dumps(post["i18n"], ensure_ascii=False) if post.get("i18n") else None,
            ),
        )
        inserted += max(cursor.rowcount, 0)
    return inserted
