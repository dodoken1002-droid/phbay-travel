#!/usr/bin/env bash
# Verify that a blog post's translated i18n content is actually live on production,
# not just returning 200 with the Chinese fallback.
#
# Usage:
#   bash scripts/check_i18n_live.sh <slug> [lang ...]
#
# If no langs are given, checks every language present in content/posts/<slug>.json's
# "i18n" object. Exits 0 if every language returns HTTP 200 and the live page contains
# a snippet of that language's translated title; exits 1 otherwise.

set -euo pipefail

SLUG="${1:?Usage: bash scripts/check_i18n_live.sh <slug> [lang ...]}"
shift || true

JSON_PATH="content/posts/${SLUG}.json"
if [ ! -f "$JSON_PATH" ]; then
  echo "ERROR: $JSON_PATH not found" >&2
  exit 1
fi

if [ "$#" -gt 0 ]; then
  LANGS=("$@")
else
  mapfile -t LANGS < <(PYTHONIOENCODING=utf-8 python3 -c "
import json
with open(r'$JSON_PATH', encoding='utf-8') as f:
    data = json.load(f)
for lang in sorted(data.get('i18n', {}).keys()):
    print(lang)
" | tr -d '\r')
fi

if [ "${#LANGS[@]}" -eq 0 ]; then
  echo "No i18n languages found in $JSON_PATH" >&2
  exit 1
fi

BASE_URL="https://www.phbay.info/blog/${SLUG}"
OVERALL_OK=1

for lang in "${LANGS[@]}"; do
  URL="${BASE_URL}?lang=${lang}"
  CODE=$(curl -s -o /dev/null -w "%{http_code}" "$URL")

  SNIPPET=$(PYTHONIOENCODING=utf-8 python3 -c "
import json
with open(r'$JSON_PATH', encoding='utf-8') as f:
    data = json.load(f)
title = data.get('i18n', {}).get('$lang', {}).get('title', '')
print(title[:10])
" | tr -d '\r')

  if [ -z "$SNIPPET" ]; then
    echo "lang=$lang http=$CODE content_check=SKIPPED(no title in i18n.$lang)"
    [ "$CODE" = "200" ] || OVERALL_OK=0
    continue
  fi

  # Capture the body into a variable before grepping it (rather than piping
  # curl straight into `grep -q`): grep -q exits as soon as it finds a match,
  # which can SIGPIPE a still-writing curl. With `pipefail` active that turns
  # into a false-negative "MISMATCH" even though the content was there.
  BODY=$(curl -s "$URL")
  if printf '%s' "$BODY" | grep -qF "$SNIPPET"; then
    CONTENT_CHECK="OK"
  else
    CONTENT_CHECK="MISMATCH"
    OVERALL_OK=0
  fi

  echo "lang=$lang http=$CODE content_check=$CONTENT_CHECK"
  [ "$CODE" = "200" ] || OVERALL_OK=0
done

if [ "$OVERALL_OK" -eq 1 ]; then
  echo "ALL CHECKS PASSED for $SLUG"
  exit 0
else
  echo "SOME CHECKS FAILED for $SLUG" >&2
  exit 1
fi
