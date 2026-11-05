import unittest
from unittest.mock import patch

from scripts.daily_health_check import _i18n_check


class DailyHealthI18nTests(unittest.TestCase):
    @patch("scripts.daily_health_check._probe_translated_post")
    @patch("scripts.daily_health_check._translated_posts")
    def test_uses_deployed_baseline_during_deploy_grace(self, translated_posts, probe):
        latest = {"slug": "new-post"}
        deployed = {"slug": "deployed-post"}
        translated_posts.return_value = [latest, deployed]
        probe.side_effect = [
            (["zh-tw", "en", "ja", "ko", "zh-cn"], {"zh-tw": {"http_status": 404}}),
            ([], {"zh-tw": {"http_status": 200, "title_matched": True}}),
        ]

        result = _i18n_check("https://example.com", deployment_pending=True)

        self.assertEqual(result.status, "warning")
        self.assertEqual(result.details["latest_slug"], "new-post")
        self.assertEqual(result.details["slug"], "deployed-post")
        self.assertIn("尚待部署", result.summary)

    @patch("scripts.daily_health_check._probe_translated_post")
    @patch("scripts.daily_health_check._translated_posts")
    def test_does_not_hide_latest_failure_after_deploy(self, translated_posts, probe):
        translated_posts.return_value = [{"slug": "new-post"}, {"slug": "deployed-post"}]
        probe.return_value = (["en"], {"en": {"http_status": 404}})

        result = _i18n_check("https://example.com", deployment_pending=False)

        self.assertEqual(result.status, "critical")
        self.assertEqual(result.details["slug"], "new-post")
        probe.assert_called_once()


if __name__ == "__main__":
    unittest.main()
