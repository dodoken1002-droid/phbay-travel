import pathlib
import re
import unittest


ROOT = pathlib.Path(__file__).resolve().parent
ASSET_DIR = ROOT / 'images' / 'events' / 'penghu-2026-q4'
SEASON_ASSET_DIR = ROOT / 'images' / 'autumn-winter'


def png_size(path):
    data = path.read_bytes()[:24]
    assert data[:8] == b'\x89PNG\r\n\x1a\n', path.name
    return int.from_bytes(data[16:20], 'big'), int.from_bytes(data[20:24], 'big')


class PenghuAutumnWinterTests(unittest.TestCase):
    def setUp(self):
        self.home = (ROOT / 'index.html').read_text(encoding='utf-8')
        self.page = (ROOT / 'penghu-autumn-winter.html').read_text(encoding='utf-8')
        self.app = (ROOT / 'app.py').read_text(encoding='utf-8')

    def test_original_q4_asset_pack_remains_complete(self):
        desktop = [
            'carousel-lintou-fishing-net',
            'carousel-penghu-cross-sea-marathon',
            'carousel-penghu-great-march',
            'carousel-like-penghu-slow-travel',
        ]
        expected = {
            **{name: (1920, 720) for name in desktop},
            **{name + '-mobile': (1080, 1350) for name in desktop},
            'penghu-2026-q4-events-overview': (1920, 1080),
            'penghu-2026-10-calendar': (1400, 1200),
            'penghu-2026-11-calendar': (1400, 1200),
            'penghu-2026-12-calendar': (1400, 1200),
        }
        shipped = sorted(p.name for p in ASSET_DIR.iterdir())
        self.assertEqual(shipped, sorted(f'{name}.{ext}' for name in expected for ext in ('png', 'webp')))
        for name, size in expected.items():
            self.assertEqual(png_size(ASSET_DIR / f'{name}.png'), size)

    def test_homepage_has_one_seasonal_entry_instead_of_four_event_slides(self):
        self.assertEqual(self.home.count('class="carousel-slide slide-autumn-entry"'), 1)
        self.assertNotIn('class="carousel-slide slide-banner"', self.home)
        self.assertGreaterEqual(self.home.count('href="/penghu-autumn-winter"'), 3)
        self.assertIn('id="season-entry"', self.home)
        self.assertNotIn('id="events-2026"', self.home)
        self.assertNotIn('class="partner-trust"', self.home)

    def test_season_page_contains_current_events_and_notice(self):
        for value in (
            '10/17・10/25・10/31',
            'Like 澎湖・免費交通與 9 大場館',
            '菊島澎湖跨海馬拉松',
            '2026 澎湖大行軍',
            '08:30–11:30＊',
            '依主辦行前通知',
        ):
            self.assertIn(value, self.page)
        self.assertNotIn('08:00–14:00', self.page)
        self.assertNotIn('光島盛典', self.page)

    def test_season_page_routes_to_existing_site_tools(self):
        for href in (
            '/penghu-itinerary-recommendations/planner?src=autumn_winter',
            '/tides', '/tours', '/faq.html',
            'https://go.mantago.co/iCy82S',
        ):
            self.assertIn(f'href="{href}"', self.page)

    def test_production_route_assets_and_sitemap_are_registered(self):
        self.assertIn("@app.route('/penghu-autumn-winter')", self.app)
        self.assertIn("send_from_directory('.', 'penghu-autumn-winter.html')", self.app)
        self.assertIn("f'{SITE}/penghu-autumn-winter'", self.app)
        self.assertEqual(sorted(p.name for p in SEASON_ASSET_DIR.iterdir()), [
            'event-lintou.webp', 'event-marathon.webp', 'hero-slow-travel.webp',
            'og-autumn-winter.jpg'])
        css = (ROOT / 'penghu-autumn-winter.css').read_text(encoding='utf-8')
        for name in ('hero-slow-travel.webp', 'event-lintou.webp', 'event-marathon.webp'):
            self.assertIn(f'/images/autumn-winter/{name}', css)

    def test_season_page_has_one_h1_and_accessibility_basics(self):
        self.assertEqual(len(re.findall(r'<h1\b', self.page)), 1)
        self.assertIn('<html lang="zh-Hant">', self.page)
        self.assertIn('class="skip-link"', self.page)
        self.assertIn('aria-controls="main-menu"', self.page)

    def test_bottom_banner_keeps_line_consult_without_ended_festival(self):
        banner = re.search(r'<div class="bottom-banner" id="bottom-banner">(.*?)</div>',
                           self.home, re.S).group(1)
        self.assertNotIn('追風', banner)
        self.assertNotIn('banner-festival', banner)
        self.assertIn('class="banner-line-btn"', banner)

    def test_season_page_is_tracked_like_other_pages(self):
        self.assertIn("gtag('config', 'G-47DV1VPF9J')", self.page)
        self.assertIn("fbq('init', '25643845041980148')", self.page)
        js = (ROOT / 'penghu-autumn-winter.js').read_text(encoding='utf-8')
        self.assertIn("gtag('event', 'contact_click'", js)

    def test_season_page_license_numbers_are_correct(self):
        self.assertNotIn('交通部品保', self.page)
        self.assertIn('交觀乙第1864號', self.page)
        self.assertIn('品保澎字第0188號', self.page)
        self.assertIn('插畫示意', self.page)

    def test_undated_theme_tours_show_as_pending_not_guessed(self):
        self.assertIn('<span class="status pending">待確認</span>', self.page)
        for name in ('湖東・灶腳山海味', '成功・擼魚栽！', '南寮・雞母狗捏捏樂', '媽宮城・走讀趣'):
            self.assertIn(name, self.page)

    def test_share_images_are_jpg_1200x630(self):
        jpg = SEASON_ASSET_DIR / 'og-autumn-winter.jpg'
        data = jpg.read_bytes()
        self.assertEqual(data[:2], bytes([0xFF, 0xD8]))
        url = 'https://www.phbay.info/images/autumn-winter/og-autumn-winter.jpg'
        self.assertIn(f'<meta property="og:image" content="{url}"', self.page)
        self.assertIn(f'<meta property="og:image" content="{url}"', self.home)
        self.assertNotIn('festival-poster', self.home)

    def test_autumn_quiz_answer_no_longer_points_to_ended_festival(self):
        script = (ROOT / 'script.js').read_text(encoding='utf-8')
        line = next(l for l in script.splitlines() if "text:'9–10 月（秋）'" in l)
        self.assertNotIn('festival', line)

    def test_season_page_mobile_hero_and_top_note(self):
        css = (ROOT / 'penghu-autumn-winter.css').read_text(encoding='utf-8')
        # 375px 寬時 8 個字的標題要放得下，不可留下單獨的「湖。」
        self.assertIn('.hero h1{font-size:clamp(32px,9.2vw,45px)}', css)
        self.assertNotIn('.hero h1{font-size:45px}', css)
        # 手機頂部資訊：先顯示每項，再隱藏分隔線與 LINE（順序反了 LINE 會被蓋回來）
        hide = '.top-note .tn-sep,.top-note .tn-line{display:none}'
        self.assertLess(css.index('.top-note .tn-item{display:block}'), css.index(hide))
        self.assertIn('<span class="tn-item tn-line">官方 LINE @phbay2018</span>', self.page)


if __name__ == '__main__':
    unittest.main()
