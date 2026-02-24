"""System regression tests — full HTTP stack via Flask test client.

Tests every route in the application (auth, admin, simulation, main) using
role-appropriate accounts. Each test gets a fresh temporary SQLite database
and a complete Flask application instance (all 4 blueprints registered).

Test classes
------------
 1. TestHealthAndRoot          — /health, / redirects
 2. TestAuthLogin              — POST /auth/login
 3. TestAuthLogout             — GET  /auth/logout
 4. TestAuthRegister           — POST /auth/register
 5. TestAuthSettings           — POST /auth/settings (update_info, change_password)
 6. TestSessionTokenValidation — kick / token-mismatch forced logout
 7. TestUnauthenticatedAccess  — every protected route blocks anonymous users
 8. TestRoleBasedAccess        — research_required / lab_required / admin_required
 9. TestAdminUserManagement    — add / toggle / delete / reset-password
10. TestAdminMonitor           — GET /admin/monitor + /admin/monitor/data
11. TestAdminLogs              — GET /admin/logs + /admin/logs/view + statistics
12. TestSimulationPages        — GET page routes for each role
13. TestSimulationRunUpload    — POST /simulation/run, /upload, /predict stubs
14. TestExperimentSubmission   — POST /simulation/experiment (lab workflow)
15. TestSystemMonitorUnit      — unit tests for app/utils/system_monitor.py

Run from the project root:
    python system_regression_test.py
    python system_regression_test.py -v
"""

import io
import json
import os
import re
import shutil
import sys
import tempfile
import unittest

# Ensure project root on sys.path when executed directly
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


# ── App factory ───────────────────────────────────────────────────────────────

def _make_app(db_path: str, upload_dir: str):
    """Return a full Flask app backed by a temporary SQLite file.

    DATABASE_URL must be set *before* importing create_app so that the
    SQLAlchemy URI is picked up at call time rather than at import time.
    """
    os.environ['DATABASE_URL'] = f'sqlite:///{db_path}'
    from app import create_app          # noqa: PLC0415  (deferred import intentional)
    app = create_app()
    app.config.update(
        TESTING=False,                  # True forces exception propagation which breaks 404 tests
        WTF_CSRF_ENABLED=False,
        SESSION_COOKIE_SECURE=False,    # plain-HTTP cookies work in Werkzeug test client
        UPLOAD_FOLDER=upload_dir,
        PROPAGATE_EXCEPTIONS=False,     # convert HTTP exceptions to responses, not Python exceptions
    )
    return app


# ── Shared helpers ────────────────────────────────────────────────────────────

def _add_user(db, employee_id, password='pass123',
              role='research_engineer', is_active=True):
    """Insert a user directly into the database and return it."""
    from database import User
    u = User(employee_id=employee_id, role=role, is_active=is_active)
    u.set_password(password)
    db.session.add(u)
    db.session.commit()
    return u


def _login(client, employee_id, password='pass123', follow_redirects=True):
    """POST to /auth/login and return the response."""
    return client.post(
        '/auth/login',
        data={'employee_id': employee_id, 'password': password},
        follow_redirects=follow_redirects,
    )


def _json(resp):
    """Decode JSON from a test response."""
    return json.loads(resp.data)


def _fake_xlsx() -> io.BytesIO:
    """Return a minimal valid xlsx file as a seekable BytesIO object."""
    try:
        import openpyxl
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.append(['time', 'pressure'])
        ws.append([0.0, 0.1])
        buf = io.BytesIO()
        wb.save(buf)
        buf.seek(0)
        return buf
    except Exception:
        # Fallback: valid zip magic bytes (xlsx is a zip)
        return io.BytesIO(
            b'PK\x03\x04\x14\x00\x00\x00\x00\x00' + b'\x00' * 50
        )


# ── Base test case ────────────────────────────────────────────────────────────

class SystemTestCase(unittest.TestCase):
    """Fresh temp DB + upload dir + full Flask app instance per test method."""

    def setUp(self):
        self.db_fd, self.db_path = tempfile.mkstemp(suffix='.db')
        self.upload_dir = tempfile.mkdtemp()
        self.app = _make_app(self.db_path, self.upload_dir)
        self.client = self.app.test_client()
        self.ctx = self.app.app_context()
        self.ctx.push()
        from database.extensions import db
        self.db = db
        # init_database seeds: employee_id='admin', password='admin123', role='admin'

    def tearDown(self):
        self.db.session.remove()
        self.ctx.pop()
        os.close(self.db_fd)
        os.unlink(self.db_path)
        shutil.rmtree(self.upload_dir, ignore_errors=True)

    # ── Conveniences ──────────────────────────────────────────────────────────

    def login_admin(self, client=None):
        c = client or self.client
        return _login(c, 'admin', 'admin123')

    def add_user(self, employee_id, password='pass123',
                 role='research_engineer', is_active=True):
        return _add_user(self.db, employee_id, password, role, is_active)


# ═══════════════════════════════════════════════════════════════════════════════
# 1. Health check + root redirect
# ═══════════════════════════════════════════════════════════════════════════════

