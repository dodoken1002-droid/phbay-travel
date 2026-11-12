"""GSC「重複網頁」修正：未翻譯文章與外語分類頁的 canonical 要回中文版。"""
import re

import pytest

import app as app_module

SITE = app_module.SITE

TRANSLATED = {
    'id': 1, 'slug': 'translated-post', 'title': '有翻譯的文章', 'summary': '摘要',
    'content': '<p>內文</p>', 'tags': '七美,美食', 'cover_image': None,
    'published_at': '2026-11-01', 'created_at': '2026-11-01', 'view_count': 0,
    'faq': None, 'info_box': None,
    'i18n': {l: {'title': f'T-{l}', 'content': f'<p>{l}</p>'} for l in ('en', 'ja', 'ko', 'zh-cn')},
}
UNTRANSLATED = dict(TRANSLATED, id=2, slug='plain-post', title='沒翻譯的文章', i18n={})


class _Cur:
    def __init__(self, rows):
        self.rows, self._last = rows, []

    def execute(self, sql, params=None):
        if params and 'slug=%s' in sql:
            self._last = [r for r in self.rows if r['slug'] == params[0]]
        else:
            self._last = list(self.rows)

    def fetchone(self):
        return self._last[0] if self._last else None

    def fetchall(self):
        return self._last

    def close(self):
        pass


class _Conn:
    def __init__(self, rows):
        self.rows = rows

    def cursor(self):
        return _Cur(self.rows)

    def commit(self):
        pass

    def rollback(self):
        pass

    def close(self):
        pass


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(app_module, 'get_db', lambda: _Conn([TRANSLATED, UNTRANSLATED]))
    monkeypatch.setattr(app_module, '_countable_pageview', lambda: False, raising=False)
    app_module.app.config['TESTING'] = True
    return app_module.app.test_client()


def _canonical(html):
    return re.search(r'<link rel="canonical" href="([^"]+)"', html).group(1)


def _hreflangs(html):
    return re.findall(r'hreflang="([^"]+)"', html)


def test_untranslated_post_lang_variant_canonical_to_chinese(client):
    html = client.get('/blog/plain-post?lang=en').get_data(as_text=True)
    assert _canonical(html) == f'{SITE}/blog/plain-post'


def test_translated_post_keeps_self_canonical(client):
    html = client.get('/blog/translated-post?lang=ja').get_data(as_text=True)
    assert _canonical(html) == f'{SITE}/blog/translated-post?lang=ja'
    assert 'ja' in _hreflangs(html)


def test_localized_tag_page_canonical_to_chinese_tag(client):
    html = client.get('/blog?tag=七美&lang=en').get_data(as_text=True)
    assert _canonical(html) == f'{SITE}/blog?tag=七美'
    assert set(_hreflangs(html)) == {'zh-Hant', 'x-default'}


def test_chinese_tag_page_self_canonical(client):
    html = client.get('/blog?tag=七美').get_data(as_text=True)
    assert _canonical(html) == f'{SITE}/blog?tag=七美'


def test_localized_blog_index_keeps_self_canonical(client):
    html = client.get('/blog?lang=ja').get_data(as_text=True)
    assert _canonical(html) == f'{SITE}/blog?lang=ja'
    assert 'ja' in _hreflangs(html)


def test_member_page_has_no_contradictory_hreflang():
    with open('member.html', encoding='utf-8') as f:
        html = f.read()
    assert 'penghu-100?lang=' not in html


# ── 本次：不再產生重複的 ?lang= 網址 ──
from test_tour_pages import make_tour  # noqa: E402
import tour_pages  # noqa: E402


def test_localized_index_links_untranslated_post_to_chinese(client):
    html = client.get('/blog?lang=en').get_data(as_text=True)
    assert 'href="/blog/plain-post"' in html
    assert 'href="/blog/plain-post?lang=en"' not in html
    assert 'href="/blog/translated-post?lang=en"' in html


def test_untranslated_tour_canonical_to_chinese_and_nofollow_contact():
    tour = make_tour()
    _, _, canonical, body, _, _ = tour_pages.render_tour_page(tour, lang='en')
    assert canonical == f'{SITE}/tours/{tour["id"]}'
    assert 'rel="nofollow"' in body


def test_translated_tour_keeps_lang_canonical():
    tour = make_tour(i18n={'en': {'title': 'South Penghu Tour', 'description': 'Island hopping.'}})
    _, _, canonical, _, _, _ = tour_pages.render_tour_page(tour, lang='en')
    assert canonical == f'{SITE}/tours/{tour["id"]}?lang=en'
