"""上線後第一批安全與監控修正的回歸測試。"""
import io
import re
import unittest
from pathlib import Path

try:
    import yaml
except ImportError:  # pyyaml 僅供本機驗證 workflow YAML，缺少時跳過該組測試
    yaml = None

from app import app


ROOT = Path(__file__).parent


def src(name):
    return io.open(ROOT / name, encoding='utf-8').read()


class RegistrationEnumerationTests(unittest.TestCase):
    """註冊端點不得洩漏某組手機／Email 是不是會員。"""

    def setUp(self):
        app.config.update(TESTING=True)
        self.client = app.test_client()
        self.app_src = src('app.py')

    def test_no_conflict_status_is_returned(self):
        self.assertNotIn('此手機或 Email 已加入，請使用驗證碼登入', self.app_src)
        body = self.app_src.split('def member_register')[1].split('@app.route')[0]
        self.assertNotIn('409', body, '註冊不得用 409 透露帳號已存在')

    def test_registration_never_grants_a_session_directly(self):
        """未驗證 Email 就發登入態，等於任何人都能拿別人信箱開帳號並登入。"""
        body = self.app_src.split('def member_register')[1].split('@app.route')[0]
        self.assertNotIn("session['member_id']", body)

    def test_consent_is_still_required(self):
        r = self.client.post('/api/member/register',
                             json={'name': 'A', 'phone': '0912345678', 'email': 'a@b.co'})
        self.assertEqual(r.status_code, 400)
        r.close()

    def test_login_code_goes_to_the_stored_email(self):
        """驗證碼必須寄到會員檔案上的信箱，不能寄到請求輸入的信箱。"""
        helper = self.app_src.split('def _issue_member_login_code')[1].split('@app.route')[0]
        self.assertIn('_send_member_code_email(member, code)', helper)
        self.assertIn("INTERVAL '1 hour'", helper)


class AdminHardeningTests(unittest.TestCase):
    def setUp(self):
        self.app_src = src('app.py')

    def test_member_admin_endpoints_do_not_leak_exceptions(self):
        for fn in ('admin_members', 'admin_member_detail', 'admin_member_add_trip',
                   'admin_member_update_trip', 'admin_member_adjust_points',
                   'admin_member_merge', 'admin_members_export', 'conversion_summary'):
            body = self.app_src.split('def ' + fn + '(')[1].split('@app.route')[0]
            self.assertNotIn('error=str(exc)', body, fn + ' 仍回傳原始例外')

    def test_member_export_is_owner_only(self):
        body = self.app_src.split('def admin_members_export')[1].split('@app.route')[0]
        self.assertIn('if not is_admin():', body)
        self.assertNotIn("has_role('orders')", body)

    def test_merge_locks_rows_in_a_fixed_order(self):
        body = self.app_src.split('def admin_member_merge')[1].split('@app.route')[0]
        self.assertIn('sorted((source_id, target_id))', body)
        self.assertNotIn('WHERE id IN (%s,%s) FOR UPDATE', body)

    def test_health_endpoint_hides_database_error_text(self):
        body = self.app_src.split('def health()')[1].split('@app.route')[0]
        self.assertNotIn('db_error = str(e)', body)
        self.assertIn("db_error = 'connection_failed'", body)


class SecurityHeaderTests(unittest.TestCase):
    def setUp(self):
        app.config.update(TESTING=True)
        self.client = app.test_client()

    def test_csp_is_served_report_only_by_default(self):
        r = self.client.get('/api/health')
        self.assertIn('Content-Security-Policy-Report-Only', r.headers)
        self.assertNotIn('Content-Security-Policy', r.headers)
        policy = r.headers['Content-Security-Policy-Report-Only']
        for directive in ("default-src 'self'", "object-src 'none'",
                          "base-uri 'self'", "form-action 'self'"):
            self.assertIn(directive, policy)
        r.close()

    def test_csp_allows_the_third_parties_the_site_actually_uses(self):
        r = self.client.get('/api/health')
        policy = r.headers['Content-Security-Policy-Report-Only']
        for host in ('googletagmanager.com', 'cdnjs.cloudflare.com', 'connect.facebook.net'):
            self.assertIn(host, policy, 'CSP 未放行實際使用中的 ' + host)
        r.close()

    def test_other_security_headers(self):
        r = self.client.get('/api/health')
        self.assertEqual(r.headers.get('X-Content-Type-Options'), 'nosniff')
        self.assertEqual(r.headers.get('Referrer-Policy'), 'strict-origin-when-cross-origin')
        r.close()


class TripSyncConsistencyTests(unittest.TestCase):
    def setUp(self):
        self.app_src = src('app.py')
        self.body = self.app_src.split('def _sync_completed_order_trip')[1].split('@app.route')[0]

    def test_trip_follows_the_order_to_the_new_member(self):
        self.assertIn('member_id=EXCLUDED.member_id', self.body)
        self.assertIn('UPDATE member_points SET member_id=%s WHERE trip_id=%s', self.body)
        self.assertIn('recalculate_member(cur, previous_member_id)', self.body)

    def test_upgrade_notice_is_deferred_until_after_commit(self):
        """LINE 推播是十幾秒的網路呼叫，不能放在交易裡佔著訂單列鎖。"""
        self.assertNotIn('_line_api_call', self.body)
        self.assertIn("'notify': notify", self.body)
        self.assertEqual(2, self.app_src.count("if member_sync and member_sync.get('notify'):"))

    def test_manual_counts_trip_override_still_wins(self):
        conflict = re.search(r'ON CONFLICT \(source_type,source_ref\) DO UPDATE SET(.*?)RETURNING',
                             self.body, re.S).group(1)
        self.assertNotIn('counts_trip', conflict)


