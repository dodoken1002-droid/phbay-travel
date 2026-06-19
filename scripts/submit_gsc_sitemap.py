"""Submit the production sitemap to Google Search Console."""

from __future__ import annotations

import json
import os
import sys
import urllib.request

from google.oauth2 import service_account
from googleapiclient.discovery import build


REQUIRED_ENV = (
    "GSC_SERVICE_ACCOUNT_JSON",
    "GSC_SITE_URL",
    "GSC_SITEMAP_URL",
)
WEBMASTERS_SCOPE = "https://www.googleapis.com/auth/webmasters"


def required_env(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def verify_public_sitemap(url: str) -> None:
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "phbay-gsc-sitemap-submit/1.0"},
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        body = response.read(4096).decode("utf-8", errors="replace")
        if response.status != 200:
            raise RuntimeError(f"Sitemap returned HTTP {response.status}: {url}")
        if "<urlset" not in body and "<sitemapindex" not in body:
            raise RuntimeError(f"Response is not a sitemap XML document: {url}")


def main() -> int:
    for name in REQUIRED_ENV:
        required_env(name)

    site_url = required_env("GSC_SITE_URL")
    sitemap_url = required_env("GSC_SITEMAP_URL")
    service_account_info = json.loads(required_env("GSC_SERVICE_ACCOUNT_JSON"))

    verify_public_sitemap(sitemap_url)

    credentials = service_account.Credentials.from_service_account_info(
        service_account_info,
        scopes=[WEBMASTERS_SCOPE],
    )
    search_console = build(
        "searchconsole",
        "v1",
        credentials=credentials,
        cache_discovery=False,
    )
    search_console.sitemaps().submit(
        siteUrl=site_url,
        feedpath=sitemap_url,
    ).execute()

    print(f"Submitted {sitemap_url} for {site_url}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"GSC sitemap submission failed: {exc}", file=sys.stderr)
        raise