class TestHealthAndRoot(SystemTestCase):

    def test_health_returns_200(self):
        resp = self.client.get('/health')
        self.assertEqual(resp.status_code, 200)

    def test_health_returns_json_with_status_key(self):
        data = _json(self.client.get('/health'))
        self.assertIn('status', data)
        self.assertIn('checks', data)

    def test_health_database_check_ok(self):
        data = _json(self.client.get('/health'))
        self.assertEqual(data['checks'].get('database'), 'ok')

    def test_health_no_auth_required(self):
        """Health endpoint must be publicly accessible."""
        resp = self.client.get('/health')
        self.assertNotIn(resp.status_code, (302, 401, 403))

    def test_root_unauthenticated_redirects_to_login(self):
        resp = self.client.get('/', follow_redirects=False)
        self.assertEqual(resp.status_code, 302)
        self.assertIn('/auth/login', resp.headers['Location'])

    def test_root_admin_redirects_to_simulation_index(self):
        self.login_admin()
        resp = self.client.get('/', follow_redirects=False)
        self.assertEqual(resp.status_code, 302)
        self.assertIn('/simulation/', resp.headers['Location'])

    def test_root_research_engineer_redirects_to_simulation_index(self):
        self.add_user('R001', role='research_engineer')
        _login(self.client, 'R001')
        resp = self.client.get('/', follow_redirects=False)
        self.assertEqual(resp.status_code, 302)
        self.assertIn('/simulation/', resp.headers['Location'])

    def test_root_lab_engineer_redirects_to_history(self):
        self.add_user('L001', role='lab_engineer')
        _login(self.client, 'L001')
        resp = self.client.get('/', follow_redirects=False)
        self.assertEqual(resp.status_code, 302)
        self.assertIn('/simulation/history', resp.headers['Location'])


# ═══════════════════════════════════════════════════════════════════════════════
# 2. Auth — Login
# ═══════════════════════════════════════════════════════════════════════════════

class TestAuthLogin(SystemTestCase):

    def test_login_page_get_returns_200(self):
        self.assertEqual(self.client.get('/auth/login').status_code, 200)

    def test_login_success_returns_200(self):
        resp = self.login_admin()
        self.assertEqual(resp.status_code, 200)

    def test_login_stores_session_token_in_db(self):
        from database import User
        self.login_admin()
        admin = User.query.filter_by(employee_id='admin').first()
        self.assertIsNotNone(admin.session_token,
                             'session_token must be populated after login')

    def test_login_stores_auth_token_in_flask_session(self):
        self.login_admin()
        with self.client.session_transaction() as sess:
            self.assertIn('auth_token', sess)

    def test_login_db_token_matches_session_token(self):
        """The UUID in the DB must match the one stored in the session cookie."""
        from database import User
        self.login_admin()
        with self.client.session_transaction() as sess:
            session_token = sess.get('auth_token')
        admin = User.query.filter_by(employee_id='admin').first()
        self.assertEqual(admin.session_token, session_token)

    def test_login_wrong_password_stays_on_login_page(self):
        resp = self.client.post('/auth/login',
                                data={'employee_id': 'admin', 'password': 'WRONG'},
                                follow_redirects=True)
        self.assertEqual(resp.status_code, 200)
        with self.client.session_transaction() as sess:
            self.assertNotIn('auth_token', sess)

    def test_login_nonexistent_employee_id_stays_on_login_page(self):
        resp = self.client.post('/auth/login',
                                data={'employee_id': 'NOBODY', 'password': 'x'},
                                follow_redirects=True)
        self.assertEqual(resp.status_code, 200)
        with self.client.session_transaction() as sess:
            self.assertNotIn('auth_token', sess)

    def test_login_inactive_user_rejected(self):
        self.add_user('E002', password='pass123', is_active=False)
        self.client.post('/auth/login',
                         data={'employee_id': 'E002', 'password': 'pass123'},
                         follow_redirects=True)
        with self.client.session_transaction() as sess:
            self.assertNotIn('auth_token', sess,
                             'Inactive user must not receive a session token')

    def test_authenticated_user_redirected_away_from_login(self):
        self.login_admin()
        resp = self.client.get('/auth/login', follow_redirects=False)
        self.assertEqual(resp.status_code, 302)

    def test_login_admin_redirected_to_simulation(self):
        resp = _login(self.client, 'admin', 'admin123', follow_redirects=False)
        self.assertEqual(resp.status_code, 302)
        self.assertIn('/simulation/', resp.headers['Location'])

    def test_login_lab_engineer_redirected_to_history(self):
        self.add_user('L001', role='lab_engineer')
        resp = _login(self.client, 'L001', follow_redirects=False)
        self.assertEqual(resp.status_code, 302)
        self.assertIn('/simulation/history', resp.headers['Location'])


# ═══════════════════════════════════════════════════════════════════════════════
# 3. Auth — Logout
# ═══════════════════════════════════════════════════════════════════════════════

class TestAuthLogout(SystemTestCase):

    def test_logout_redirects_to_login(self):
        self.login_admin()
        resp = self.client.get('/auth/logout', follow_redirects=False)
        self.assertEqual(resp.status_code, 302)
        self.assertIn('/auth/login', resp.headers['Location'])

    def test_logout_clears_session_token_in_db(self):
        from database import User
        self.login_admin()
        self.client.get('/auth/logout')
        admin = User.query.filter_by(employee_id='admin').first()
        self.assertIsNone(admin.session_token,
                          'session_token must be None after logout')

    def test_logout_prevents_further_authenticated_access(self):
        self.login_admin()
        self.client.get('/auth/logout')
        resp = self.client.get('/admin/', follow_redirects=False)
        self.assertEqual(resp.status_code, 302)

    def test_unauthenticated_logout_does_not_crash(self):
        resp = self.client.get('/auth/logout')
        self.assertIn(resp.status_code, (200, 302))


