import json
import tempfile
import unittest
from pathlib import Path

from repo_posts import sync_repo_posts


class FakeCursor:
    def __init__(self, existing_slugs=()):
        self.existing_slugs = set(existing_slugs)
        self.rowcount = -1
        self.calls = []

    def execute(self, sql, params):
        self.calls.append((sql, params))
        slug = params[0]
        if slug in self.existing_slugs:
            self.rowcount = 0
        else:
            self.existing_slugs.add(slug)
            self.rowcount = 1


class SyncRepoPostsTests(unittest.TestCase):
    def make_post_dir(self):
        temp = tempfile.TemporaryDirectory()
        post = {
            "slug": "unique-test-post",
            "title": "測試文章",
            "summary": "這是一段符合規則的測試摘要。",
            "content": "<p>測試內容</p>",
            "cover_image": "/images/original.jpg",
            "tags": "測試",
            "author": "潮旅國際旅行社",
            "is_published": True,
        }
        Path(temp.name, "post.json").write_text(
            json.dumps(post, ensure_ascii=False), encoding="utf-8"
        )
        return temp

    def test_new_slug_is_inserted(self):
        with self.make_post_dir() as directory:
            cursor = FakeCursor()
            self.assertEqual(sync_repo_posts(cursor, directory), 1)
            self.assertIn("ON CONFLICT (slug) DO NOTHING", cursor.calls[0][0])

    def test_existing_slug_is_not_overwritten(self):
        with self.make_post_dir() as directory:
            cursor = FakeCursor({"unique-test-post"})
            self.assertEqual(sync_repo_posts(cursor, directory), 0)
            sql = cursor.calls[0][0]
            self.assertNotIn("DO UPDATE", sql)
            self.assertNotIn("cover_image=", sql)


if __name__ == "__main__":
    unittest.main()
