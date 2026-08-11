# Automated blog posts

Each published article is stored as one UTF-8 JSON file named
`YYYY-MM-DD-slug.json`. Railway imports new files into PostgreSQL during
deployment. The article `slug` is the idempotency key, so it must be unique.

Existing database articles are never overwritten during deployment. After the
first import, edits made in the admin UI—including cover-image corrections—are
preserved. To publish a different article, always create a new unique slug.

Required fields:

- `slug`: lowercase ASCII letters, numbers, and hyphens
- `title`, `summary`, `content`, `tags`, `author`
- `is_published`: must be `true`

Optional fields:

- `cover_image`: use an empty string unless the image is licensed and stable
- `source_urls`: an array of fact-checking sources retained in version history
- `faq`: a non-empty list of `{q, a}` objects (renders as an FAQ block + FAQPage schema)
- `info_box`: a non-empty object of `label: value` (renders as an info table)
- `i18n`: translations, see below

## Multi-language (`i18n`)

Blog articles are served in Traditional Chinese by default and can carry
pre-translated versions. Readers reach a translation at `/blog/<slug>?lang=xx`,
and the site emits `hreflang` alternates automatically.

Supported languages: `en`, `ja`, `ko`, `zh-cn` (Traditional Chinese `zh-tw` is
the default and is never placed inside `i18n`).

Shape — every field inside a language is **optional** and falls back to the
Chinese original field by field:

```json
"i18n": {
  "en": {
    "title": "…", "summary": "…",
    "content": "<p>…</p>",
    "faq": [{ "q": "…", "a": "…" }],
    "info_box": { "Label": "Value" }
  },
  "ja": { "title": "…", "summary": "…", "content": "<p>…</p>" }
}
```

Rules:

- Translate `content` as HTML with the **same tag structure** as the Chinese
  original (`<p> <h2> <h3> <ul><li> <strong> <a>`); keep internal links such as
  `/#contact` unchanged (translate only the link text).
- No `<script>/<iframe>/<form>` or inline event handlers inside translated
  `content` (same safety rule as the Chinese content).
- A language with no entry (or only some fields) simply falls back to Chinese;
  only fully/partly translated languages appear in `hreflang` and are worth
  publishing.
- **Import is insert-only**: adding `i18n` to an already-published slug via git
  will NOT update the live row (deployment does `ON CONFLICT DO NOTHING`).
  New posts can ship translations in the JSON; back-filling an existing post's
  translations must be done with a direct DB update.

Run `python validate_repo_posts.py` before committing.

Use `tool-blog-topic-backlog.md` as the topic backlog for utility-style daily
articles such as transportation, accommodation, best months to visit, rainy-day
plans, quick answers, and FAQ-led guides.