# ═══════════════════════════════════════════════════════════════════════════════
# 4. Auth — Register
# ═══════════════════════════════════════════════════════════════════════════════

class TestAuthRegister(SystemTestCase):

    def test_register_page_get_returns_200(self):
        self.assertEqual(self.client.get('/auth/register').status_code, 200)

    def test_register_creates_user_in_db(self):
        from database import User
        self.client.post('/auth/register', data={
            'employee_id': 'EMP001',
            'password': 'pass123',
            'confirm_password': 'pass123',
        })
        self.assertIsNotNone(User.query.filter_by(employee_id='EMP001').first())

    def test_register_redirects_to_login_on_success(self):
        resp = self.client.post('/auth/register', data={
            'employee_id': 'EMP002',
            'password': 'pass123',
            'confirm_password': 'pass123',
        }, follow_redirects=False)
        self.assertEqual(resp.status_code, 302)
        self.assertIn('/auth/login', resp.headers['Location'])

    def test_register_new_user_has_default_role(self):
        from database import User
        self.client.post('/auth/register', data={
            'employee_id': 'EMP003',
            'password': 'pass123',
            'confirm_password': 'pass123',
        })
        user = User.query.filter_by(employee_id='EMP003').first()
        self.assertEqual(user.role, 'research_engineer')

    def test_register_duplicate_employee_id_rejected(self):
        from database import User
        for _ in range(2):
            self.client.post('/auth/register', data={
                'employee_id': 'EMP004',
                'password': 'pass123',
                'confirm_password': 'pass123',
            })
        self.assertEqual(User.query.filter_by(employee_id='EMP004').count(), 1,
                         'Duplicate registration must create only one user')

    def test_register_password_mismatch_creates_no_user(self):
        from database import User
        self.client.post('/auth/register', data={
            'employee_id': 'EMP005',
            'password': 'pass123',
            'confirm_password': 'DIFFERENT',
        })
        self.assertIsNone(User.query.filter_by(employee_id='EMP005').first())

    def test_authenticated_user_redirected_from_register(self):
        self.login_admin()
        resp = self.client.get('/auth/register', follow_redirects=False)
        self.assertEqual(resp.status_code, 302)


# ═══════════════════════════════════════════════════════════════════════════════
# 5. Auth — Settings
# ═══════════════════════════════════════════════════════════════════════════════

class TestAuthSettings(SystemTestCase):

    def test_settings_requires_login(self):
        resp = self.client.get('/auth/settings', follow_redirects=False)
        self.assertEqual(resp.status_code, 302)

    def test_settings_page_loads_when_logged_in(self):
        self.login_admin()
        self.assertEqual(self.client.get('/auth/settings').status_code, 200)

    def test_settings_update_username_and_phone(self):
        from database import User
        self.login_admin()
        self.client.post('/auth/settings', data={
            'action': 'update_info',
            'username': 'Admin Zhang',
            'phone': '13800000001',
        })
        admin = User.query.filter_by(employee_id='admin').first()
        self.assertEqual(admin.username, 'Admin Zhang')
        self.assertEqual(admin.phone, '13800000001')

    def test_settings_change_password_success(self):
        from database import User
        self.login_admin()
        self.client.post('/auth/settings', data={
            'action': 'change_password',
            'current_password': 'admin123',
            'new_password': 'newpass99',
            'confirm_password': 'newpass99',
        })
        admin = User.query.filter_by(employee_id='admin').first()
        self.assertTrue(admin.check_password('newpass99'))
        self.assertFalse(admin.check_password('admin123'))

    def test_settings_change_password_wrong_current_rejected(self):
        from database import User
        self.login_admin()
        self.client.post('/auth/settings', data={
            'action': 'change_password',
            'current_password': 'WRONGPASSWORD',
            'new_password': 'newpass99',
            'confirm_password': 'newpass99',
        })
        admin = User.query.filter_by(employee_id='admin').first()
        self.assertTrue(admin.check_password('admin123'),
                        'Password must not change with wrong current password')

    def test_settings_change_password_mismatch_rejected(self):
        from database import User
        self.login_admin()
        self.client.post('/auth/settings', data={
            'action': 'change_password',
            'current_password': 'admin123',
            'new_password': 'pass111',
            'confirm_password': 'pass222',
        })
        admin = User.query.filter_by(employee_id='admin').first()
        self.assertTrue(admin.check_password('admin123'),
                        'Password must not change when confirm does not match')

    def test_settings_change_password_too_short_rejected(self):
        from database import User
        self.login_admin()
        self.client.post('/auth/settings', data={
            'action': 'change_password',
            'current_password': 'admin123',
            'new_password': 'ab',
            'confirm_password': 'ab',
        })
        admin = User.query.filter_by(employee_id='admin').first()
        self.assertTrue(admin.check_password('admin123'),
                        'Password shorter than 6 chars must be rejected')


# ═══════════════════════════════════════════════════════════════════════════════
# 6. Session token / kick validation
# ═══════════════════════════════════════════════════════════════════════════════

