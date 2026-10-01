import os
import unittest
from unittest.mock import patch

os.environ.setdefault('SKIP_SCHEMA_INIT', '1')

import app as app_module


BASE_STRUCTURE = {
    'version': 1,
    'template_id': 'classic',
    'travel_days': '3d2n',
    'party_type': 'couple',
    'travel_style': ['culture'],
    'avoid_preference': ['rushed'],
    'warning_types': ['overpacked'],
    'days': [{'day_index': 1, 'items': [
        {'item_id': 'magong_old_town_walk', 'category': 'culture', 'slot': 'afternoon'},
    ]}],
}


class FakeCursor:
    def __init__(self, fetchone=None, fetchall=None):
        self.fetchone_values = list(fetchone or [])
        self.fetchall_values = list(fetchall or [])
        self.calls = []

    def execute(self, sql, params=None):
        self.calls.append((sql, params))

    def fetchone(self):
        return self.fetchone_values.pop(0)

    def fetchall(self):
        return self.fetchall_values.pop(0)

    def close(self):
        pass


class FakeConnection:
    def __init__(self, cursor):
        self._cursor = cursor

    def cursor(self):
        return self._cursor

    def commit(self):
        pass

    def rollback(self):
        pass

    def close(self):
        pass


class PlannerStructureTests(unittest.TestCase):
    def test_allowlist_drops_unknown_items_and_free_text(self):
        raw = dict(BASE_STRUCTURE, notes='不可儲存', days=[{'day_index': 1, 'items': [
            {'item_id': 'unknown', 'category': 'culture', 'slot': 'morning'},
            {'item_id': 'magong_old_town_walk', 'category': 'wrong', 'slot': 'afternoon'},
            BASE_STRUCTURE['days'][0]['items'][0],
        ]}])
        clean = app_module.sanitize_planner_structure(raw)
        self.assertNotIn('notes', clean)
        self.assertEqual(clean['days'][0]['items'], [BASE_STRUCTURE['days'][0]['items'][0]])

    def test_limits_are_truncated_and_oversize_is_discarded(self):
        item = BASE_STRUCTURE['days'][0]['items'][0]
        day_limited = app_module.sanitize_planner_structure(
            dict(BASE_STRUCTURE, days=[{'day_index': i + 1, 'items': [item]}
                                       for i in range(9)]))
        item_limited = app_module.sanitize_planner_structure(
            dict(BASE_STRUCTURE, days=[{'day_index': 1, 'items': [item] * 20}]))
        self.assertEqual(len(day_limited['days']), 7)
        self.assertEqual(len(item_limited['days'][0]['items']), 12)
        self.assertIsNone(app_module.sanitize_planner_structure(
            dict(BASE_STRUCTURE, ignored='x' * 9000)))
        self.assertIsNone(app_module.sanitize_planner_structure('{broken json'))

    def test_bad_structure_does_not_fail_contact_submission(self):
        cursor = FakeCursor(fetchone=[{'id': 9, 'created_at': '2026-10-01'}])
        payload = {'name': '測試', 'phone': '0900', 'travel_date': '2026-10-10',
                   'travel_date_end': '2026-10-12', 'people': '2', 'transport': '飛機',
                   'planner_structure': '{broken json'}
        app_module.app.config.update(TESTING=True)
        with patch.object(app_module, 'get_db', return_value=FakeConnection(cursor)), \
             patch.object(app_module, 'send_contact_email'):
            response = app_module.app.test_client().post('/api/contact', json=payload)
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(cursor.calls[-1][1][-1])

    def test_valid_structure_is_stored_as_clean_json(self):
        cursor = FakeCursor(fetchone=[{'id': 10, 'created_at': '2026-10-01'}])
        payload = {'name': '測試', 'phone': '0900', 'travel_date': '2026-10-10',
                   'travel_date_end': '2026-10-12', 'people': '2', 'transport': '飛機',
                   'planner_structure': dict(BASE_STRUCTURE, notes='自由文字不可存')}
        app_module.app.config.update(TESTING=True)
        with patch.object(app_module, 'get_db', return_value=FakeConnection(cursor)), \
             patch.object(app_module, 'send_contact_email'):
            response = app_module.app.test_client().post('/api/contact', json=payload)
        self.assertEqual(response.status_code, 200)
        stored = cursor.calls[-1][1][-1]
        self.assertIsNotNone(stored)
        self.assertEqual(stored.adapted['days'], BASE_STRUCTURE['days'])
        self.assertNotIn('notes', stored.adapted)


