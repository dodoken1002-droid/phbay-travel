import json
import unittest
from pathlib import Path

from app import app
from pillar_pages import PILLAR_PAGES


ROOT = Path(__file__).resolve().parent


class MoneyPillarTests(unittest.TestCase):
    def test_money_keyword_baseline_is_fixed_and_unique(self):
        rows = json.loads((ROOT / "content" / "seo-money-keywords.json").read_text(encoding="utf-8"))
        self.assertEqual(len(rows), 20)
        self.assertEqual(len({row["keyword"] for row in rows}), 20)
        allowed = {"/", "/penghu-family-travel", "/penghu-3days-itinerary",
                   "/penghu-itinerary-recommendations"}
        self.assertTrue(all(row["target"] in allowed for row in rows))

    def test_first_phase_pillars_have_required_content_and_schema(self):
        for slug in ("penghu-family-travel", "penghu-3days-itinerary",
                     "penghu-itinerary-recommendations"):
            page = PILLAR_PAGES[slug]
            self.assertIn("<h1>", page["body"])
            self.assertIn("<h2", page["body"])
            self.assertIn("<h3", page["body"])
            self.assertIn("alt=", page["body"])
            self.assertIn('"@type": "Article"', page["head_extra"])
            self.assertIn('"@type": "FAQPage"', page["head_extra"])
            self.assertIn('"@type": "BreadcrumbList"', page["head_extra"])
            self.assertIn('"@type": "TouristTrip"', page["head_extra"])

    def test_recommendations_route_and_sitemap(self):
        client = app.test_client()
        page = client.get("/penghu-itinerary-recommendations")
        self.assertEqual(page.status_code, 200)
        html = page.get_data(as_text=True)
        self.assertIn('<link rel="canonical" href="https://www.phbay.info/penghu-itinerary-recommendations"', html)
        self.assertIn("澎湖行程推薦", html)
        sitemap = client.get("/sitemap.xml").get_data(as_text=True)
        self.assertIn("https://www.phbay.info/penghu-itinerary-recommendations", sitemap)

    def test_weather_entry_links_to_all_first_phase_pillars(self):
        faq = (ROOT / "faq.html").read_text(encoding="utf-8")
        tides = (ROOT / "tides.html").read_text(encoding="utf-8")
        for path in ("/penghu-family-travel", "/penghu-3days-itinerary",
                     "/penghu-itinerary-recommendations"):
            self.assertIn(path, faq)
            self.assertIn(path, tides)


if __name__ == "__main__":
    unittest.main()