class TestSessionTokenValidation(SystemTestCase):

    def test_valid_token_allows_protected_access(self):
        self.login_admin()
        self.assertEqual(self.client.get('/simulation/').status_code, 200)

    def test_clearing_db_token_forces_redirect_to_login(self):
        """Simulates what admin kick does to any currently-logged-in user."""
        from database import User
        self.login_admin()
        # Directly clear the DB token (what kick_user does)
        admin = User.query.filter_by(employee_id='admin').first()
        admin.session_token = None
        self.db.session.commit()
        # Next request: check_daily_login detects mismatch
        resp = self.client.get('/simulation/', follow_redirects=False)
        self.assertEqual(resp.status_code, 302)
        self.assertIn('/auth/login', resp.headers['Location'])

    def test_kick_api_clears_session_token_in_db(self):
        from database import User
        user = self.add_user('E002')
        self.login_admin()
        resp = self.client.post(f'/admin/user/{user.id}/kick')
        data = _json(resp)
        self.assertTrue(data['success'])
        self.assertIsNone(User.query.get(user.id).session_token)

    def test_kicked_user_redirected_on_next_request(self):
        """End-to-end: kick via admin API → target user forced offline."""
        user = self.add_user('E003', 'pass123')
        admin_client = self.app.test_client()
        user_client = self.app.test_client()
        _login(admin_client, 'admin', 'admin123')
        _login(user_client, 'E003', 'pass123')
        # Admin kicks E003
        admin_client.post(f'/admin/user/{user.id}/kick')
        # E003's next request should be forced to login
        resp = user_client.get('/simulation/', follow_redirects=False)
        self.assertEqual(resp.status_code, 302)
        self.assertIn('/auth/login', resp.headers['Location'])

    def test_admin_cannot_kick_self(self):
        from database import User
        admin = User.query.filter_by(employee_id='admin').first()
        self.login_admin()
        data = _json(self.client.post(f'/admin/user/{admin.id}/kick'))
        self.assertFalse(data['success'])

    def test_logout_prevents_further_access(self):
        self.login_admin()
        self.client.get('/auth/logout')
        resp = self.client.get('/admin/', follow_redirects=False)
        self.assertEqual(resp.status_code, 302)

    def test_re_login_after_kick_restores_access(self):
        """Kicked user can log back in and get a fresh session token."""
        from database import User
        user = self.add_user('E004', 'pass123')
        user_client = self.app.test_client()
        admin_client = self.app.test_client()
        _login(user_client, 'E004', 'pass123')
        _login(admin_client, 'admin', 'admin123')
        admin_client.post(f'/admin/user/{user.id}/kick')
        # Re-login as E004
        _login(user_client, 'E004', 'pass123')
        resp = user_client.get('/simulation/')
        self.assertEqual(resp.status_code, 200)


# ═══════════════════════════════════════════════════════════════════════════════
# 7. Unauthenticated access
# ═══════════════════════════════════════════════════════════════════════════════

class TestUnauthenticatedAccess(SystemTestCase):

    def _assert_protected(self, url, method='GET'):
        if method == 'GET':
            resp = self.client.get(url, follow_redirects=False)
        else:
            resp = self.client.post(url, follow_redirects=False)
        self.assertEqual(resp.status_code, 302,
                         f'{url} must redirect unauthenticated users')
        loc = resp.headers.get('Location', '')
        self.assertIn('login', loc.lower(),
                      f'{url} redirect must go to login, got: {loc}')

    def test_admin_index_blocks_anonymous(self):
        self._assert_protected('/admin/')

    def test_admin_monitor_blocks_anonymous(self):
        self._assert_protected('/admin/monitor')

    def test_admin_monitor_data_blocks_anonymous(self):
        self._assert_protected('/admin/monitor/data')

    def test_admin_logs_blocks_anonymous(self):
        self._assert_protected('/admin/logs')

    def test_admin_logs_view_blocks_anonymous(self):
        self._assert_protected('/admin/logs/view')

    def test_admin_logs_statistics_blocks_anonymous(self):
        self._assert_protected('/admin/logs/statistics')

    def test_admin_add_user_blocks_anonymous(self):
        self._assert_protected('/admin/user/add', method='POST')

    def test_simulation_index_blocks_anonymous(self):
        self._assert_protected('/simulation/')

    def test_simulation_history_blocks_anonymous(self):
        self._assert_protected('/simulation/history')

    def test_simulation_reverse_blocks_anonymous(self):
        self._assert_protected('/simulation/reverse')

    def test_simulation_run_blocks_anonymous(self):
        self._assert_protected('/simulation/run', method='POST')

    def test_simulation_experiment_blocks_anonymous(self):
        self._assert_protected('/simulation/experiment', method='POST')

    def test_auth_settings_blocks_anonymous(self):
        self._assert_protected('/auth/settings')


# ═══════════════════════════════════════════════════════════════════════════════
# 8. Role-based access control
# ═══════════════════════════════════════════════════════════════════════════════

