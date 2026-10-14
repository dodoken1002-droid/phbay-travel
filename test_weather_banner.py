import json
import pathlib
import unittest
from unittest.mock import patch

import app as app_module
from app import app


ROOT = pathlib.Path(__file__).resolve().parent
# 2026-10-14 實際呼叫 F-D0047-045 的回應（6 鄉市、每個元素只留前 6 個時段，不含金鑰）
SAMPLE = json.loads((ROOT / 'test_data' / 'cwa-F-D0047-045-sample.json').read_text(encoding='utf-8'))
PAGES_WITH_BANNER = ('index.html', 'faq.html', 'tides.html', 'preorder.html', 'neihai-preorder.html',
                     'privacy.html', 'terms.html', 'penghu-autumn-winter.html')


class WeatherParsingTests(unittest.TestCase):
    def setUp(self):
        self.towns = app_module._parse_cwa_weather(SAMPLE)

    def test_real_response_has_all_six_towns(self):
        self.assertEqual(list(self.towns), list(app_module.WEATHER_TOWNS))
        self.assertIn('湖西鄉', self.towns)

    def test_picks_the_slot_covering_now_not_the_first_one(self):
        # 第一筆是 18:00；21:30 應取 21:00 的溫度與 21:00–00:00 的天氣／降雨
        now = app_module._weather_now(self.towns['馬公市'], '2026-10-14T21:30:00+08:00')
        temps = self.towns['馬公市']['溫度']
        self.assertEqual(now['forecast_time'], '2026-10-14T21:00:00+08:00')
        self.assertEqual(now['temp_c'], int(next(t for t in temps if t['start'].startswith('2026-10-14T21'))['value']['Temperature']))
        weather_slot = next(s for s in self.towns['馬公市']['天氣現象'] if s['start'].startswith('2026-10-14T21'))
        self.assertEqual(now['weather'], weather_slot['value']['Weather'])

    def test_beaufort_with_operator_is_parsed_and_flags_strong_wind(self):
        self.assertEqual(app_module._parse_beaufort('>= 6'), (6, True))
        self.assertEqual(app_module._parse_beaufort('4'), (4, False))
        self.assertEqual(app_module._parse_beaufort(''), (None, False))
        now = app_module._weather_now(self.towns['馬公市'], '2026-10-14T18:30:00+08:00')
        self.assertEqual((now['beaufort'], now['beaufort_or_more'], now['strong_wind']), (6, True, True))
        self.assertEqual(now['wind_direction'], '東北風')

    def test_missing_values_stay_none_never_invented(self):
        now = app_module._weather_now({}, '2026-10-14T21:30:00+08:00')
        for key in ('weather', 'temp_c', 'pop_percent', 'wind_direction', 'beaufort'):
            self.assertIsNone(now[key], key)
        self.assertFalse(now['strong_wind'])

    def test_bad_or_empty_response_raises_instead_of_returning_empty(self):
        with self.assertRaises(Exception):
            app_module._parse_cwa_weather({'success': 'false'})
        with self.assertRaises(Exception):
            app_module._parse_cwa_weather({'success': 'true', 'records': {'Locations': [{'Location': []}]}})


class WeatherApiTests(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()
        app_module._weather_cache.clear()
        self.towns = app_module._parse_cwa_weather(SAMPLE)

    def tearDown(self):
        app_module._weather_cache.clear()

    def test_returns_magong_by_default(self):
        with patch.object(app_module, 'CWA_API_KEY', 'test'), \
             patch.object(app_module, '_fetch_cwa_weather', return_value=self.towns):
            r = self.client.get('/api/weather')
        d = r.get_json()
        self.assertEqual(r.status_code, 200)
        self.assertTrue(d['ok'])
        self.assertEqual(d['location'], '馬公市')
        self.assertFalse(d['stale'])
        self.assertIn('max-age', r.headers['Cache-Control'])

    def test_rejects_unknown_location_and_missing_key(self):
        with patch.object(app_module, 'CWA_API_KEY', 'test'):
            self.assertEqual(self.client.get('/api/weather?location=臺北市').status_code, 400)
        with patch.object(app_module, 'CWA_API_KEY', ''):
            self.assertEqual(self.client.get('/api/weather').status_code, 503)

    def test_falls_back_to_last_good_data_when_cwa_fails(self):
        app_module._weather_cache['all'] = {'at': 0, 'data': self.towns}
        with patch.object(app_module, 'CWA_API_KEY', 'test'), \
             patch.object(app_module, '_fetch_cwa_weather', side_effect=RuntimeError('down')):
            d = self.client.get('/api/weather?location=湖西鄉').get_json()
        self.assertTrue(d['ok'])
        self.assertTrue(d['stale'])
        self.assertEqual(d['location'], '湖西鄉')

    def test_cwa_failure_without_cache_is_502(self):
        with patch.object(app_module, 'CWA_API_KEY', 'test'), \
             patch.object(app_module, '_fetch_cwa_weather', side_effect=RuntimeError('down')):
            self.assertEqual(self.client.get('/api/weather').status_code, 502)


class WeatherBannerPagesTests(unittest.TestCase):
    def test_every_public_page_loads_the_banner_script(self):
        tag = '<script src="/weather-banner.js?v=20261014a" defer></script>'
        for name in PAGES_WITH_BANNER:
            with self.subTest(page=name):
                self.assertIn(tag, (ROOT / name).read_text(encoding='utf-8'))
        self.assertIn(tag, (ROOT / 'app.py').read_text(encoding='utf-8'))  # 部落格／行程／攻略頁外殼

    def test_privacy_and_terms_now_have_the_info_bar(self):
        for name in ('privacy.html', 'terms.html'):
            self.assertIn('<div class="top-banner">', (ROOT / name).read_text(encoding='utf-8'))

    def test_info_bars_no_longer_promote_the_ended_festival(self):
        old = '2026 澎湖追風音樂燈光節 官方合作旅行社</span>'
        for name in PAGES_WITH_BANNER + ('app.py',):
            with self.subTest(page=name):
                self.assertNotIn(old, (ROOT / name).read_text(encoding='utf-8'))

    def test_banner_links_to_cwa_magong_and_warns_on_strong_wind(self):
        js = (ROOT / 'weather-banner.js').read_text(encoding='utf-8')
        self.assertIn('https://www.cwa.gov.tw/V8/C/W/Town/Town.html?TID=1001601', js)
        self.assertIn('風浪較大，離島船班請先確認', js)
        self.assertNotIn('停航', js)  # 只提醒，不宣稱停航


if __name__ == '__main__':
    unittest.main()
