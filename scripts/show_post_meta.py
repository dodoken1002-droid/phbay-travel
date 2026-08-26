"""Print metadata for one content/posts/*.json file, for quick daily checks.

Usage:
    python scripts/show_post_meta.py                # today's post
    python scripts/show_post_meta.py today           # same as above
    python scripts/show_post_meta.py 2026-08-26      # post dated 2026-08-26
    python scripts/show_post_meta.py 2026-08-26-penghu-longmen-military-tunnel-walk-guide

Kept as a fixed, no-wildcard-needed command so it can be allowlisted verbatim
(`Bash(python scripts/show_post_meta.py)` / `... today`) without opening up
arbitrary `python -c "..."` execution.
"""

from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from repo_posts import POSTS_DIR  # noqa: E402

I18N_LANGS = ("en", "ja", "ko", "zh-cn")


def resolve_path(arg: str | None) -> Path | None:
    if arg is None or arg == "today":
        arg = date.today().isoformat()

    direct = POSTS_DIR / (arg if arg.endswith(".json") else f"{arg}.json")
    if direct.is_file():
        return direct

    if len(arg) == 10 and arg[4] == "-" and arg[7] == "-":
        matches = sorted(POSTS_DIR.glob(f"{arg}-*.json"))
        if matches:
            return matches[0]

    return None


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")

    arg = sys.argv[1] if len(sys.argv) > 1 else None
    path = resolve_path(arg)
    if path is None:
        print(f"No post file found for '{arg or 'today'}' in {POSTS_DIR}", file=sys.stderr)
        sys.exit(1)

    post = json.loads(path.read_text(encoding="utf-8"))
    i18n = post.get("i18n") if isinstance(post.get("i18n"), dict) else {}
    langs = [lang for lang in I18N_LANGS if lang in i18n]

    print("file:", path.name)
    print("slug:", post.get("slug"))
    print("title:", post.get("title"))
    print("is_published:", post.get("is_published"))
    print("i18n_langs:", ", ".join(langs) if langs else "(none)")


if __name__ == "__main__":
    main()