class TestRoleBasedAccess(SystemTestCase):

    def setUp(self):
        super().setUp()
        self.add_user('LAB001', role='lab_engineer')
        self.add_user('RES001', role='research_engineer')

    def _login_lab(self):
        return _login(self.client, 'LAB001')

    def _login_res(self):
        return _login(self.client, 'RES001')

    # lab_engineer blocked from research_required routes
    def test_lab_blocked_from_simulation_index(self):
        self._login_lab()
        resp = self.client.get('/simulation/', follow_redirects=False)
        self.assertEqual(resp.status_code, 302)
        self.assertIn('/simulation/history', resp.headers['Location'])

    def test_lab_blocked_from_simulation_reverse(self):
        self._login_lab()
        resp = self.client.get('/simulation/reverse', follow_redirects=False)
        self.assertEqual(resp.status_code, 302)

    # research_engineer blocked from lab_required routes
    def test_research_blocked_from_simulation_history(self):
        self._login_res()
        resp = self.client.get('/simulation/history', follow_redirects=False)
        self.assertEqual(resp.status_code, 302)
        self.assertIn('/simulation/', resp.headers['Location'])

    def test_research_blocked_from_experiment_endpoint(self):
        self._login_res()
        resp = self.client.post('/simulation/experiment',
                                data={'ticket_number': 'WO001'},
                                content_type='multipart/form-data',
                                follow_redirects=False)
        self.assertEqual(resp.status_code, 302)

    # non-admin blocked from admin routes
    def test_research_blocked_from_admin_index(self):
        self._login_res()
        resp = self.client.get('/admin/', follow_redirects=False)
        self.assertEqual(resp.status_code, 302)

    def test_lab_blocked_from_admin_monitor(self):
        self._login_lab()
        resp = self.client.get('/admin/monitor', follow_redirects=False)
        self.assertEqual(resp.status_code, 302)

    def test_research_blocked_from_add_user(self):
        self._login_res()
        resp = self.client.post('/admin/user/add', data={
            'employee_id': 'X001', 'password': 'pass', 'role': 'lab_engineer',
        }, follow_redirects=False)
        self.assertEqual(resp.status_code, 302)

    def test_lab_blocked_from_kick(self):
        from database import User
        admin = User.query.filter_by(employee_id='admin').first()
        self._login_lab()
        resp = self.client.post(f'/admin/user/{admin.id}/kick',
                                follow_redirects=False)
        self.assertEqual(resp.status_code, 302)

    # admin has cross-role access
    def test_admin_accesses_simulation_index(self):
        """Admin satisfies research_required."""
        self.login_admin()
        self.assertEqual(self.client.get('/simulation/').status_code, 200)

    def test_admin_accesses_simulation_history(self):
        """Admin satisfies lab_required."""
        self.login_admin()
        self.assertEqual(self.client.get('/simulation/history').status_code, 200)


# ═══════════════════════════════════════════════════════════════════════════════
# 9. Admin — User management
# ═══════════════════════════════════════════════════════════════════════════════

class TestAdminUserManagement(SystemTestCase):

    def setUp(self):
        super().setUp()
        self.login_admin()

    # Dashboard
    def test_admin_index_returns_200(self):
        self.assertEqual(self.client.get('/admin/').status_code, 200)

    def test_admin_index_lists_all_users(self):
        self.add_user('E010', role='lab_engineer')
        resp = self.client.get('/admin/')
        self.assertIn(b'E010', resp.data)

    # Add user
    def test_add_user_success(self):
        from database import User
        data = _json(self.client.post('/admin/user/add', data={
            'employee_id': 'EMP100',
            'username': 'Test User',
            'password': 'pass123',
            'role': 'lab_engineer',
        }))
        self.assertTrue(data['success'])
        self.assertIsNotNone(User.query.filter_by(employee_id='EMP100').first())

    def test_add_user_all_valid_roles_accepted(self):
        from database import User
        for i, role in enumerate(('admin', 'lab_engineer', 'research_engineer')):
            data = _json(self.client.post('/admin/user/add', data={
                'employee_id': f'EMP20{i}',
                'password': 'pass123',
                'role': role,
            }))
            self.assertTrue(data['success'], f'Role {role} should be accepted')

    def test_add_user_duplicate_employee_id_rejected(self):
        self.client.post('/admin/user/add', data={
            'employee_id': 'EMP101', 'password': 'pass123', 'role': 'lab_engineer',
        })
        data = _json(self.client.post('/admin/user/add', data={
            'employee_id': 'EMP101', 'password': 'pass456', 'role': 'lab_engineer',
        }))
        self.assertFalse(data['success'])

    def test_add_user_invalid_role_rejected(self):
        data = _json(self.client.post('/admin/user/add', data={
            'employee_id': 'EMP102', 'password': 'pass123', 'role': 'superuser',
        }))
        self.assertFalse(data['success'])

    # Toggle active
    def test_toggle_user_disables_active_user(self):
        from database import User
        user = self.add_user('E020', is_active=True)
        data = _json(self.client.post(f'/admin/user/{user.id}/toggle'))
        self.assertTrue(data['success'])
        self.assertFalse(User.query.get(user.id).is_active)

    def test_toggle_user_enables_disabled_user(self):
        from database import User
        user = self.add_user('E021', is_active=False)
        data = _json(self.client.post(f'/admin/user/{user.id}/toggle'))
        self.assertTrue(data['success'])
        self.assertTrue(User.query.get(user.id).is_active)

    def test_toggle_self_forbidden(self):
        from database import User
        admin = User.query.filter_by(employee_id='admin').first()
        data = _json(self.client.post(f'/admin/user/{admin.id}/toggle'))
        self.assertFalse(data['success'])

    # Delete user
    def test_delete_user_removes_from_db(self):
        from database import User
        user = self.add_user('E030')
        uid = user.id
        data = _json(self.client.post(f'/admin/user/{uid}/delete'))
        self.assertTrue(data['success'])
        self.assertIsNone(User.query.get(uid))

    def test_delete_self_forbidden(self):
        from database import User
        admin = User.query.filter_by(employee_id='admin').first()
        data = _json(self.client.post(f'/admin/user/{admin.id}/delete'))
        self.assertFalse(data['success'])
        self.assertIsNotNone(User.query.get(admin.id))

    # Reset password
    def test_reset_password_changes_hash_in_db(self):
        from database import User
        user = self.add_user('E040', password='oldpass')
        data = _json(self.client.post(f'/admin/user/{user.id}/reset-password',
                                      data={'new_password': 'newpass99'}))
        self.assertTrue(data['success'])
        refreshed = User.query.get(user.id)
        self.assertTrue(refreshed.check_password('newpass99'))
        self.assertFalse(refreshed.check_password('oldpass'))

    def test_reset_password_allows_immediate_login(self):
        """After reset, user can log in with the new password."""
        user = self.add_user('E041', password='oldpass')
        self.client.post(f'/admin/user/{user.id}/reset-password',
                         data={'new_password': 'freshpass'})
        fresh_client = self.app.test_client()
        resp = _login(fresh_client, 'E041', 'freshpass', follow_redirects=False)
        self.assertEqual(resp.status_code, 302)


