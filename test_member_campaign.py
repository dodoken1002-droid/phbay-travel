import re
import unittest
from pathlib import Path


ROOT = Path(__file__).parent


class MemberCampaignContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html = (ROOT / 'member.html').read_text(encoding='utf-8')

    def test_campaign_has_new_and_returning_member_paths(self):
        self.assertIn('id="passport-launch"', self.html)
        self.assertIn('id="campaign-join"', self.html)
        self.assertIn('id="campaign-claim"', self.html)
        self.assertIn('不預先承諾固定現金折抵', self.html)

    def test_campaign_copy_is_available_in_all_languages(self):
        for lang in ('en', 'ja', 'ko', 'zh-cn'):
            self.assertRegex(self.html, rf"(?:{re.escape(lang)}|I\.{re.escape(lang)})")
        self.assertGreaterEqual(self.html.count('campaignTitle'), 5)
        self.assertGreaterEqual(self.html.count('campaignNote'), 5)

    def test_member_funnel_events_exist(self):
        for event in (
            'member_program_view', 'member_campaign_cta_click', 'member_signup_start',
            'member_register_submitted', 'member_signup_complete', 'member_login_start',
            'member_login_code_requested', 'member_login_complete', 'member_oauth_click',
            'member_order_claim_start', 'member_order_claim_code_requested',
            'member_order_claim_complete', 'member_line_bind_start',
            'member_line_bind_code_created', 'member_dashboard_view',
        ):
            self.assertIn(event, self.html)

    def test_tracking_helper_contains_only_anonymous_dimensions(self):
        match = re.search(r"function memberTrack\(eventName,extra=\{\}\)\{(.+?)\}", self.html)
        self.assertIsNotNone(match)
        helper = match.group(1)
        for forbidden in ('email', 'phone', 'member_no', 'member_name', 'booking_ref', 'code'):
            self.assertNotIn(forbidden, helper.lower())
        self.assertIn('campaign_id', helper)
        self.assertIn('language', helper)
        self.assertIn('auth_state', helper)

    def test_complete_events_follow_successful_api_calls(self):
        self.assertLess(self.html.index("await api('/api/member/login/verify'"),
                        self.html.index("memberTrack('member_login_complete'"))
        self.assertLess(self.html.index("await api('/api/member/orders/claim/verify'"),
                        self.html.index("memberTrack('member_order_claim_complete'"))

    def test_member_language_normalizes_uppercase_values(self):
        self.assertIn("String(value||'').toLowerCase()", self.html)
        self.assertIn("MEMBER_LANGS.includes(normalized)", self.html)

    def test_member_language_rejects_unknown_values_without_persisting_them(self):
        self.assertIn("{lang:'zh-tw',valid:false}", self.html)
        self.assertIn("applyLang(lang,normalizedLang.valid)", self.html)
        self.assertIn("if(persist)try{localStorage.setItem('phbay_lang',l)}", self.html)

    def test_member_language_accepts_supported_values_and_uses_html_codes(self):
        self.assertIn("const MEMBER_LANGS=['zh-tw','en','ja','ko','zh-cn']", self.html)
        self.assertIn("'zh-tw':'zh-TW'", self.html)
        self.assertIn("'zh-cn':'zh-CN'", self.html)
        self.assertIn("document.documentElement.lang=LANG_HTML[l]||'zh-TW'", self.html)


if __name__ == '__main__':
    unittest.main()
