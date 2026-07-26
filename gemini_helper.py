# -*- coding: utf-8 -*-
"""Gemini API 輔助模組（走 REST + urllib，零新依賴，比照 send_line_notify 模式）。

需要環境變數 GEMINI_API_KEY（Railway 網站服務已設定）。
所有呼叫皆為同步 HTTPS；失敗一律丟 RuntimeError，由呼叫端決定如何降級。
"""

import json
import os
import urllib.request
import urllib.error

GEMINI_MODEL = 'gemini-2.5-flash'
_ENDPOINT = ('https://generativelanguage.googleapis.com/v1beta/models/'
             f'{GEMINI_MODEL}:generateContent')


def gemini_available():
    return bool(os.environ.get('GEMINI_API_KEY'))


def gemini_generate(prompt, json_mode=False, timeout=45, temperature=0.7):
    """呼叫 Gemini 產生文字。json_mode=True 時要求回 JSON 並解析後回傳 dict/list。"""
    key = os.environ.get('GEMINI_API_KEY')
    if not key:
        raise RuntimeError('GEMINI_API_KEY 未設定')

    body = {
        'contents': [{'parts': [{'text': prompt}]}],
        'generationConfig': {'temperature': temperature},
    }
    if json_mode:
        body['generationConfig']['responseMimeType'] = 'application/json'

    req = urllib.request.Request(
        _ENDPOINT,
        data=json.dumps(body).encode('utf-8'),
        headers={'Content-Type': 'application/json', 'x-goog-api-key': key},
        method='POST')
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        detail = ''
        try:
            detail = e.read().decode('utf-8')[:300]
        except Exception:
            pass
        raise RuntimeError(f'Gemini API HTTP {e.code}: {detail}')
    except Exception as e:
        raise RuntimeError(f'Gemini API 連線失敗: {e}')

    try:
        text = data['candidates'][0]['content']['parts'][0]['text']
    except (KeyError, IndexError, TypeError):
        raise RuntimeError(f'Gemini 回應格式異常: {str(data)[:300]}')

    if json_mode:
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            raise RuntimeError(f'Gemini 回傳非合法 JSON: {text[:300]}')
    return text
