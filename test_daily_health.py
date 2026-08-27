import json
import os
import unittest
from unittest.mock import MagicMock, patch

from app import app
from scripts.daily_health_check import Check, render_markdown, send_line_critical_alert


class DailyHealthTests(unittest.TestCase):
    def setUp(self):
        app.config.update(TESTING=True)
        self.client = app.test_client()

    @patch("app.get_db")
    def test_health_reports_release_and_database(self, get_db):
        cursor = MagicMock()
        cursor.fetchone.return_value = {"t": "contacts"}
        connection = MagicMock()
        connection.cursor.return_value = cursor
        get_db.return_value = connection
        with patch.dict(os.environ, {"DATABASE_URL": "postgresql://example/db",
                                     "RAILWAY_GIT_COMMIT_SHA": "a" * 40}, clear=False):
            response = self.client.get("/api/health")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.get_json()["ok"])
        self.assertEqual(response.get_json()["release_sha"], "a" * 40)
        self.assertNotIn("db_url_prefix", response.get_json())

    def test_browser_404_emits_ga4_event_but_api_404_is_json(self):
        page = self.client.get("/definitely-missing")
        self.assertEqual(page.status_code, 404)
        self.assertIn("page_not_found", page.get_data(as_text=True))
        api = self.client.get("/api/definitely-missing")
        self.assertEqual(api.status_code, 404)
        self.assertEqual(api.get_json()["error"], "not found")

    def test_markdown_shows_p3_gate(self):
        report = {"generated_at": "2026-08-27T00:00:00+00:00", "p3_blocked": True,
                  "checks": [Check("homepage", "首頁", "critical", "HTTP 500", None).__dict__]}
        rendered = render_markdown(report)
        self.assertIn("P3 新功能：**暫停**", rendered)
        self.assertIn("HTTP 500", rendered)

    def test_line_alert_is_safe_without_credentials(self):
        report = {"p3_blocked": True, "checks": [
            Check("homepage", "首頁", "critical", "HTTP 500", None).__dict__
        ]}
        with patch.dict(os.environ, {"LINE_CHANNEL_ACCESS_TOKEN": "",
                                     "LINE_OWNER_USER_ID": ""}, clear=False):
            result = send_line_critical_alert(report)
        self.assertEqual(result["status"], "skipped")


if __name__ == "__main__":
    unittest.main()