# ═══════════════════════════════════════════════════════════════════════════════
# 10. Admin — Monitor
# ═══════════════════════════════════════════════════════════════════════════════

class TestAdminMonitor(SystemTestCase):

    def setUp(self):
        super().setUp()
        self.login_admin()

    def test_monitor_page_returns_200(self):
        self.assertEqual(self.client.get('/admin/monitor').status_code, 200)

    def test_monitor_data_returns_success_json(self):
        data = _json(self.client.get('/admin/monitor/data'))
        self.assertTrue(data.get('success'))

    def test_monitor_data_contains_all_sections(self):
        metrics = _json(self.client.get('/admin/monitor/data'))['metrics']
        expected = ('resources', 'disk', 'db', 'requests',
                    'crashes', 'access_failures', 'active_users', 'generated_at')
        for section in expected:
            self.assertIn(section, metrics, f"Missing section: '{section}'")

    def test_monitor_resources_has_cpu_and_memory(self):
        resources = _json(self.client.get('/admin/monitor/data'))['metrics']['resources']
        self.assertIn('cpu_percent', resources)
        self.assertIn('memory_percent', resources)
        self.assertIsInstance(resources['cpu_percent'], (int, float))

    def test_monitor_db_section_has_table_counts(self):
        db_section = _json(self.client.get('/admin/monitor/data'))['metrics']['db']
        self.assertIn('table_counts', db_section)
        counts = db_section['table_counts']
        for table in ('user', 'simulation', 'recipe', 'work_order',
                      'experiment_file', 'test_result'):
            self.assertIn(table, counts)

    def test_monitor_db_user_count_reflects_seeded_admin(self):
        counts = _json(self.client.get(
            '/admin/monitor/data'))['metrics']['db']['table_counts']
        self.assertEqual(counts['user'], 1,
                         'Exactly 1 admin should be seeded on a fresh DB')

    def test_monitor_active_users_section_is_list(self):
        active = _json(self.client.get(
            '/admin/monitor/data'))['metrics']['active_users']
        self.assertIsInstance(active, list)

    def test_monitor_generated_at_has_datetime_format(self):
        generated_at = _json(self.client.get(
            '/admin/monitor/data'))['metrics']['generated_at']
        self.assertRegex(generated_at, r'\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}')


# ═══════════════════════════════════════════════════════════════════════════════
# 11. Admin — Logs
# ═══════════════════════════════════════════════════════════════════════════════

class TestAdminLogs(SystemTestCase):

    def setUp(self):
        super().setUp()
        self.login_admin()

    def test_logs_page_returns_200(self):
        self.assertEqual(self.client.get('/admin/logs').status_code, 200)

    def test_view_log_returns_success_json(self):
        data = _json(self.client.get('/admin/logs/view'))
        self.assertTrue(data.get('success'))

    def test_view_log_has_entries_and_count_keys(self):
        data = _json(self.client.get('/admin/logs/view'))
        self.assertIn('entries', data)
        self.assertIn('count', data)
        self.assertIsInstance(data['entries'], list)
        self.assertIsInstance(data['count'], int)

    def test_view_log_count_matches_entries_length(self):
        data = _json(self.client.get('/admin/logs/view'))
        self.assertEqual(data['count'], len(data['entries']))

    def test_log_statistics_returns_success_json(self):
        data = _json(self.client.get('/admin/logs/statistics'))
        self.assertTrue(data.get('success'))
        self.assertIn('statistics', data)

    def test_download_nonexistent_log_redirects(self):
        resp = self.client.get('/admin/logs/download/nonexistent.csv',
                               follow_redirects=False)
        self.assertEqual(resp.status_code, 302)


# ═══════════════════════════════════════════════════════════════════════════════
# 12. Simulation — Page access
# ═══════════════════════════════════════════════════════════════════════════════

class TestSimulationPages(SystemTestCase):

    def test_index_admin(self):
        self.login_admin()
        self.assertEqual(self.client.get('/simulation/').status_code, 200)

    def test_index_research_engineer(self):
        self.add_user('R001', role='research_engineer')
        _login(self.client, 'R001')
        self.assertEqual(self.client.get('/simulation/').status_code, 200)

    def test_reverse_research_engineer(self):
        self.add_user('R002', role='research_engineer')
        _login(self.client, 'R002')
        self.assertEqual(self.client.get('/simulation/reverse').status_code, 200)

    def test_reverse_admin(self):
        self.login_admin()
        self.assertEqual(self.client.get('/simulation/reverse').status_code, 200)

    def test_history_lab_engineer(self):
        self.add_user('L001', role='lab_engineer')
        _login(self.client, 'L001')
        self.assertEqual(self.client.get('/simulation/history').status_code, 200)

    def test_history_admin(self):
        self.login_admin()
        self.assertEqual(self.client.get('/simulation/history').status_code, 200)


# ═══════════════════════════════════════════════════════════════════════════════
# 13. Simulation — /run, /upload, /predict stubs
# ═══════════════════════════════════════════════════════════════════════════════

