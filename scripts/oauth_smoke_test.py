#!/usr/bin/env python3
"""Read-only smoke test for Penghu 100 LINE / Google OAuth entry points.

The script never submits an authorization code, creates a member, or prints
state/nonce values.  It verifies provider availability, the authorization
redirect contract, PKCE/state/nonce, and the user-cancel callback path.
"""

from __future__ import annotations

import argparse
import http.cookiejar
import json
import sys
import urllib.error
import urllib.parse
import urllib.request


PROVIDERS = {
    "line": ("access.line.me", "/oauth2/v2.1/authorize"),
    "google": ("accounts.google.com", "/o/oauth2/v2/auth"),
}


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def request(opener, url):
    request_obj = urllib.request.Request(
        url, headers={"Accept": "application/json,text/html", "User-Agent": "phbay-oauth-smoke/1"})
    try:
        with opener.open(request_obj, timeout=15) as response:
            return response.status, dict(response.headers), response.read()
    except urllib.error.HTTPError as exc:
        return exc.code, dict(exc.headers), exc.read()


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def validate_authorize_redirect(provider, location, expected_redirect_base):
    parsed = urllib.parse.urlparse(location)
    expected_host, expected_path = PROVIDERS[provider]
    require(parsed.scheme == "https", f"{provider}: authorize URL must use HTTPS")
    require(parsed.hostname == expected_host, f"{provider}: unexpected authorize host")
    require(parsed.path == expected_path, f"{provider}: unexpected authorize path")
    query = urllib.parse.parse_qs(parsed.query)
    for key in ("client_id", "redirect_uri", "scope", "state", "nonce",
                "code_challenge", "code_challenge_method"):
        require(query.get(key, [""])[0], f"{provider}: missing {key}")
    require(query.get("response_type") == ["code"], f"{provider}: response_type must be code")
    require(query.get("code_challenge_method") == ["S256"], f"{provider}: PKCE must use S256")
    scopes = set(query["scope"][0].split())
    require({"openid", "email"}.issubset(scopes), f"{provider}: openid/email scope is required")
    require(len(query["state"][0]) >= 32, f"{provider}: state is too short")
    require(len(query["nonce"][0]) >= 32, f"{provider}: nonce is too short")
    expected_redirect = f"{expected_redirect_base}/api/member/oauth/{provider}/callback"
    require(query["redirect_uri"][0] == expected_redirect,
            f"{provider}: redirect_uri does not match {expected_redirect}")
    return query["state"][0]


def run(base_url, expected_redirect_base, allow_disabled=False):
    base_url = base_url.rstrip("/")
    expected_redirect_base = expected_redirect_base.rstrip("/")
    cookie_jar = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(NoRedirect(), urllib.request.HTTPCookieProcessor(cookie_jar))

    status, _, body = request(opener, f"{base_url}/api/member/oauth/providers")
    require(status == 200, f"providers endpoint returned HTTP {status}")
    payload = json.loads(body.decode("utf-8"))
    require(payload.get("ok") is True, "providers endpoint did not return ok=true")
    availability = payload.get("providers") or {}
    require(availability.get("facebook") is False, "facebook must remain disabled")

    disabled = []
    for provider in PROVIDERS:
        enabled = availability.get(provider) is True
        print(f"{provider}: {'configured' if enabled else 'disabled'}")
        if not enabled:
            disabled.append(provider)
            continue

        status, headers, _ = request(opener, f"{base_url}/api/member/oauth/{provider}/start")
        require(status == 302, f"{provider}: start returned HTTP {status}")
        state = validate_authorize_redirect(provider, headers.get("Location", ""), expected_redirect_base)
        cancel_query = urllib.parse.urlencode({"state": state, "error": "access_denied"})
        status, headers, _ = request(
            opener, f"{base_url}/api/member/oauth/{provider}/callback?{cancel_query}")
        require(status == 302, f"{provider}: cancel callback returned HTTP {status}")
        cancel_location = headers.get("Location", "")
        require(cancel_location.endswith("/member/dashboard?oauth_error=denied"),
                f"{provider}: cancel callback did not fail safely")
        print(f"{provider}: authorize + PKCE/state/nonce + cancel callback OK")

    if disabled and not allow_disabled:
        raise AssertionError("OAuth providers are disabled: " + ", ".join(disabled))
    if disabled:
        print("warning: full provider smoke test is blocked until credentials are configured")


def main():
    parser = argparse.ArgumentParser(description="Read-only LINE / Google OAuth preflight smoke test")
    parser.add_argument("--base-url", default="https://www.phbay.info")
    parser.add_argument("--expected-redirect-base", default=None)
    parser.add_argument("--allow-disabled", action="store_true",
                        help="report disabled providers without failing the command")
    args = parser.parse_args()
    expected = args.expected_redirect_base or args.base_url
    try:
        run(args.base_url, expected, args.allow_disabled)
    except (AssertionError, json.JSONDecodeError, urllib.error.URLError, TimeoutError) as exc:
        print(f"OAuth smoke test failed: {exc}", file=sys.stderr)
        return 1
    print("OAuth smoke test passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
