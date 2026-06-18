"""Validate version-controlled posts before committing or deploying."""

from repo_posts import POSTS_DIR, load_repo_posts


if __name__ == "__main__":
    posts = load_repo_posts(POSTS_DIR)
    print(f"Validated {len(posts)} repository post(s).")

