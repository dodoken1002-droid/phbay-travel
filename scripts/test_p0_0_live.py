# -*- coding: utf-8 -*-
"""對本機 dev 站台實跑 P0-0 的四條防線。"""
import json
import urllib.error
import urllib.request

B = 'http://127.0.0.1:5001'
KEY = 'devkey-local-only'
fails = []


def call(method, path, body=None):
    sep = '&' if '?' in path else '?'
    url = f'{B}{path}{sep}key={KEY}'
    if body is not None:
        body = dict(body, _key=KEY)
    req = urllib.request.Request(
        url, method=method,
        data=json.dumps(body).encode() if body is not None else None,
        headers={'Content-Type': 'application/json'})
    try:
        r = urllib.request.urlopen(req, timeout=25)
        return r.status, json.load(r)
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.load(e)
        except Exception:
            return e.code, {'raw': e.read()[:300].decode('utf8', 'replace')}


def check(label, cond, detail=''):
    print(('  PASS  ' if cond else '  FAIL  ') + label + (f'  -> {detail}' if detail else ''))
    if not cond:
        fails.append(label)


def pax(n, tag):
    return [{'name': f'{tag}{i}', 'national_id': f'B22345678{i}',
             'birth_date': '1991-02-02', 'phone': '0911111111'} for i in range(n)]


print('=== B. 公開下單：額滿的 9/12 必須擋下（線下已售把位子吃光）===')
s, d = call('POST', '/api/preorder/festival/orders',
            {'departure_date': '2026-09-12', 'departure_time': '',
             'passengers': pax(1, '擋')})
check('9/12 下單被拒', s == 400 and not d.get('ok'), f"{s} {d.get('error','')}")
check('錯誤訊息說剩 0 位', '剩餘 0' in str(d.get('error', '')), d.get('error'))

s, d = call('POST', '/api/preorder/festival/orders',
            {'departure_date': '2026-09-19', 'departure_time': '',
             'passengers': pax(3, '收')})
check('9/19 收滿 3 位可成立', s == 200 and d.get('ok'), f"{s} {d.get('booking_ref','')}")
ref_ok = d.get('booking_ref')

s, d = call('POST', '/api/preorder/festival/orders',
            {'departure_date': '2026-09-19', 'departure_time': '',
             'passengers': pax(1, '超')})
check('9/19 再收 1 位被拒（已滿）', s == 400 and not d.get('ok'), f"{s} {d.get('error','')}")

print('\n=== C. 後台匯入超額：先擋下要確認，確認後才寫入 ===')
imp = {'orders': [{'product': 'festival', 'departure_date': '2026-09-26',
                   'departure_time': '', 'booking_ref': 'IMPOVER1',
                   'contact_name': '匯入客', 'contact_phone': '0922222222',
                   'passengers': pax(5, '匯')},
                  {'product': 'festival', 'departure_date': '2026-09-26',
                   'departure_time': '', 'booking_ref': 'IMPOVER2',
                   'contact_name': '匯入客2', 'contact_phone': '0933333333',
                   'passengers': pax(3, '爆')}]}
s, d = call('POST', '/api/admin/preorder/import', imp)
check('回 409 needs_confirm', s == 409 and d.get('needs_confirm') is True, f'{s}')
check('有列出超額場次', bool(d.get('overbooked')), str(d.get('overbooked')))

s2, d2 = call('GET', '/api/admin/preorder/orders')
wrote = [o for o in (d2.get('orders') or []) if str(o.get('booking_ref', '')).startswith('IMPOVER')]
check('被擋下時整批未寫入（rollback 生效）', len(wrote) == 0, f'找到 {len(wrote)} 筆')

s, d = call('POST', '/api/admin/preorder/import', dict(imp, confirm_overbook=True))
check('帶 confirm_overbook 後寫入成功', s == 200 and d.get('ok'), f'{s} created={d.get("created")}')

s2, d2 = call('GET', '/api/admin/preorder/orders')
wrote = [o for o in (d2.get('orders') or []) if str(o.get('booking_ref', '')).startswith('IMPOVER')]
check('確認後兩筆都進去了', len(wrote) == 2, f'找到 {len(wrote)} 筆')

print('\n=== D. 後台改期超額：先擋下要確認，確認後寫入並留紀錄 ===')
s2, d2 = call('GET', '/api/admin/preorder/orders')
target = next((o for o in (d2.get('orders') or [])
               if o.get('booking_ref') == 'TEST20260919'), None)
if not target:
    check('找得到 9/19 的測試訂單', False, '找不到 TEST20260919')
else:
    oid = target['id']
    s, d = call('PATCH', f'/api/admin/preorder/orders/{oid}',
                {'departure_date': '2026-09-12'})
    check('改到額滿的 9/12 回 409', s == 409 and d.get('needs_confirm') is True,
          f"{s} {d.get('error','')}")

    s3, d3 = call('GET', '/api/admin/preorder/orders')
    still = next((o for o in (d3.get('orders') or []) if o['id'] == oid), None)
    check('被擋下時日期沒被改掉', str(still.get('departure_date', '')).startswith('2026-09-19'),
          str(still.get('departure_date')))

    s, d = call('PATCH', f'/api/admin/preorder/orders/{oid}',
                {'departure_date': '2026-09-12', 'confirm_overbook': True})
    check('帶 confirm_overbook 後改期成功', s == 200 and d.get('ok'), f'{s} {d}')

    s3, d3 = call('GET', '/api/admin/preorder/orders')
    moved = next((o for o in (d3.get('orders') or []) if o['id'] == oid), None)
    check('日期確實改成 9/12', str(moved.get('departure_date', '')).startswith('2026-09-12'),
          str(moved.get('departure_date')))
    logs = json.dumps(moved.get('logs') or [], ensure_ascii=False)
    check('修改紀錄留下「已確認超額改期」', '已確認超額改期' in logs, logs[:160])

print('\n' + ('全部通過' if not fails else f'{len(fails)} 項失敗：{fails}'))
