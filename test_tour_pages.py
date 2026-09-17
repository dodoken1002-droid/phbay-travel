import unittest
from datetime import date
from unittest.mock import patch

import tour_pages
from app import app


def make_tour(**kw):
    tour = {
        "id": 12, "title": "南方四島＋七美深度遊", "description": "東吉嶼登島、西吉藍洞巡航。",
        "tabs": ["south-sea"], "badge_text": "熱銷", "image_url": "", "duration": "1 日遊",
        "suitable_for": "親子 / 深度旅遊", "price_display": "NT$ 1,500 起 / 人",
        "prices": [{"label": "機車", "value": "NT$ 1,500"}], "preorder_slug": None,
        "modal_data": {"highlights": ["東吉嶼登島", "七美登島"], "includes": "船票、保險",
                       "notes": "遇天候不佳保留調整權利。"},
    }
    tour.update(kw)
    return tour


POSTS = [
    {"slug": "dongji-guide", "title": "東吉嶼半日登島指南", "summary": "南方四島", "tags": "澎湖景點,東吉嶼"},
    {"slug": "food", "title": "澎湖海鮮怎麼點", "summary": "海鮮", "tags": "澎湖美食,海鮮"},
]


class TourPageRenderTests(unittest.TestCase):
    def test_database_text_is_escaped(self):
        tour = make_tour(title='<script>alert(1)</script>', description='"><img src=x onerror=1>',
                         image_url='javascript:alert(1)')
        _, _, _, body, head, _ = tour_pages.render_tour_page(tour)
        self.assertNotIn('<script>alert', body)
        self.assertNotIn('<img src=x', body)
        self.assertNotIn('javascript:', body)
        self.assertNotIn('alert(1)</script>', head)  # JSON-LD 裡的 </ 要跳脫，不能提早關閉 script

    def test_sections_follow_available_fields(self):
        _, _, canonical, body, head, _ = tour_pages.render_tour_page(make_tour())
        self.assertEqual(canonical, 'https://www.phbay.info/tours/12')
        for heading in ('費用', '行程內容', '費用包含', '適合誰', '注意事項', '出發前查潮汐'):
            self.assertIn(heading, body)
        self.assertNotIn('每日行程', body)
        self.assertNotIn('行程照片', body)
        self.assertIn('href="/tides"', body)
        self.assertIn('/?tour_id=12#contact', body)
        self.assertIn('"@type": "TouristTrip"', head)
        self.assertIn('"@type": "BreadcrumbList"', head)

    def test_day_by_day_itinerary(self):
        tour = make_tour(modal_data={"days": [{"label": "DAY 1", "title": "抵達澎湖", "items": ["市區觀光"]}]})
        _, _, _, body, head, _ = tour_pages.render_tour_page(tour)
        self.assertIn('每日行程', body)
        self.assertIn('抵達澎湖', body)
        self.assertIn('"itinerary"', head)

    def test_booking_link_only_from_preorder_slug_or_neihai(self):
        self.assertEqual(tour_pages.booking_link(make_tour(preorder_slug='festival')), '/preorder/festival')
        self.assertEqual(tour_pages.booking_link(make_tour(title='小城故事・內海巡禮')), '/neihai-preorder.html')
        # 別家旅行社標題含「追風」「內海巡禮」不能被導到潮旅的預購頁
        self.assertIsNone(tour_pages.booking_link(make_tour(title='澎湖追風派對 風浪板四天三夜')))
        self.assertIsNone(tour_pages.booking_link(make_tour(title='慵藍號遊艇 × 小城故事內海巡禮')))
        self.assertIsNone(tour_pages.booking_link(make_tour(preorder_slug='../admin')))

    def test_past_departure_dates_are_hidden(self):
        today = date(2026, 9, 17)
        dates = ['6/12（五）－ 6/15（一）', '9/17（四）', '10/3（六）', '1/9（六）', '每週六出發']
        self.assertEqual(tour_pages.upcoming_dates(dates, today),
                         ['9/17（四）', '10/3（六）', '1/9（六）', '每週六出發'])
        _, _, _, body, _, _ = tour_pages.render_tour_page(
            make_tour(modal_data={"dates": ['6/12（五）－ 6/15（一）']}), today=today)
        self.assertIn('公告的梯次都已出發', body)
        self.assertNotIn('6/12', body)

    def test_related_posts_prefer_place_names(self):
        self.assertEqual([p['slug'] for p in tour_pages.related_posts(make_tour(), POSTS)], ['dongji-guide'])

    def test_filters(self):
        tours = [make_tour(id=1, tabs=['featured', '3d2n']), make_tour(id=2, tabs=['north-sea']),
                 make_tour(id=3, tabs=['south-sea'])]
        self.assertEqual([t['id'] for t in tour_pages.filter_tours(tours, 'package')], [1])
        self.assertEqual([t['id'] for t in tour_pages.filter_tours(tours, 'single')], [2, 3])
        self.assertEqual([t['id'] for t in tour_pages.filter_tours(tours, 'north-sea')], [2])
        self.assertEqual(tour_pages.normalize_filter('"><script>'), '')
        title, _, canonical, body, _ = tour_pages.render_tours_index(tours, 'south-sea')
        self.assertIn('南海', title)
        self.assertEqual(canonical, 'https://www.phbay.info/tours?type=south-sea')
        self.assertIn('共 1 個行程', body)
        # 沒有行程的分頁不出現篩選鈕
        self.assertNotIn('type=east-sea', body)


class TourRouteTests(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()
        self.tours = [make_tour(id=12), make_tour(id=13, title='七美藍洞巡航')]

    def test_index_and_detail_routes(self):
        with patch('app._active_tours', return_value=self.tours), \
                patch('app._published_posts_brief', return_value=POSTS):
            index = self.client.get('/tours?type=south-sea')
            detail = self.client.get('/tours/12')
            missing = self.client.get('/tours/999')
        self.assertEqual(index.status_code, 200)
        self.assertIn('href="/tours/13"', index.get_data(as_text=True))
        self.assertEqual(detail.status_code, 200)
        html = detail.get_data(as_text=True)
        self.assertIn('<link rel="canonical" href="https://www.phbay.info/tours/12"', html)
        self.assertIn('東吉嶼半日登島指南', html)
        self.assertIn('href="/tours/13"', html)
        self.assertEqual(missing.status_code, 404)
        self.assertIn('noindex', missing.get_data(as_text=True))

    def test_database_failure_is_503(self):
        with patch('app._active_tours', side_effect=RuntimeError('db down')):
            self.assertEqual(self.client.get('/tours').status_code, 503)


if __name__ == '__main__':
    unittest.main()
