"""唯讀盤點行程外語欄位覆蓋率。

有 ``--base-url`` 時讀取公開 ``/api/tours``；未指定時使用既有
``DATABASE_URL`` 連線，並將 PostgreSQL session 明確設為唯讀。
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter


LANGUAGES = ("en", "ja", "ko", "zh-cn")
FIELD_PATHS = (
    ("title",),
    ("badge_text",),
    ("description",),
    ("suitable_for",),
    ("duration",),
    ("price_display",),
    ("prices",),
    ("modal_data", "subtitle"),
    ("modal_data", "highlights"),
    ("modal_data", "dates"),
    ("modal_data", "days"),
    ("modal_data", "includes"),
    ("modal_data", "notice"),
    ("modal_data", "notes"),
)


def _json_object(value):
    if isinstance(value, dict):
        return value
    if isinstance(value, str) and value.strip():
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            return {}
        return parsed if isinstance(parsed, dict) else {}
    return {}


def _meaningful(value):
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, tuple, dict)):
        return bool(value)
    return value is not None


def _get_path(mapping, path):
    value = mapping
    for part in path:
        if not isinstance(value, dict):
            return None
        value = value.get(part)
    return value


def _field_name(path):
    return ".".join(path)


def translation_gaps(tour):
    """回傳每種語言的應翻、已翻與缺漏欄位；不修改輸入資料。"""
    source = dict(tour)
    source["modal_data"] = _json_object(source.get("modal_data"))
    translations = _json_object(source.get("i18n"))
    eligible = [path for path in FIELD_PATHS if _meaningful(_get_path(source, path))]
    result = {}
    for language in LANGUAGES:
        translated = dict(_json_object(translations.get(language)))
        translated["modal_data"] = _json_object(translated.get("modal_data"))
        missing = [
            _field_name(path)
            for path in eligible
            if not _meaningful(_get_path(translated, path))
        ]
        result[language] = {
            "eligible": len(eligible),
            "translated": len(eligible) - len(missing),
            "missing": missing,
        }
    return result


def flatten_api_tours(payload):
    if not isinstance(payload, dict) or payload.get("ok") is not True:
        raise ValueError("公開 API 未回傳 ok=true")
    grouped = payload.get("tours")
    if not isinstance(grouped, dict):
        raise ValueError("公開 API 的 tours 格式不正確")
    unique = {}
    for rows in grouped.values():
        if not isinstance(rows, list):
            continue
        for tour in rows:
            if not isinstance(tour, dict):
                continue
            key = ("id", tour.get("id")) if tour.get("id") is not None else (
                "fallback", tour.get("title"), tour.get("sort_order")
            )
            unique.setdefault(key, tour)
    return list(unique.values())


def load_from_api(base_url, timeout=20):
    parsed = urllib.parse.urlsplit(base_url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("--base-url 必須是 http 或 https 網址")
    url = base_url.rstrip("/")
    if not url.endswith("/api/tours"):
        url += "/api/tours"
    request = urllib.request.Request(
        url, headers={"Accept": "application/json", "User-Agent": "phbay-tour-i18n-coverage/1"}
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        payload = json.loads(response.read().decode("utf-8"))
    return flatten_api_tours(payload)


def load_from_database(database_url=None):
    url = (database_url or os.environ.get("DATABASE_URL", "")).strip()
    if not url:
        raise ValueError("未指定 --base-url，且 DATABASE_URL 未設定")
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)
    import psycopg2
    import psycopg2.extras

    try:
        connection = psycopg2.connect(
            url, cursor_factory=psycopg2.extras.RealDictCursor, connect_timeout=5
        )
    except psycopg2.Error as error:
        raise RuntimeError("資料庫連線失敗（連線資訊不會輸出）") from error
    try:
        connection.set_session(readonly=True, autocommit=True)
        with connection.cursor() as cursor:
            cursor.execute(
                """SELECT id, title, badge_text, description, suitable_for, duration,
                          price_display, prices, modal_data, i18n
                     FROM tours
                    WHERE is_active=TRUE
                    ORDER BY sort_order, id"""
            )
            return [dict(row) for row in cursor.fetchall()]
    except psycopg2.Error as error:
        raise RuntimeError("資料庫唯讀查詢失敗（連線資訊不會輸出）") from error
    finally:
        connection.close()


def analyze_tours(tours):
    rows = []
    language_totals = {
        language: {"eligible": 0, "translated": 0} for language in LANGUAGES
    }
    missing_fields = Counter()
    for tour in tours:
        gaps = translation_gaps(tour)
        rows.append({"id": tour.get("id"), "title": tour.get("title") or "（未命名）", "gaps": gaps})
        for language, stats in gaps.items():
            language_totals[language]["eligible"] += stats["eligible"]
            language_totals[language]["translated"] += stats["translated"]
            missing_fields.update(stats["missing"])
    return {"tours": rows, "languages": language_totals, "missing_fields": missing_fields}


def render_report(analysis, stream=sys.stdout):
    print(f"行程外語覆蓋盤點：{len(analysis['tours'])} 筆行程", file=stream)
    for tour in analysis["tours"]:
        print(f"\n[{tour['id']}] {tour['title']}", file=stream)
        for language in LANGUAGES:
            stats = tour["gaps"][language]
            missing = ", ".join(stats["missing"]) if stats["missing"] else "完整"
            print(
                f"  {language}: {stats['translated']}/{stats['eligible']}；缺少：{missing}",
                file=stream,
            )
    print("\n各語言覆蓋率", file=stream)
    for language in LANGUAGES:
        totals = analysis["languages"][language]
        eligible = totals["eligible"]
        rate = totals["translated"] / eligible * 100 if eligible else 100.0
        print(
            f"  {language}: {totals['translated']}/{eligible} ({rate:.1f}%)",
            file=stream,
        )
    print("\n缺漏最多欄位", file=stream)
    if analysis["missing_fields"]:
        for field, count in analysis["missing_fields"].most_common():
            print(f"  {field}: {count}", file=stream)
    else:
        print("  無", file=stream)


def build_parser():
    parser = argparse.ArgumentParser(description="唯讀盤點行程外語欄位覆蓋率")
    parser.add_argument(
        "--base-url",
        help="公開網站根網址（會讀取 /api/tours）；未指定時使用 DATABASE_URL",
    )
    parser.add_argument("--timeout", type=int, default=20, help="公開 API timeout 秒數")
    return parser


def _configure_utf8_output():
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure:
            reconfigure(encoding="utf-8", errors="backslashreplace")


def main(argv=None):
    _configure_utf8_output()
    args = build_parser().parse_args(argv)
    try:
        tours = (
            load_from_api(args.base_url, args.timeout)
            if args.base_url
            else load_from_database()
        )
        render_report(analyze_tours(tours))
        return 0
    except (ValueError, RuntimeError, json.JSONDecodeError, urllib.error.URLError, OSError) as error:
        print(f"錯誤：{error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
