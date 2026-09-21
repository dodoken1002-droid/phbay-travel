import unittest

from scripts.oauth_smoke_test import header_value


class OAuthSmokeHeaderTests(unittest.TestCase):
    def test_location_header_is_case_insensitive(self):
        self.assertEqual(
            header_value({"location": "https://access.line.me/example"}, "Location"),
            "https://access.line.me/example",
        )


if __name__ == "__main__":
    unittest.main()
