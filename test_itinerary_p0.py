import os
import unittest
from pathlib import Path

os.environ.setdefault('SKIP_SCHEMA_INIT', '1')

from app import app


ROOT = Path(__file__).parent


def src(name):
    return (ROOT / name).read_text(encoding='utf-8')


class ItineraryP0RouteTests(unittest.TestCase):
    def setUp(self):
        app.config.update(TESTING=True)
        self.client = app.test_client()

    def test_recommendation_page_contains_v1_quiz_without_contact_fields(self):
        response = self.client.get('/penghu-itinerary-recommendations')
        body = response.get_data(as_text=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn('id="itinerary-quiz-v1"', body)
        self.assertIn('/itinerary-quiz.js?v=', body)
        self.assertNotIn('qlead-name', body)
        self.assertNotIn('qlead-phone', body)

    def test_result_page_is_noindex_and_loads_rule_engine(self):
        response = self.client.get('/penghu-itinerary-recommendations/result')
        body = response.get_data(as_text=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn('name="robots" content="noindex,follow"', body)
        self.assertIn('id="itinerary-result-v1"', body)
        self.assertIn('/itinerary-analytics.js?v=', body)

    def test_existing_legal_member_and_order_routes_remain_registered(self):
        rules = {rule.rule for rule in app.url_map.iter_rules()}
        for route in ('/privacy', '/terms', '/member/dashboard',
                      '/neihai-preorder', '/api/neihai/preorders',
                      '/preorder/<slug>', '/api/preorder/<slug>/orders'):
            self.assertIn(route, rules)


class ItineraryP0AnalyticsContractTests(unittest.TestCase):
    def test_required_events_exist(self):
        combined = '\n'.join(src(x) for x in (
            'itinerary-quiz.js', 'preorder.html', 'neihai-preorder.html'))
        for event in ('quiz_start', 'quiz_complete', 'itinerary_view', 'product_view',
                      'checkout_start', 'line_click', 'purchase'):
            self.assertIn("'" + event + "'", combined)

    def test_only_anonymous_quiz_dimensions_are_allowlisted(self):
        text = src('itinerary-analytics.js')
        for key in ('travel_days', 'party_type', 'children_age', 'budget_range',
                    'travel_style', 'avoid_preference', 'arrival_method', 'first_visit'):
            self.assertIn("'" + key + "'", text)
        allowlist = text.split('const ALLOWED = [', 1)[1].split('];', 1)[0]
        for pii in ('name', 'phone', 'email', 'travel_date', 'adults', 'children'):
            self.assertNotIn("'" + pii + "'", allowlist)

    def test_preorders_keep_existing_lead_tracking_and_add_purchase_funnel(self):
        for filename in ('preorder.html', 'neihai-preorder.html'):
            text = src(filename)
            self.assertIn('preorder_submit_attempt', text)
            self.assertIn("gtag('event','generate_lead'", text)
            self.assertIn("track('checkout_start'", text)
            self.assertIn("track('purchase'", text)


if __name__ == '__main__':
    unittest.main()
