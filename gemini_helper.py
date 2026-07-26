# -*- coding: utf-8 -*-
"""Gemini API 輔助模組（走 REST + urllib，零新依賴，比照 send_line_notify 模式）。

需要環境變數 GEMINI_API_KEY（Railway 網站服務已設定）。
模型自動偵測：向 Google 查詢金鑰可用的模型，依偏好序挑 flash 系列；
也可用環境變數 GEMINI_MODEL 強制指定。
所有呼叫皆為同步 HTTPS；失敗一律丟 RuntimeError，由呼叫端決定如何降級。
"""

import json
import os
import urllib.request
import urllib.error

_BASE = 'https://generativelanguage.googleapis.com/v1beta'

# 偏好序：新版 flash 優先（2026-07 起 gemini-2.5-flash 已不開放新用戶）
_PREFERRED_MODELS = [
    'gemini-3-flash', 'gemini-3.0-flash', 'gemini-flash-latest',
    'gemini-3-flash-preview', 'gemini-2.5-flash',
]

_resolved_model = None  # 快取（每個 worker 解析一次）


def gemini_available():
    return bool(os.environ.get('GEMINI_API_KEY'))


def _http_json(url, key, payload=None, timeout=30):
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode('utf-8') if payload is not None else None,
        headers={'Content-Type': 'application/json', 'x-goog-api-key': key},
        method='POST' if payload is not None else 'GET')
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        detail = ''
        try:
            detail = e.read().decode('utf-8')[:300]
        except Exception:
            pass
        raise RuntimeError(f'Gemini API HTTP {e.code}: {detail}')
    except Exception as e:
        raise RuntimeError(f'Gemini API 連線失敗: {e}')


def list_models(key=None):
    """回傳此金鑰可用、支援 generateContent 的模型名稱清單。"""
    key = key or os.environ.get('GEMINI_API_KEY')
    if not key:
        raise RuntimeError('GEMINI_API_KEY 未設定')
    data = _http_json(f'{_BASE}/models?pageSize=100', key)
    names = []
    for m in data.get('models', []):
        if 'generateContent' in (m.get('supportedGenerationMethods') or []):
            names.append(m.get('name', '').split('/')[-1])
    return names


def resolve_model(force_refresh=False):
    """決定要用的模型：GEMINI_MODEL 環境變數 > 可用清單中的偏好序 > 任一 flash > 第一個。"""
    global _resolved_model
    env_model = os.environ.get('GEMINI_MODEL', '').strip()
    if env_model:
        return env_model
    if _resolved_model and not force_refresh:
        return _resolved_model
    key = os.environ.get('GEMINI_API_KEY')
    if not key:
        raise RuntimeError('GEMINI_API_KEY 未設定')
    names = list_models(key)
    if not names:
        raise RuntimeError('此金鑰查不到任何可用模型')
    chosen = None
    for p in _PREFERRED_MODELS:
        if p in names:
            chosen = p
            break
    if not chosen:
        flashes = [n for n in names if 'flash' in n and 'image' not in n and 'tts' not in n]
        chosen = flashes[0] if flashes else names[0]
    _resolved_model = chosen
    return chosen


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

    model = resolve_model()
    try:
        data = _http_json(f'{_BASE}/models/{model}:generateContent', key, body, timeout)
    except RuntimeError as e:
        # 模型被下架時（404）重新偵測一次再試
        if 'HTTP 404' in str(e):
            model = resolve_model(force_refresh=True)
            data = _http_json(f'{_BASE}/models/{model}:generateContent', key, body, timeout)
        else:
            raise

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