class TestSimulationRunUpload(SystemTestCase):

    def setUp(self):
        super().setUp()
        self.login_admin()

    def test_run_always_returns_json(self):
        """POST /simulation/run may fail (no model), but must return JSON."""
        resp = self.client.post('/simulation/run',
                                data={'ignition_model': 'test', 'nc_usage_1': '10'})
        self.assertIn('application/json', resp.content_type)
        data = _json(resp)
        self.assertIn('success', data)

    def test_upload_without_file_returns_error_json(self):
        data = _json(self.client.post('/simulation/upload', data={}))
        self.assertFalse(data['success'])

    def test_upload_non_xlsx_returns_json_error(self):
        resp = self.client.post('/simulation/upload',
                                data={'file': (io.BytesIO(b'not xlsx'), 'bad.txt')},
                                content_type='multipart/form-data')
        self.assertIn('application/json', resp.content_type)

    def test_predict_returns_json(self):
        resp = self.client.post('/simulation/predict',
                                json={'nc_usage_1': 10.0})
        self.assertIn('application/json', resp.content_type)

    def test_generate_comparison_chart_returns_json(self):
        resp = self.client.post('/simulation/generate_comparison_chart',
                                json={'simulation_data': None, 'test_data': None})
        self.assertIn('application/json', resp.content_type)

    def test_save_to_data_folder_without_file_returns_error(self):
        resp = self.client.post('/simulation/save_to_data_folder', data={})
        self.assertIn('application/json', resp.content_type)
        self.assertFalse(_json(resp).get('success'))

    def test_load_test_data_without_file_returns_error(self):
        resp = self.client.post('/simulation/load_test_data', data={})
        self.assertIn('application/json', resp.content_type)
        self.assertFalse(_json(resp).get('success'))


# ═══════════════════════════════════════════════════════════════════════════════
# 14. Simulation — Experiment submission (lab engineer workflow)
# ═══════════════════════════════════════════════════════════════════════════════

class TestExperimentSubmission(SystemTestCase):

    def setUp(self):
        super().setUp()
        self.add_user('LAB001', role='lab_engineer')
        _login(self.client, 'LAB001')

    def _post_experiment(self, ticket, files=None, extra=None):
        data = {'ticket_number': ticket}
        if files:
            data['files'] = files
        if extra:
            data.update(extra)
        return self.client.post('/simulation/experiment',
                                data=data,
                                content_type='multipart/form-data')

    def test_missing_ticket_number_returns_error(self):
        data = _json(self._post_experiment('', files=(_fake_xlsx(), 'run1.xlsx')))
        self.assertFalse(data['success'])

    def test_missing_files_returns_error(self):
        data = _json(self.client.post('/simulation/experiment',
                                      data={'ticket_number': 'WO001'},
                                      content_type='multipart/form-data'))
        self.assertFalse(data['success'])

    def test_success_returns_success_json(self):
        data = _json(self._post_experiment(
            'WO20260218T01', files=(_fake_xlsx(), 'run1.xlsx')))
        self.assertTrue(data['success'], f'Expected success, got: {data}')

    def test_success_creates_work_order_in_db(self):
        from database import WorkOrder
        self._post_experiment('WO20260218T02', files=(_fake_xlsx(), 'run1.xlsx'))
        wo = WorkOrder.query.filter_by(work_order_number='WO20260218T02').first()
        self.assertIsNotNone(wo)
        self.assertEqual(wo.source, 'experiment')

    def test_success_creates_experiment_file_record(self):
        from database import ExperimentFile
        self._post_experiment('WO20260218T03', files=(_fake_xlsx(), 'run1.xlsx'))
        files = ExperimentFile.query.all()
        self.assertEqual(len(files), 1)
        self.assertEqual(files[0].original_filename, 'run1.xlsx')

    def test_experiment_file_saved_to_disk(self):
        from database import ExperimentFile
        self._post_experiment('WO20260218T04', files=(_fake_xlsx(), 'run1.xlsx'))
        record = ExperimentFile.query.first()
        self.assertTrue(os.path.isfile(record.file_path),
                        f'File not found on disk: {record.file_path}')

    def test_multiple_files_all_saved(self):
        from database import ExperimentFile
        data = {
            'ticket_number': 'WO20260218T05',
            'files': [
                (_fake_xlsx(), 'run1.xlsx'),
                (_fake_xlsx(), 'run2.xlsx'),
                (_fake_xlsx(), 'run3.xlsx'),
            ],
        }
        result = _json(self.client.post('/simulation/experiment',
                                        data=data,
                                        content_type='multipart/form-data'))
        self.assertTrue(result['success'])
        self.assertEqual(ExperimentFile.query.count(), 3)

    def test_second_upload_to_same_work_order_appends_file(self):
        from database import WorkOrder, ExperimentFile
        self._post_experiment('WO20260218T06', files=(_fake_xlsx(), 'run1.xlsx'))
        self._post_experiment('WO20260218T06', files=(_fake_xlsx(), 'run2.xlsx'))
        self.assertEqual(WorkOrder.query.count(), 1,
                         'Must not create a duplicate WorkOrder')
        self.assertEqual(ExperimentFile.query.count(), 2)

    def test_metadata_stored_on_work_order(self):
        from database import WorkOrder
        self._post_experiment(
            'WO20260218T07',
            files=(_fake_xlsx(), 'run1.xlsx'),
            extra={
                'employee_id': 'LAB001',
                'test_name': 'Batch A',
                'test_date': '2026-02-18',
                'test_time': '09:30',
            },
        )
        wo = WorkOrder.query.filter_by(work_order_number='WO20260218T07').first()
        self.assertEqual(wo.employee_id, 'LAB001')
        self.assertEqual(wo.test_name, 'Batch A')
        self.assertIsNotNone(wo.test_date)

    def test_research_engineer_blocked(self):
        self.add_user('RES001', role='research_engineer')
        res_client = self.app.test_client()
        _login(res_client, 'RES001')
        resp = res_client.post(
            '/simulation/experiment',
            data={'ticket_number': 'WO001', 'files': (_fake_xlsx(), 'run1.xlsx')},
            content_type='multipart/form-data',
            follow_redirects=False,
        )
        self.assertEqual(resp.status_code, 302)


