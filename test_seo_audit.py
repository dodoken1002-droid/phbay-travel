import unittest
from unittest.mock import patch

from scripts.seo_audit import audit_page, run


class SeoAuditTests(unittest.TestCase):
    def test_description_attribute_order_does_not_matter(self):
        html = """
        <html><head><title>Penghu travel guide title</title>
        <meta content="A sufficiently long and useful description for the Penghu travel page and visitors." name="description">
        <link href="https://example.test/page" rel="canonical">
        <script type="application/ld+json">{"@type":"WebPage"}</script>
        </head></html>
        """
        with patch("scripts.seo_audit.fetch", return_value=(200, html)):
            findings = audit_page("https://example.test", "/page")
        self.assertEqual(findings, [])

    def test_invalid_json_ld_is_an_error(self):
        html = """
        <html><head><title>Penghu travel guide title</title>
        <meta name="description" content="A sufficiently long and useful description for the Penghu travel page and visitors.">
        <link rel="canonical" href="https://example.test/page">
        <script type="application/ld+json">{invalid}</script>
        </head></html>
        """
        with patch("scripts.seo_audit.fetch", return_value=(200, html)):
            findings = audit_page("https://example.test", "/page")
        self.assertTrue(any("JSON-LD" in row.message for row in findings))

    @patch("scripts.seo_audit.audit_repository_content", return_value=[])
    @patch("scripts.seo_audit.latest_post_paths", return_value=[])
    @patch("scripts.seo_audit.audit_page", return_value=[])
    @patch("scripts.seo_audit.audit_sitemap")
    def test_reviews_page_is_audited_only_when_it_is_in_sitemap(
        self, audit_sitemap, audit_page_mock, _latest_posts, _repository_content
    ):
        site = "https://example.test"
        audit_sitemap.return_value = ([], set())
        run(site)
        self.assertNotIn(
            "/reviews", [call.args[1] for call in audit_page_mock.call_args_list]
        )

        audit_page_mock.reset_mock()
        audit_sitemap.return_value = ([], {site + "/reviews"})
        run(site)
        self.assertIn(
            "/reviews", [call.args[1] for call in audit_page_mock.call_args_list]
        )


if __name__ == "__main__":
    unittest.main()
