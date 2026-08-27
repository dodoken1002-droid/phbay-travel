import os
import unittest
from unittest.mock import patch

from app import app, _member_code_hash
from member_program import level_for_trips, levels, next_level, normalize_phone


class MemberRulesTests(unittest.TestCase):
    def test_default_levels_and_progress(self):
        with patch.dict(os.environ, {"MEMBER_LEVELS_JSON": ""}, clear=False):
            self.assertEqual(level_for_trips(0), "準會員")
            self.assertEqual(level_for_trips(5), "澎湖知己")
            self.assertEqual(next_level(5)["threshold"], 10)
            self.assertEqual(next_level(100), None)

    def test_levels_are_configurable(self):
        custom = '[{"trips":1,"name":"A"},{"trips":3,"name":"B"}]'
        with patch.dict(os.environ, {"MEMBER_LEVELS_JSON": custom}, clear=False):
            self.assertEqual(levels(), [(1, "A"), (3, "B")])
            self.assertEqual(level_for_trips(3), "B")

    def test_phone_normalization(self):
        self.assertEqual(normalize_phone("+886 912-345-678"), "0912345678")


class MemberRoutesTests(unittest.TestCase):
    def setUp(self):
        app.config.update(TESTING=True)
        self.client = app.test_client()

    def test_member_pages_are_available(self):
        program = self.client.get('/penghu-100')
        dashboard = self.client.get('/member/dashboard')
        self.assertEqual(program.status_code, 200)
        self.assertEqual(dashboard.status_code, 200)
        self.assertEqual(dashboard.headers.get('X-Robots-Tag'), 'noindex, nofollow')
        program.close(); dashboard.close()

    def test_member_me_requires_login_without_database_access(self):
        response = self.client.get('/api/member/me')
        self.assertEqual(response.status_code, 401)

    def test_registration_requires_consent_before_database_access(self):
        response = self.client.post('/api/member/register', json={
            'name': '測試', 'phone': '0912345678', 'email': 'test@example.com'
        })
        self.assertEqual(response.status_code, 400)
        self.assertIn('同意', response.get_json()['error'])

    def test_member_code_hash_is_scoped(self):
        a = _member_code_hash(1, 'login', '123456')
        self.assertEqual(a, _member_code_hash(1, 'login', '123456'))
        self.assertNotEqual(a, _member_code_hash(1, 'line_bind', '123456'))


if __name__ == '__main__':
    unittest.main()
