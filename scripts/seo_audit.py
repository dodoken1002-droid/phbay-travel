"""SEO/GEO/AEO repeatable audit for repository content and production pages."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parents[1]
SITE = "https://www.phbay.info"
CORE_PATHS = ["/", "/blog", "/faq.html", "/penghu-3days-itinerary",
              "/penghu-family-travel", "/penghu-itinerary-recommendations", "/penghu-food-guide",
              "/penghu-2026-festival-guide", "/reviews", "/penghu-100"]


@dataclass
class Finding:
    severity: str
    target: str
    message: str


def fetch(url, timeout=20):
    req = urllib.request.Request(url, headers={"User-Agent": "phbay-seo-audit/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            return response.status, response.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode("utf-8", "replace")


def latest_post_paths(limit=5):
    paths = []
    for path in sorted((ROOT / "content" / "posts").glob("*.json"), reverse=True):
        try:
            post = json.loads(path.read_text(encoding="utf-8"))
            if post.get("is_published") and post.get("slug"):
                paths.append(f"/blog/{post['slug']}")
        except Exception:
            pass
        if len(paths) >= limit:
            break
    return paths


def audit_page(site, path):
    findings = []
    code, html = fetch(site + path)
    if code != 200:
        return [Finding("error", path, f"HTTP {code}")]
    checks = [
        (r'<title>[^<]{8,}</title>', "缺少有效 title"),
        (r'<link[^>]+rel=["\']canonical["\']', "缺少 canonical"),
        (r'application/ld\+json', "缺少 JSON-LD"),
    ]
    for pattern, message in checks:
        if not re.search(pattern, html, re.I):
            findings.append(Finding("error", path, message))
    description = ""
    for tag in re.findall(r'<meta\b[^>]*>', html, re.I):
        if re.search(r'\bname\s*=\s*["\']description["\']', tag, re.I):
            match = re.search(r'\bcontent\s*=\s*["\']([^"\']*)', tag, re.I)
            if match:
                description = match.group(1).strip()
                break
    if len(description) < 40:
        findings.append(Finding("error", path, "缺少或過短的 meta description"))
    if re.search(r'<meta[^>]+name=["\']robots["\'][^>]+noindex', html, re.I):
        findings.append(Finding("error", path, "公開重點頁含 noindex"))
    for raw in re.findall(r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>', html, re.I | re.S):
        try:
            json.loads(raw)
        except Exception as exc:
            findings.append(Finding("error", path, f"JSON-LD 無法解析：{exc}"))
    if path.startswith("/blog/"):
        for lang in ("zh-TW", "en", "ja", "ko", "zh-CN", "x-default"):
            if f'hreflang="{lang}"' not in html and f"hreflang='{lang}'" not in html:
                findings.append(Finding("warning", path, f"未輸出 hreflang {lang}"))
    return findings


def audit_sitemap(site):
    findings = []
    code, xml = fetch(site + "/sitemap.xml")
    if code != 200:
        return [Finding("error", "/sitemap.xml", f"HTTP {code}")], set()
    try:
        root = ET.fromstring(xml)
        urls = {row.text.rstrip("/") or site for row in root.findall(".//{*}loc") if row.text}
    except Exception as exc:
        return [Finding("error", "/sitemap.xml", f"XML 無法解析：{exc}")], set()
    for path in CORE_PATHS:
        expected = site + path
        normalized = expected.rstrip("/") or site
        if normalized not in urls:
            findings.append(Finding("error", "/sitemap.xml", f"缺少 {path}"))
    return findings, urls


def audit_repository_content():
    findings = []
    required_langs = {"en", "ja", "ko", "zh-cn"}
    for path in sorted((ROOT / "content" / "posts").glob("*.json")):
        try:
            post = json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:
            findings.append(Finding("error", str(path.relative_to(ROOT)), f"JSON 錯誤：{exc}"))
            continue
        if not post.get("is_published"):
            continue
        target = str(path.relative_to(ROOT)).replace("\\", "/")
        summary = re.sub(r'<[^>]+>', '', post.get("summary") or "").strip()
        content = post.get("content") or ""
        if len(summary) < 40:
            findings.append(Finding("warning", target, "summary 少於 40 字，不利 AEO 摘要"))
        if not post.get("faq"):
            findings.append(Finding("warning", target, "缺少 FAQ"))
        if not post.get("info_box"):
            findings.append(Finding("warning", target, "缺少 info_box"))
        missing_langs = sorted(required_langs - set((post.get("i18n") or {}).keys()))
        if missing_langs:
            findings.append(Finding("warning", target, "缺少翻譯：" + ", ".join(missing_langs)))
        if not re.search(r'href=["\']/penghu-(?:3days|family|itinerary|food|2026)', content):
            findings.append(Finding("warning", target, "缺少 pillar page 內鏈"))
        if len(re.findall(r'href=["\']/blog/', content)) < 2:
            findings.append(Finding("warning", target, "相關文章內鏈少於 2 個"))
        if not re.search(r'href=["\'](?:/#contact|https://line\.me)', content):
            findings.append(Finding("warning", target, "缺少諮詢或 LINE CTA"))
    for filename in ("llms.txt", "llms-full.txt"):
        text = (ROOT / filename).read_text(encoding="utf-8")
        for path in ("/penghu-3days-itinerary", "/penghu-family-travel",
                     "/penghu-itinerary-recommendations", "/penghu-food-guide", "/penghu-100"):
            if path not in text:
                findings.append(Finding("warning", filename, f"未列出 {path}"))
    return findings


def run(site):
    findings, sitemap_urls = audit_sitemap(site)
    for path in CORE_PATHS + latest_post_paths():
        findings.extend(audit_page(site, path))
    findings.extend(audit_repository_content())
    errors = sum(row.severity == "error" for row in findings)
    warnings = sum(row.severity == "warning" for row in findings)
    return {"generated_at": datetime.now(timezone.utc).isoformat(), "site": site,
            "ok": errors == 0, "errors": errors, "warnings": warnings,
            "sitemap_url_count": len(sitemap_urls), "findings": [asdict(row) for row in findings]}


def markdown(report):
    lines = [f"# SEO／GEO／AEO 稽核 — {report['generated_at'][:10]}", "",
             f"結果：**{'通過' if report['ok'] else '失敗'}**；{report['errors']} errors；{report['warnings']} warnings；sitemap {report['sitemap_url_count']} URLs。", ""]
    for severity in ("error", "warning"):
        rows = [row for row in report["findings"] if row["severity"] == severity]
        if rows:
            lines.extend([f"## {severity.upper()}", ""])
            lines.extend(f"- `{row['target']}`：{row['message']}" for row in rows)
            lines.append("")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--site", default=os.environ.get("HEALTH_SITE_URL", SITE).rstrip("/"))
    parser.add_argument("--output", default="seo-audit.json")
    parser.add_argument("--markdown", default="seo-audit.md")
    args = parser.parse_args()
    report = run(args.site)
    Path(args.output).write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    rendered = markdown(report)
    Path(args.markdown).write_text(rendered + "\n", encoding="utf-8")
    print(rendered)
    return 1 if not report["ok"] else 0


if __name__ == "__main__":
    sys.exit(main())