class PlannerInsightsTests(unittest.TestCase):
    def setUp(self):
        app_module.app.config.update(TESTING=True)
        self.client = app_module.app.test_client()
        app_module._PLANNER_GA4_CACHE.clear()

    def test_unauthorized_is_401(self):
        with patch.object(app_module, 'has_role', return_value=False):
            self.assertEqual(self.client.get('/api/admin/planner-insights').status_code, 401)

    def test_unconfigured_ga4_is_200(self):
        empty = {'total_inquiries': 0, 'planned_inquiries': 0, 'templates': [], 'items': []}
        with patch.object(app_module, 'has_role', return_value=True), \
             patch.object(app_module, '_planner_database_insights', return_value=empty), \
             patch.dict(os.environ, {'GA4_PROPERTY_ID': '', 'GOOGLE_SERVICE_ACCOUNT_JSON': ''}):
            result = self.client.get('/api/admin/planner-insights?days=7').get_json()
        self.assertTrue(result['ok'])
        self.assertFalse(result['ga4_configured'])

    def test_database_result_is_aggregate_only(self):
        cursor = FakeCursor(
            fetchone=[{'total': 5, 'planned': 1}],
            fetchall=[[{'planner_structure': BASE_STRUCTURE}]])
        with patch.object(app_module, 'get_db', return_value=FakeConnection(cursor)):
            result = app_module._planner_database_insights(30)
        self.assertEqual(result['planned_inquiries'], 1)
        self.assertEqual(result['templates'][0], {'template_id': 'classic', 'count': 1})
        self.assertNotIn('days', result)

    def test_contact_list_does_not_expose_individual_structure(self):
        cursor = FakeCursor(fetchall=[[{
            'id': 1, 'name': '旅客', 'phone': '0900', 'planner_structure': BASE_STRUCTURE,
            'created_at': '2026-10-01', 'conversion_value': None,
        }]])
        with patch.object(app_module, 'has_role', return_value=True), \
             patch.object(app_module, 'get_db', return_value=FakeConnection(cursor)):
            result = self.client.get('/api/contacts').get_json()
        self.assertTrue(result['ok'])
        self.assertNotIn('planner_structure', result['contacts'][0])

    def test_ga4_call_is_mocked_and_cached(self):
        mock_value = {'data_since': '2026-09-30', 'templates': [], 'items': [], 'funnel': {}}
        with patch.object(app_module, '_fetch_planner_ga4', return_value=mock_value) as fetch:
            self.assertEqual(app_module._cached_planner_ga4(30), mock_value)
            self.assertEqual(app_module._cached_planner_ga4(30), mock_value)
        fetch.assert_called_once_with(30)

    def test_ga4_failure_still_returns_database_stats(self):
        stats = {'total_inquiries': 4, 'planned_inquiries': 2,
                 'templates': [{'template_id': 'classic', 'count': 2}], 'items': []}
        env = {'GA4_PROPERTY_ID': '539602253', 'GOOGLE_SERVICE_ACCOUNT_JSON': '{"x":1}'}
        with patch.object(app_module, 'has_role', return_value=True), \
             patch.object(app_module, '_planner_database_insights', return_value=stats), \
             patch.object(app_module, '_fetch_planner_ga4',
                          side_effect=RuntimeError('403 sa@secret.iam.gserviceaccount.com')), \
             patch.dict(os.environ, env):
            response = self.client.get('/api/admin/planner-insights?days=30')
        result = response.get_json()
        self.assertEqual(response.status_code, 200)
        self.assertTrue(result['ok'])
        self.assertTrue(result['ga4_configured'])
        self.assertEqual(result['inquiries'], stats)
        self.assertIn('ga4_error', result)
        self.assertNotIn('gserviceaccount', response.get_data(as_text=True),
                         'GA4 錯誤細節不可回傳到前端')
        self.assertEqual(app_module._PLANNER_GA4_CACHE, {}, '失敗結果不可被快取')

    def test_ga4_query_clamps_start_date_and_uses_registered_dimensions(self):
        bodies = []

        class FakeRequest:
            def __init__(self, body):
                self.body = body

            def execute(self):
                bodies.append(self.body)
                return {'rows': []}

        class FakeProperties:
            def runReport(self, property, body):
                return FakeRequest(body)

        class FakeService:
            def properties(self):
                return FakeProperties()

        from datetime import date as real_date
        with patch.dict(os.environ, {'GA4_PROPERTY_ID': '539602253'}), \
             patch.object(app_module, '_planner_ga4_credentials', return_value=object()), \
             patch('googleapiclient.discovery.build', return_value=FakeService()):
            early = app_module._fetch_planner_ga4(90, today=real_date(2026, 10, 1))
            late = app_module._fetch_planner_ga4(7, today=real_date(2026, 12, 1))
        self.assertEqual(early['data_since'], '2026-09-30', '自訂維度 9/30 才註冊，不可往前查')
        self.assertEqual(late['data_since'], '2026-11-24')
        dims = [[d['name'] for d in body['dimensions']] for body in bodies[:3]]
        self.assertEqual(dims, [['customEvent:template_id'],
                                ['customEvent:item_id', 'customEvent:category', 'customEvent:area'],
                                ['eventName']])
        events = [body['dimensionFilter']['filter']['inListFilter']['values'] for body in bodies[:3]]
        self.assertEqual(events[0], ['planner_template_generated'])
        self.assertEqual(events[1], ['planner_item_add'])
        self.assertIn('planner_quote_submitted', events[2])
        self.assertTrue(all(body['metrics'] == [{'name': 'eventCount'}] for body in bodies))


if __name__ == '__main__':
    unittest.main()
