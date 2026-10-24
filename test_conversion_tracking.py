import unittest
from pathlib import Path


ROOT = Path(__file__).parent


class ConversionContractTests(unittest.TestCase):
    def test_contact_has_method_and_attribution(self):
        script = (ROOT / 'script.js').read_text(encoding='utf-8')
        self.assertIn("method:        'contact_form'", script)
        self.assertIn('data.utm = getAttribution()', script)

    def test_contact_success_hands_off_to_line(self):
        html = (ROOT / 'index.html').read_text(encoding='utf-8')
        script = (ROOT / 'script.js').read_text(encoding='utf-8')
        i18n = (ROOT / 'i18n.js').read_text(encoding='utf-8')
        self.assertIn('id="form-success-line"', html)
        self.assertIn('https://go.mantago.co/bDsNKJ', html)
        self.assertIn("gtag('event', 'line_handoff_click'", script)
        self.assertEqual(i18n.count("'form.lineCta'"), 4)

    def test_preorders_track_attempt_success_failure(self):
        for filename, method in (('preorder.html', "method:'preorder'"),
                                 ('neihai-preorder.html', "method:'neihai_preorder'")):
            html = (ROOT / filename).read_text(encoding='utf-8')
            self.assertIn('preorder_submit_attempt', html)
            self.assertIn('preorder_submit_failed', html)
            self.assertIn("gtag('event','generate_lead'", html)
            self.assertIn(method, html)
            self.assertIn('utm: attribution', html)

    def test_admin_has_lead_funnel_and_member_management(self):
        html = (ROOT / 'admin.html').read_text(encoding='utf-8')
        self.assertIn('conversion-summary', html)
        self.assertIn('saveLeadStatus', html)
        self.assertIn("switchTab('members'", html)


if __name__ == '__main__':
    unittest.main()