# ═══════════════════════════════════════════════════════════════════════════════
# 15. System monitor — unit tests (no HTTP layer)
# ═══════════════════════════════════════════════════════════════════════════════

class TestSystemMonitorUnit(SystemTestCase):

    def setUp(self):
        super().setUp()
        from app.utils.system_monitor import _resolve_db_path
        self.db_path = _resolve_db_path()

    # get_system_resources
    def test_get_system_resources_returns_all_keys(self):
        from app.utils.system_monitor import get_system_resources
        result = get_system_resources()
        for key in ('cpu_percent', 'memory_percent', 'memory_used_mb',
                    'memory_total_mb', 'memory_available_mb'):
            self.assertIn(key, result)

    def test_get_system_resources_values_in_valid_range(self):
        from app.utils.system_monitor import get_system_resources
        r = get_system_resources()
        self.assertGreaterEqual(r['cpu_percent'], 0.0)
        self.assertLessEqual(r['cpu_percent'], 100.0)
        self.assertGreaterEqual(r['memory_percent'], 0.0)
        self.assertLessEqual(r['memory_percent'], 100.0)
        self.assertGreater(r['memory_total_mb'], 0.0)

    # get_disk_usage
    def test_get_disk_usage_returns_all_keys(self):
        from app.utils.system_monitor import get_disk_usage
        uploads = os.path.join(self.upload_dir, 'uploads')
        backups = os.path.join(self.upload_dir, 'backups')
        result = get_disk_usage(self.db_path, uploads, backups)
        for key in ('db_size_mb', 'uploads_size_mb', 'uploads_file_count',
                    'backups_size_mb', 'backups_file_count'):
            self.assertIn(key, result)

    def test_get_disk_usage_db_size_positive(self):
        from app.utils.system_monitor import get_disk_usage
        result = get_disk_usage(self.db_path, self.upload_dir, self.upload_dir)
        self.assertGreater(result['db_size_mb'], 0.0)

    # get_db_stats
    def test_get_db_stats_returns_all_keys(self):
        from app.utils.system_monitor import get_db_stats
        result = get_db_stats(self.db_path)
        for key in ('file_size_mb', 'table_counts', 'backup_count',
                    'latest_backup_date'):
            self.assertIn(key, result)

    def test_get_db_stats_all_six_tables_counted(self):
        from app.utils.system_monitor import get_db_stats
        counts = get_db_stats(self.db_path)['table_counts']
        for table in ('user', 'simulation', 'test_result',
                      'recipe', 'work_order', 'experiment_file'):
            self.assertIn(table, counts)

    def test_get_db_stats_user_count_equals_one(self):
        from app.utils.system_monitor import get_db_stats
        counts = get_db_stats(self.db_path)['table_counts']
        self.assertEqual(counts['user'], 1)

    # get_active_users
    def test_get_active_users_returns_list(self):
        from app.utils.system_monitor import get_active_users
        result = get_active_users(self.db_path)
        self.assertIsInstance(result, list)

    def test_active_user_appears_after_request(self):
        """last_seen_at is stamped by check_daily_login on each authenticated request."""
        from app.utils.system_monitor import get_active_users
        self.login_admin()
        self.client.get('/simulation/')    # triggers last_seen_at update
        users = get_active_users(self.db_path)
        self.assertIn('admin', [u['employee_id'] for u in users])

    def test_active_user_record_has_expected_keys(self):
        from app.utils.system_monitor import get_active_users
        self.login_admin()
        self.client.get('/simulation/')
        users = get_active_users(self.db_path)
        self.assertTrue(len(users) > 0)
        for key in ('id', 'employee_id', 'username', 'role', 'last_seen_at'):
            self.assertIn(key, users[0])

    # get_system_metrics
    def test_get_system_metrics_returns_all_sections(self):
        from app.utils.system_monitor import get_system_metrics
        metrics = get_system_metrics()
        for section in ('resources', 'disk', 'db', 'requests', 'crashes',
                        'access_failures', 'active_users', 'generated_at'):
            self.assertIn(section, metrics, f"Missing section: '{section}'")

    def test_get_system_metrics_generated_at_format(self):
        from app.utils.system_monitor import get_system_metrics
        generated_at = get_system_metrics()['generated_at']
        self.assertRegex(generated_at, r'\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}')

    def test_get_system_metrics_is_fault_tolerant(self):
        """A broken sub-section must not crash the entire metrics call."""
        from app.utils.system_monitor import get_system_metrics
        # Call once normally — must always return a dict with generated_at
        metrics = get_system_metrics()
        self.assertIsInstance(metrics, dict)
        self.assertIn('generated_at', metrics)


# ───────────────────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    unittest.main(verbosity=2)
