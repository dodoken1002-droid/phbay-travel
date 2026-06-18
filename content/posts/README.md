# Automated blog posts

Each published article is stored as one UTF-8 JSON file named
`YYYY-MM-DD-slug.json`. Railway imports these files into PostgreSQL during
deployment. The article `slug` is the idempotency key, so it must be unique.

Required fields:

- `slug`: lowercase ASCII letters, numbers, and hyphens
- `title`, `summary`, `content`, `tags`, `author`
- `is_published`: must be `true`

Optional fields:

- `cover_image`: use an empty string unless the image is licensed and stable
- `source_urls`: an array of fact-checking sources retained in version history

Run `python validate_repo_posts.py` before committing.

