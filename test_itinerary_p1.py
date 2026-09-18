import unittest
from pathlib import Path


ROOT = Path(__file__).parent


def src(name):
    return (ROOT / name).read_text(encoding='utf-8')


class ItineraryP1ContractTests(unittest.TestCase):
    def test_recommendations_and_price_model_are_centralized(self):
        text = src('itinerary-quiz.js')
        self.assertIn('const RECOMMENDED_PRODUCTS = {', text)
        self.assertIn('const PRICE_MODEL = {', text)
        self.assertIn("confirmed:false", text)
        self.assertIn("fetch('/api/tours'", text)
        self.assertNotIn("price:'NT$", text)

    def test_boat_avoidance_and_active_fallback_are_enforced(self):
        text = src('itinerary-quiz.js')
        for value in ('long_boat', 'seasick', 'water'):
            self.assertIn("'" + value + "'", text)
        self.assertIn('live.is_active!==false', text)
        self.assertIn('!noBoat||!setting.boat', text)
        self.assertIn('land_itinerary_consultation', text)

    def test_adjust_flow_uses_session_storage_without_query_pii_or_submit(self):
        quiz = src('itinerary-quiz.js')
        prefill = src('itinerary-prefill.js')
        self.assertIn('phbay_itinerary_prefill_v1', quiz)
        self.assertIn('sessionStorage.setItem(PREFILL_KEY', quiz)
        self.assertIn('/?tour_id=', quiz)
        self.assertNotIn('?travel_date=', quiz)
        self.assertNotIn('?phone=', quiz)
        self.assertNotIn('.submit(', prefill)
        self.assertNotIn('requestSubmit(', prefill)
        for field in ('travel-date-start', 'travel-date-end', 'people',
                      'transport', 'tour-interest', 'notes'):
            self.assertIn(field, prefill)

    def test_mobile_cta_is_near_hero_and_has_no_duplicate_ids(self):
        js = src('itinerary-quiz.js')
        css = src('itinerary-quiz.css')
        self.assertIn('ir-mobile-actions', js)
        self.assertIn('@media(max-width:760px)', css)
        self.assertIn('.ir-mobile-actions { display:grid;', css)
        self.assertNotIn('id="ir-book"', js)
        self.assertNotIn('id="ir-adjust"', js)

    def test_normal_view_only_shows_selected_budget(self):
        text = src('itinerary-quiz.js')
        self.assertIn("get('price_preview')==='1'", text)
        self.assertIn('你的預算：', text)
        self.assertIn('preview?pricePreviewHtml(estimate)', text)
        self.assertIn('preview?null:track(name,params)', text)

    def test_cache_versions_are_updated_together(self):
        self.assertIn("ASSET_VERSION = '20260917f'", src('app.py'))
        for filename in ('index.html', 'neihai-preorder.html', 'preorder.html'):
            self.assertIn('20260917f', src(filename))


if __name__ == '__main__':
    unittest.main()