class HealthCheckCalibrationTests(unittest.TestCase):
    def setUp(self):
        self.hc = src('scripts/daily_health_check.py')

    def test_missing_sitemap_is_a_warning_not_a_gate(self):
        """設定字串對不上是設定問題，不該暫停 P3 開發。"""
        self.assertNotIn('"critical", "正式 sitemap 尚未提交"', self.hc)
        self.assertIn('請確認 GSC_SITEMAP_URL', self.hc)

    def test_sitemap_lookup_falls_back_to_suffix_match(self):
        self.assertIn('.endswith(tail)', self.hc)

    def test_only_an_index_drop_is_critical(self):
        self.assertIn('status = "critical" if dropped else ("warning" if errors else "ok")', self.hc)

    def test_fresh_deploy_gets_a_grace_period(self):
        self.assertIn('def _deploy_grace_minutes', self.hc)
        self.assertIn('grace < 30', self.hc)

    def test_zero_submission_attempts_with_traffic_warns(self):
        self.assertIn('elif not attempts and pageviews >= 100:', self.hc)


@unittest.skipIf(yaml is None, '未安裝 pyyaml，跳過 workflow YAML 驗證')
class WorkflowGuardTests(unittest.TestCase):
    def load(self, name):
        return yaml.safe_load(src('.github/workflows/' + name))

    def test_gate_step_is_skipped_when_the_report_is_missing(self):
        raw = src('.github/workflows/daily-health-check.yml')
        self.assertIn("hashFiles('health-report.json') != ''", raw)
        self.assertIn('未產出 health-report.json', raw)

    def test_conversion_report_keeps_artifacts_on_failure(self):
        raw = src('.github/workflows/weekly-conversion-report.yml')
        self.assertIn('continue-on-error: true', raw)
        self.assertIn('if: always()', raw)
        self.assertIn("steps.report.outcome == 'failure'", raw)

    def test_all_workflows_stay_valid_yaml(self):
        for name in ('daily-health-check.yml', 'weekly-conversion-report.yml',
                     'weekly-seo-audit.yml'):
            self.assertIn('jobs', self.load(name))


if __name__ == '__main__':
    unittest.main()


class SchemaMigrationRunnerTests(unittest.TestCase):
    """schema DDL 必須只由 migrate.py 單次執行，而且失敗要擋下部署。

    多個 gunicorn worker 各自跑 init_db() 會在全新資料庫上互相競爭，
    其中一方拿到 duplicate 錯誤；會員資料表那段又是 fail-open，
    結果 schema 只建到一半卻沒有人發現——members.merged_into_member_id
    沒建起來時，每一個會員 API 都會在 _member_row() 上 500。
    """

    def test_start_command_runs_migrate_before_gunicorn(self):
        for name in ('railway.json', 'Procfile'):
            text = src(name)
            self.assertIn('python migrate.py', text, name)
            self.assertLess(text.index('python migrate.py'), text.index('gunicorn'),
                            f'{name}：migrate 必須排在 gunicorn 之前')
            self.assertIn('SKIP_SCHEMA_INIT=1', text, name)

    def test_workers_do_not_run_ddl_on_import(self):
        app_src = src('app.py')
        self.assertIn("os.environ.get('SKIP_SCHEMA_INIT') == '1'", app_src)
        # 設了旗標就必須連 before_request 的補建也一起關掉，否則第一批請求仍會競爭建表。
        marker = app_src.index("os.environ.get('SKIP_SCHEMA_INIT') == '1'")
        self.assertIn('_db_initialized = True', app_src[marker:marker + 400])

    def test_migrate_verifies_schema_and_fails_closed(self):
        text = src('migrate.py')
        # init_db() 會吞掉會員資料表的錯誤，所以「跑完」不等於「建好」，一定要回查。
        self.assertIn('information_schema', text)
        self.assertIn('merged_into_member_id', text)
        for table in ('member_identities', 'order_claims', 'point_wallet'):
            self.assertIn(table, text)
        self.assertIn('sys.exit(main())', text)


class BlogViewCountTests(unittest.TestCase):
    """文章瀏覽數：只給後台看，且計數失敗不可以影響讀者。"""

    def test_public_apis_never_expose_view_count(self):
        app_src = src('app.py')
        # _post_public 同時餵給 /api/posts/<slug>（SELECT *），沒有 pop 就會外流。
        self.assertIn("r.pop('view_count', None)", app_src)

    def test_admin_list_adds_view_count_back(self):
        app_src = src('app.py')
        self.assertIn("row['view_count'] = int(r.get('view_count') or 0)", app_src)
        self.assertIn('view_count', src('admin.html'))

    def test_counting_failure_cannot_break_the_article_page(self):
        app_src = src('app.py')
        start = app_src.index('def blog_post(slug):')
        body = app_src[start:start + 1600]
        # UPDATE 必須包在自己的 try 裡；跟著外層 except 一起炸的話 p 會變 None → 讀者看到 404。
        self.assertIn('[BLOG VIEW COUNT]', body)
        self.assertIn('conn.rollback()', body)
        self.assertLess(body.index('UPDATE posts SET view_count'), body.index('[BLOG VIEW COUNT]'))

    def test_bots_and_admin_previews_are_not_counted(self):
        app_src = src('app.py')
        self.assertIn('_BOT_UA_MARKERS', app_src)
        self.assertIn('return not current_admin()', app_src)
        for marker in ('bot', 'crawler', 'spider', 'facebookexternalhit'):
            self.assertIn(f"'{marker}'", app_src)

    def test_column_is_migrated_not_only_in_create_table(self):
        # CREATE TABLE IF NOT EXISTS 不會改既有資料表，正式站只會拿到舊結構。
        self.assertIn('ALTER TABLE posts ADD COLUMN IF NOT EXISTS view_count',
                      src('app.py'))
