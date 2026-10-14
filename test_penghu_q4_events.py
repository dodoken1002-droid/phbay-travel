import pathlib
import re
import unittest


ROOT = pathlib.Path(__file__).resolve().parent
ASSET_DIR = ROOT / 'images' / 'events' / 'penghu-2026-q4'
ASSET_URL = '/images/events/penghu-2026-q4/'

DESKTOP_SLIDES = {
    'carousel-lintou-fishing-net': '2026-10-31',
    'carousel-penghu-cross-sea-marathon': '2026-11-01',
    'carousel-penghu-great-march': '2026-11-07',
    'carousel-like-penghu-slow-travel': '2027-01-31',
}
GALLERY = [
    'penghu-2026-q4-events-overview',
    'penghu-2026-10-calendar',
    'penghu-2026-11-calendar',
    'penghu-2026-12-calendar',
]


def png_size(path):
    data = path.read_bytes()[:24]
    assert data[:8] == b'\x89PNG\r\n\x1a\n', path.name
    return int.from_bytes(data[16:20], 'big'), int.from_bytes(data[20:24], 'big')


class PenghuQ4EventAssetsTests(unittest.TestCase):
    def setUp(self):
        self.index = (ROOT / 'index.html').read_text(encoding='utf-8')

    def test_every_design_ships_as_webp_and_png_at_spec_size(self):
        expected = {
            **{name: (1920, 720) for name in DESKTOP_SLIDES},
            **{name + '-mobile': (1080, 1350) for name in DESKTOP_SLIDES},
            'penghu-2026-q4-events-overview': (1920, 1080),
            'penghu-2026-10-calendar': (1400, 1200),
            'penghu-2026-11-calendar': (1400, 1200),
            'penghu-2026-12-calendar': (1400, 1200),
        }
        shipped = sorted(p.name for p in ASSET_DIR.iterdir())
        self.assertEqual(shipped, sorted(f'{n}.{ext}' for n in expected for ext in ('png', 'webp')))
        for name, size in expected.items():
            with self.subTest(name=name):
                self.assertEqual(png_size(ASSET_DIR / f'{name}.png'), size)
                webp = (ASSET_DIR / f'{name}.webp').read_bytes()[:12]
                self.assertEqual((webp[:4], webp[8:12]), (b'RIFF', b'WEBP'))

    def test_carousel_slides_use_webp_first_mobile_art_and_expire(self):
        for name, end in DESKTOP_SLIDES.items():
            with self.subTest(name=name):
                block = re.search(
                    r'<div class="carousel-slide slide-banner" data-event-end="%s">(.*?)</div>' % end,
                    self.index, re.S)
                self.assertIsNotNone(block, f'{name} 輪播格需帶 data-event-end={end}')
                sources = re.findall(r'<source ([^>]*)>', block.group(1))
                self.assertEqual(len(sources), 3)
                self.assertIn(f'{ASSET_URL}{name}-mobile.webp', sources[0])
                self.assertIn('media="(max-width: 768px)"', sources[0])
                self.assertIn('type="image/webp"', sources[0])
                self.assertIn(f'{ASSET_URL}{name}-mobile.png', sources[1])
                self.assertIn(f'{ASSET_URL}{name}.webp', sources[2])
                self.assertIn(f'src="{ASSET_URL}{name}.png"', block.group(1))
                self.assertIn('width="1920" height="720"', block.group(1))

    def test_banner_slides_never_crop_text(self):
        css = (ROOT / 'style.css').read_text(encoding='utf-8')
        rule = re.search(r'\.slide-banner img \{(.*?)\}', css, re.S).group(1)
        self.assertIn('object-fit: contain', rule)
        self.assertNotIn('cover', rule)

    def test_expired_slides_are_removed_before_carousel_counts_them(self):
        script = (ROOT / 'script.js').read_text(encoding='utf-8')
        body = script[script.index('function initCarousel()'):]
        removal = body.index(".carousel-slide[data-event-end]")
        self.assertLess(removal, body.index('_carouselTotal = track.children.length'))
        self.assertIn("timeZone: 'Asia/Taipei'", body[:removal])

    def test_gallery_lives_in_events_section_with_month_expiry(self):
        section = re.search(r'<section class="quick-answers" id="events-2026">(.*?)</section>',
                            self.index, re.S).group(1)
        for name in GALLERY:
            with self.subTest(name=name):
                self.assertIn(f'srcset="{ASSET_URL}{name}.webp" type="image/webp"', section)
                self.assertIn(f'src="{ASSET_URL}{name}.png"', section)
        for end in ('2026-10-31', '2026-11-30', '2026-12-31'):
            self.assertIn(f'<figure data-event-end="{end}">', section)
        i18n = (ROOT / 'i18n.js').read_text(encoding='utf-8')
        for key in ('events.gallery.title', 'events.gallery.note'):
            self.assertEqual(i18n.count(f"'{key}'"), 4, key)

    def test_great_march_keeps_organizer_time_and_notice(self):
        self.assertIn('2026 澎湖大行軍 11/07 08:30–11:30', self.index)
        self.assertIn('時間依行前通知', self.index)
        self.assertNotIn('08:00–14:00', self.index)


if __name__ == '__main__':
    unittest.main()
