import unittest
from unittest.mock import patch

from scripts.seo_audit import audit_page


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


if __name__ == "__main__":
    unittest.main()
