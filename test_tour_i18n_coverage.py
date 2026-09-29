import io
import json
import unittest
from unittest.mock import patch

from scripts import tour_i18n_coverage as coverage


def make_tour(**overrides):
    tour = {
        "id": 7,
        "title": "南海一日遊",
        "badge_text": "公會精選",
        "description": "登島與巡航",
        "suitable_for": "親子",
        "duration": "一日",
        "price_display": "線上詢價",
        "prices": [],
        "modal_data": {"subtitle": "經典航線", "highlights": ["登島"], "notes": "依海況調整"},
        "i18n": {},
    }
    tour.update(overrides)
    return tour


class TourI18nCoverageTests(unittest.TestCase):
    def test_reports_only_missing_fields_that_exist_in_source(self):
        tour = make_tour(i18n={"en": {
            "title": "South Sea Day Tour",
            "description": "Island landing and cruise",
            "modal_data": {"highlights": ["Island landing"]},
        }})
        english = coverage.translation_gaps(tour)["en"]
        self.assertNotIn("prices", english["missing"])
        self.assertIn("badge_text", english["missing"])
        self.assertIn("modal_data.subtitle", english["missing"])
        self.assertNotIn("modal_data.highlights", english["missing"])
        self.assertEqual(tour["i18n"]["en"]["modal_data"], {"highlights": ["Island landing"]})

    def test_blank_or_malformed_translation_is_missing(self):
        gaps = coverage.translation_gaps(make_tour(i18n={"ja": {
            "title": "  ", "modal_data": "not-an-object"
        }}))
        self.assertIn("title", gaps["ja"]["missing"])
        self.assertIn("modal_data.notes", gaps["ja"]["missing"])

    def test_api_groups_are_deduplicated_by_tour_id(self):
        tour = make_tour()
        payload = {"ok": True, "tours": {"featured": [tour], "south-sea": [dict(tour)]}}
        self.assertEqual(coverage.flatten_api_tours(payload), [tour])

    def test_public_api_loader_appends_endpoint(self):
        payload = {"ok": True, "tours": {"featured": [make_tour()]}}

        class Response:
            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

            def read(self):
                return json.dumps(payload).encode("utf-8")

        with patch("urllib.request.urlopen", return_value=Response()) as urlopen:
            tours = coverage.load_from_api("https://example.test/")
        self.assertEqual(len(tours), 1)
        self.assertEqual(urlopen.call_args.args[0].full_url, "https://example.test/api/tours")

    def test_summary_includes_language_rates_and_most_missing_fields(self):
        analysis = coverage.analyze_tours([make_tour(i18n={"en": {"title": "Tour"}})])
        output = io.StringIO()
        coverage.render_report(analysis, output)
        report = output.getvalue()
        self.assertIn("en: 1/9 (11.1%)", report)
        self.assertIn("缺漏最多欄位", report)
        self.assertIn("badge_text: 4", report)

    def test_database_loader_enforces_readonly_session_and_select_only(self):
        class Cursor:
            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

            def execute(self, query):
                self.query = query

            def fetchall(self):
                return [{"id": 7, "title": "Tour"}]

        class Connection:
            def __init__(self):
                self.cursor_instance = Cursor()
                self.closed = False

            def set_session(self, **kwargs):
                self.session = kwargs

            def cursor(self):
                return self.cursor_instance

            def close(self):
                self.closed = True

        connection = Connection()
        with patch("psycopg2.connect", return_value=connection):
            rows = coverage.load_from_database("postgres://example")
        self.assertEqual(rows[0]["id"], 7)
        self.assertEqual(connection.session, {"readonly": True, "autocommit": True})
        self.assertIn("SELECT id", connection.cursor_instance.query)
        self.assertNotIn("UPDATE", connection.cursor_instance.query.upper())
        self.assertTrue(connection.closed)


if __name__ == "__main__":
    unittest.main()
