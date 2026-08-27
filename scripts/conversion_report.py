"""GA4 conversion funnel report with period-over-period and segment breakdowns."""

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def credentials():
    raw = (os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON") or
           os.environ.get("GSC_SERVICE_ACCOUNT_JSON") or "").strip()
    if not raw:
        raise RuntimeError("GOOGLE_SERVICE_ACCOUNT_JSON 未設定")
    from google.oauth2 import service_account
    return service_account.Credentials.from_service_account_info(
        json.loads(raw), scopes=["https://www.googleapis.com/auth/analytics.readonly"])


def run_report(service, prop, start, end, dimension):
    body = {"dateRanges": [{"startDate": start, "endDate": end}],
            "dimensions": [{"name": dimension}], "metrics": [{"name": "eventCount"}],
            "dimensionFilter": {"filter": {"fieldName": "eventName", "inListFilter": {
                "values": ["contact_submit_attempt", "contact_submit_failed", "preorder_submit_attempt",
                           "preorder_submit_failed", "generate_lead", "contact_fallback_click"]}}},
            "orderBys": [{"metric": {"metricName": "eventCount"}, "desc": True}], "limit": 100}
    response = service.properties().runReport(property=f"properties/{prop}", body=body).execute()
    return [{"name": row["dimensionValues"][0].get("value") or "(not set)",
             "events": int(row["metricValues"][0]["value"])} for row in response.get("rows", [])]


def events(service, prop, start, end):
    body = {"dateRanges": [{"startDate": start, "endDate": end}],
            "dimensions": [{"name": "eventName"}], "metrics": [{"name": "eventCount"}], "limit": 100}
    response = service.properties().runReport(property=f"properties/{prop}", body=body).execute()
    return {row["dimensionValues"][0]["value"]: int(row["metricValues"][0]["value"])
            for row in response.get("rows", [])}


def funnel(rows):
    contact_attempts = rows.get("contact_submit_attempt", 0)
    contact_failed = rows.get("contact_submit_failed", 0)
    preorder_attempts = rows.get("preorder_submit_attempt", 0)
    preorder_failed = rows.get("preorder_submit_failed", 0)
    return {"contact_attempts": contact_attempts, "contact_failed": contact_failed,
            "contact_success_rate": ((contact_attempts-contact_failed)/contact_attempts if contact_attempts else None),
            "preorder_attempts": preorder_attempts, "preorder_failed": preorder_failed,
            "preorder_success_rate": ((preorder_attempts-preorder_failed)/preorder_attempts if preorder_attempts else None),
            "generate_lead": rows.get("generate_lead", 0),
            "fallback_clicks": rows.get("contact_fallback_click", 0)}


def run():
    prop = os.environ.get("GA4_PROPERTY_ID", "").strip()
    if not prop:
        raise RuntimeError("GA4_PROPERTY_ID 未設定")
    from googleapiclient.discovery import build
    service = build("analyticsdata", "v1beta", credentials=credentials(), cache_discovery=False)
    current, previous = events(service, prop, "28daysAgo", "yesterday"), events(service, prop, "56daysAgo", "29daysAgo")
    report = {"generated_at": datetime.now(timezone.utc).isoformat(),
              "current_28_days": funnel(current), "previous_28_days": funnel(previous), "segments": {}}
    for dimension in ("sessionSourceMedium", "deviceCategory", "language"):
        report["segments"][dimension] = run_report(service, prop, "28daysAgo", "yesterday", dimension)
    try:
        report["segments"]["method"] = run_report(service, prop, "28daysAgo", "yesterday", "customEvent:method")
    except Exception as exc:
        report["method_dimension_note"] = "請在 GA4 將事件參數 method 註冊為事件範圍自訂維度後啟用分流：" + str(exc)
    return report


def markdown(report):
    c, p = report["current_28_days"], report["previous_28_days"]
    pct = lambda v: "—" if v is None else f"{v:.1%}"
    lines = ["# P1 轉換報告（近 28 天）", "", "| 漏斗 | 本期 | 前期 |", "|---|---:|---:|",
             f"| 諮詢嘗試 | {c['contact_attempts']} | {p['contact_attempts']} |",
             f"| 諮詢成功率 | {pct(c['contact_success_rate'])} | {pct(p['contact_success_rate'])} |",
             f"| 預購嘗試 | {c['preorder_attempts']} | {p['preorder_attempts']} |",
             f"| 預購成功率 | {pct(c['preorder_success_rate'])} | {pct(p['preorder_success_rate'])} |",
             f"| generate_lead | {c['generate_lead']} | {p['generate_lead']} |", ""]
    for dimension, rows in report["segments"].items():
        lines.extend([f"## {dimension}", ""] + [f"- {r['name']}：{r['events']}" for r in rows[:15]] + [""])
    if report.get("method_dimension_note"):
        lines.append(report["method_dimension_note"])
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(); parser.add_argument("--output", default="conversion-report.json"); parser.add_argument("--markdown", default="conversion-report.md"); args = parser.parse_args()
    report = run(); Path(args.output).write_text(json.dumps(report, ensure_ascii=False, indent=2)+"\n", encoding="utf-8"); rendered = markdown(report); Path(args.markdown).write_text(rendered+"\n", encoding="utf-8"); print(rendered)


if __name__ == "__main__": main()
