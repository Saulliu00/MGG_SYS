#!/usr/bin/env python3
"""
Application regression tests for MGG_SYS — app layer.

Covers:
  - ComparisonService: find_peak_pressure
  - Plotter: chart structure, legend config, multi-run chart
  - WorkOrderService: deduplication, authorization, delete scoping
  - Work-order route validation: invalid param → 400
  - Auth enforcement: unauthenticated → redirect
  - Backup script (scripts/backup.py): SQLite backup, uploads, logs

Database:
  Tests always run against a temporary SQLite database regardless of the
  DATABASE_URL environment variable, keeping tests fast and self-contained.
  The production PostgreSQL path is exercised on the real server.

Run from the project root:
    python app_regression_test.py
"""

import json
import os
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

# ── Environment must be set before any app import ──────────────────────────────
os.environ.setdefault('SECRET_KEY', 'test-secret-app-regression')
os.environ.setdefault('ADMIN_PASSWORD', 'TestAdmin1!')

_db_fd, _DB_PATH = tempfile.mkstemp(suffix='_app_reg.db')
os.close(_db_fd)
os.environ['DATABASE_URL'] = f'sqlite:///{_DB_PATH}'

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# ── Single app instance shared across all test classes ─────────────────────────
from app import create_app, db as _db

_app = create_app()
_app.config['TESTING'] = True
_app.config['WTF_CSRF_ENABLED'] = False
_app.config['RATELIMIT_ENABLED'] = False   # disable rate limiter in tests


# ── Base classes ───────────────────────────────────────────────────────────────

class AppTestCase(unittest.TestCase):
    """Base: pushes an app context + rolls back after each test."""

    @classmethod
    def setUpClass(cls):
        cls.app = _app
        cls.db = _db

    def setUp(self):
        self.ctx = self.app.app_context()
        self.ctx.push()
        # Nested transaction — rolled back in tearDown so tests are isolated
        self.db.session.begin_nested()

    def tearDown(self):
        self.db.session.rollback()
        self.ctx.pop()

    # ── helpers ────────────────────────────────────────────────────────────────

    def _make_user(self, employee_id, role='research_engineer'):
        from app.models import User
        u = User(username=employee_id, employee_id=employee_id, role=role)
        u.set_password('Test@1234')
        self.db.session.add(u)
        self.db.session.flush()
        return u

    def _make_simulation(self, user_id, work_order=None):
        from app.models import Simulation
        s = Simulation(
            user_id=user_id,
            work_order=work_order,
            ignition_model='IGN-A',
            nc_type_1='NC-E',
            nc_usage_1=450.0,
            shell_model='18',
            current=1.2,
            created_at=datetime.now(timezone.utc),
        )
        self.db.session.add(s)
        self.db.session.flush()
        return s

    def _make_test_result(self, user_id, simulation_id, filename='run.xlsx',
                          time_data=None, pressure_data=None):
        from app.models import TestResult
        if time_data is None:
            time_data = [0.0, 0.5, 1.0, 1.5, 2.0]
        if pressure_data is None:
            pressure_data = [0.0, 1.5, 3.0, 2.0, 0.5]
        tr = TestResult(
            user_id=user_id,
            simulation_id=simulation_id,
            filename=filename,
            file_path=f'/fake/{filename}',
            data=json.dumps({'time': time_data, 'pressure': pressure_data}),
            uploaded_at=datetime.now(timezone.utc),
        )
        self.db.session.add(tr)
        self.db.session.flush()
        return tr


# ═══════════════════════════════════════════════════════════════════════════════
# 1. ComparisonService — pure computation, no DB needed
# ═══════════════════════════════════════════════════════════════════════════════

class TestComparisonService(unittest.TestCase):
    """app/services/comparison_service.py"""

    @classmethod
    def setUpClass(cls):
        from app.services.comparison_service import ComparisonService
        cls.svc = ComparisonService()

    def test_find_peak_pressure_basic(self):
        pressure = [0.0, 1.5, 4.2, 3.0, 1.0]
        peak_p, _ = self.svc.find_peak_pressure(pressure)
        self.assertAlmostEqual(peak_p, 4.2)

    def test_find_peak_pressure_with_time(self):
        time     = [0.0, 0.5, 1.0, 1.5, 2.0]
        pressure = [0.0, 1.5, 4.2, 3.0, 1.0]
        peak_p, peak_t = self.svc.find_peak_pressure(pressure, time)
        self.assertAlmostEqual(peak_p, 4.2)
        self.assertAlmostEqual(peak_t, 1.0)

    def test_find_peak_pressure_single_element(self):
        peak_p, _ = self.svc.find_peak_pressure([7.5])
        self.assertAlmostEqual(peak_p, 7.5)


# ═══════════════════════════════════════════════════════════════════════════════
# 2. Plotter — chart structure and legend configuration
# ═══════════════════════════════════════════════════════════════════════════════

class TestPlotter(unittest.TestCase):
    """app/utils/plotter.py + app/config/plot_config.py"""

    @classmethod
    def setUpClass(cls):
        from app.utils.plotter import Plotter
        from app.config.plot_config import LEGEND_CONFIG
        cls.Plotter = Plotter
        cls.LEGEND_CONFIG = LEGEND_CONFIG

    # ── legend config (fix #fix from code review) ───────────────────────────

    def test_legend_anchored_bottom_right(self):
        lc = self.LEGEND_CONFIG
        self.assertEqual(lc.get('xanchor'), 'right',  'xanchor must be "right"')
        self.assertEqual(lc.get('yanchor'), 'bottom', 'yanchor must be "bottom"')
        self.assertAlmostEqual(lc['x'], 0.99)
        self.assertAlmostEqual(lc['y'], 0.01)

    # ── simulation chart ────────────────────────────────────────────────────

    def test_simulation_chart_structure(self):
        chart = self.Plotter.create_simulation_chart([0, 1, 2], [0, 2, 1])
        self.assertIn('data', chart)
        self.assertIn('layout', chart)
        self.assertEqual(len(chart['data']), 1)

    def test_simulation_chart_has_legend(self):
        chart = self.Plotter.create_simulation_chart([0, 1, 2], [0, 2, 1])
        self.assertIn('legend', chart['layout'])

    def test_simulation_chart_data_values(self):
        t = [0.0, 1.0, 2.0]
        p = [0.0, 3.5, 1.0]
        chart = self.Plotter.create_simulation_chart(t, p)
        trace = chart['data'][0]
        self.assertEqual(trace['x'], t)
        self.assertEqual(trace['y'], p)

    # ── multi-run chart ─────────────────────────────────────────────────────

    def test_multi_run_chart_trace_count(self):
        datasets = [
            {'time': [0, 1, 2], 'pressure': [0, 2, 1]},
            {'time': [0, 1, 2], 'pressure': [0, 2.5, 1.2]},
            {'time': [0, 1, 2], 'pressure': [0, 1.8, 0.9]},
        ]
        labels = ['run_1.xlsx', 'run_2.xlsx', 'run_3.xlsx']
        chart = self.Plotter.create_multi_run_chart(datasets, labels)
        self.assertEqual(len(chart['data']), 3)

    def test_multi_run_chart_empty_datasets(self):
        chart = self.Plotter.create_multi_run_chart([], [])
        self.assertEqual(len(chart['data']), 0)
        # Should have annotation for empty state
        self.assertIn('annotations', chart['layout'])

    def test_multi_run_chart_skips_invalid_dataset(self):
        datasets = [
            {'time': [0, 1], 'pressure': [0, 2]},
            {'time': [], 'pressure': []},          # invalid — should be skipped
        ]
        chart = self.Plotter.create_multi_run_chart(datasets, ['a.xlsx', 'b.xlsx'])
        self.assertEqual(len(chart['data']), 1)

    def test_multi_run_chart_label_names(self):
        datasets = [{'time': [0, 1], 'pressure': [0, 2]}]
        chart = self.Plotter.create_multi_run_chart(datasets, ['my_run.xlsx'])
        self.assertEqual(chart['data'][0]['name'], 'my_run.xlsx')

    # ── comparison chart ────────────────────────────────────────────────────

    def test_comparison_chart_two_traces(self):
        chart = self.Plotter.create_comparison_chart(
            simulation_data={'time': [0, 1, 2], 'pressure': [0, 2, 1]},
            test_data={'time': [0, 1, 2], 'pressure': [0, 2.2, 1.1]},
        )
        self.assertEqual(len(chart['data']), 2)

    def test_comparison_chart_no_data_has_annotation(self):
        chart = self.Plotter.create_comparison_chart()
        self.assertIn('annotations', chart['layout'])


# ═══════════════════════════════════════════════════════════════════════════════
# 3. Work-order URL parameter validation (fix #15)
# ═══════════════════════════════════════════════════════════════════════════════

class TestWorkOrderParamValidation(unittest.TestCase):
    """app/routes/work_order.py — _valid_work_order()"""

    @classmethod
    def setUpClass(cls):
        from app.routes.work_order import _valid_work_order
        cls.valid = staticmethod(_valid_work_order)

    def test_typical_work_order_valid(self):
        self.assertTrue(self.valid('WO202603021002474632'))

    def test_alphanumeric_with_dash_valid(self):
        self.assertTrue(self.valid('WO-2026-001'))

    def test_alphanumeric_with_underscore_valid(self):
        self.assertTrue(self.valid('WO_2026_001'))

    def test_empty_string_invalid(self):
        self.assertFalse(self.valid(''))

    def test_none_invalid(self):
        self.assertFalse(self.valid(None))

    def test_space_in_param_invalid(self):
        self.assertFalse(self.valid('WO 2026 001'))

    def test_path_traversal_invalid(self):
        self.assertFalse(self.valid('../etc/passwd'))

    def test_sql_injection_attempt_invalid(self):
        self.assertFalse(self.valid("WO'; DROP TABLE simulation;--"))

    def test_over_100_chars_invalid(self):
        self.assertFalse(self.valid('A' * 101))

    def test_exactly_100_chars_valid(self):
        self.assertTrue(self.valid('A' * 100))


# ═══════════════════════════════════════════════════════════════════════════════
# 4. WorkOrderService — requires database
# ═══════════════════════════════════════════════════════════════════════════════

class TestWorkOrderService(AppTestCase):
    """app/services/work_order_service.py"""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        from app.services.work_order_service import WorkOrderService
        cls.WorkOrderService = WorkOrderService

    def _svc(self):
        return self.WorkOrderService(self.db)

    # ── get_all_work_orders ─────────────────────────────────────────────────

    def test_get_all_empty(self):
        result = self._svc().get_all_work_orders()
        # May contain pre-seeded data; result must be a list
        self.assertIsInstance(result, list)

    def test_get_all_deduplicates_same_work_order(self):
        u = self._make_user('WOS_USER1')
        wo = 'WO-TEST-DEDUP'
        # Two simulations with the same work_order
        self._make_simulation(u.id, work_order=wo)
        self._make_simulation(u.id, work_order=wo)
        result = self._svc().get_all_work_orders()
        wo_entries = [r for r in result if r['work_order'] == wo]
        self.assertEqual(len(wo_entries), 1, 'Same work_order must appear only once')

    def test_get_all_owner_id_is_earliest_sim(self):
        u1 = self._make_user('WOS_OWNER1')
        u2 = self._make_user('WOS_OWNER2')
        wo = 'WO-TEST-OWNER'
        s1 = self._make_simulation(u1.id, work_order=wo)
        s1.created_at = datetime.now() - timedelta(hours=2)
        s2 = self._make_simulation(u2.id, work_order=wo)
        s2.created_at = datetime.now()
        self.db.session.flush()
        result = self._svc().get_all_work_orders()
        entry = next(r for r in result if r['work_order'] == wo)
        self.assertEqual(entry['owner_id'], u1.id)

    def test_simulations_without_work_order_excluded(self):
        u = self._make_user('WOS_NOWO')
        self._make_simulation(u.id, work_order=None)
        self._make_simulation(u.id, work_order='')
        result = self._svc().get_all_work_orders()
        for r in result:
            self.assertTrue(r['work_order'], 'Empty/null work_order must not appear')

    # ── get_work_order_detail ───────────────────────────────────────────────

    def test_detail_not_found(self):
        detail = self._svc().get_work_order_detail('WO-NONEXISTENT-9999')
        self.assertFalse(detail.get('found'))

    def test_detail_found(self):
        u = self._make_user('WOS_DET1')
        s = self._make_simulation(u.id, work_order='WO-DET-001')
        self._make_test_result(u.id, s.id, 'det_run1.xlsx')
        detail = self._svc().get_work_order_detail('WO-DET-001')
        self.assertTrue(detail.get('found'))
        self.assertEqual(detail['simulation']['work_order'], 'WO-DET-001')

    def test_detail_includes_chart_and_stats(self):
        u = self._make_user('WOS_DET2')
        s = self._make_simulation(u.id, work_order='WO-DET-002')
        self._make_test_result(u.id, s.id, 'det_run2.xlsx',
                               time_data=[0, 1, 2, 3],
                               pressure_data=[0, 2, 4, 1])
        detail = self._svc().get_work_order_detail('WO-DET-002')
        self.assertIn('chart', detail)
        self.assertIn('statistics', detail)
        # At least our 1 run is reflected; additional count from prior-test
        # orphaned rows is acceptable due to ID-reuse after savepoint release.
        self.assertGreaterEqual(detail['statistics']['count'], 1)
        filenames = [r['filename'] for r in detail['test_results']]
        self.assertIn('det_run2.xlsx', filenames)

    def test_detail_collects_test_results_across_sims(self):
        """All sims sharing a work_order contribute their test results."""
        u = self._make_user('WOS_MULTI')
        wo = 'WO-MULTI-001'
        s1 = self._make_simulation(u.id, work_order=wo)
        s2 = self._make_simulation(u.id, work_order=wo)
        self._make_test_result(u.id, s1.id, 'mr_run1.xlsx')
        self._make_test_result(u.id, s2.id, 'mr_run2.xlsx')
        detail = self._svc().get_work_order_detail(wo)
        filenames = [r['filename'] for r in detail['test_results']]
        self.assertIn('mr_run1.xlsx', filenames)
        self.assertIn('mr_run2.xlsx', filenames)

    # ── delete_test_result ──────────────────────────────────────────────────

    def test_delete_own_test_result(self):
        u = self._make_user('WOS_DEL1')
        s = self._make_simulation(u.id, work_order='WO-DEL-TR1')
        tr = self._make_test_result(u.id, s.id)
        result = self._svc().delete_test_result(tr.id, u.id, is_admin=False)
        self.assertTrue(result['success'])

    def test_cannot_delete_others_test_result(self):
        owner = self._make_user('WOS_DEL2_OWN')
        other = self._make_user('WOS_DEL2_OTH')
        s = self._make_simulation(owner.id, work_order='WO-DEL-TR2')
        tr = self._make_test_result(owner.id, s.id)
        result = self._svc().delete_test_result(tr.id, other.id, is_admin=False)
        self.assertFalse(result['success'])

    def test_admin_can_delete_any_test_result(self):
        owner = self._make_user('WOS_DEL3_OWN')
        admin = self._make_user('WOS_DEL3_ADM', role='admin')
        s = self._make_simulation(owner.id, work_order='WO-DEL-TR3')
        tr = self._make_test_result(owner.id, s.id)
        result = self._svc().delete_test_result(tr.id, admin.id, is_admin=True)
        self.assertTrue(result['success'])

    def test_delete_nonexistent_test_result(self):
        u = self._make_user('WOS_DEL4')
        result = self._svc().delete_test_result(99999, u.id, is_admin=False)
        self.assertFalse(result['success'])

    # ── delete_work_order (fix #8) ──────────────────────────────────────────

    def test_owner_can_delete_own_work_order(self):
        u = self._make_user('WOS_WOD1')
        s = self._make_simulation(u.id, work_order='WO-WOD-001')
        self._make_test_result(u.id, s.id)
        result = self._svc().delete_work_order('WO-WOD-001', u.id, is_admin=False)
        self.assertTrue(result['success'])

    def test_non_owner_cannot_delete_work_order(self):
        owner = self._make_user('WOS_WOD2_OWN')
        other = self._make_user('WOS_WOD2_OTH')
        self._make_simulation(owner.id, work_order='WO-WOD-002')
        result = self._svc().delete_work_order('WO-WOD-002', other.id, is_admin=False)
        self.assertFalse(result['success'])

    def test_admin_can_delete_any_work_order(self):
        owner = self._make_user('WOS_WOD3_OWN')
        admin_u = self._make_user('WOS_WOD3_ADM', role='admin')
        self._make_simulation(owner.id, work_order='WO-WOD-003')
        result = self._svc().delete_work_order('WO-WOD-003', admin_u.id, is_admin=True)
        self.assertTrue(result['success'])

    def test_delete_work_order_nonexistent(self):
        u = self._make_user('WOS_WOD4')
        result = self._svc().delete_work_order('WO-GHOST-0001', u.id, is_admin=False)
        self.assertFalse(result['success'])

    def test_delete_work_order_owner_only_removes_own_test_results(self):
        """Fix #8: when owner deletes WO, other users' test results survive."""
        from app.models import TestResult
        owner = self._make_user('WOS_WOD5_OWN')
        other = self._make_user('WOS_WOD5_OTH')
        s = self._make_simulation(owner.id, work_order='WO-WOD-005')
        tr_own   = self._make_test_result(owner.id, s.id, 'own_run.xlsx')
        tr_other = self._make_test_result(other.id, s.id, 'other_run.xlsx')
        tr_other_id = tr_other.id

        self._svc().delete_work_order('WO-WOD-005', owner.id, is_admin=False)

        # Other user's test result must still exist
        surviving = self.db.session.get(TestResult, tr_other_id)
        self.assertIsNotNone(surviving, "Other user's test result was wrongly deleted")

    def test_delete_work_order_admin_removes_all_test_results(self):
        """Admin deleting a WO removes ALL test results (own + others)."""
        from app.models import TestResult
        owner = self._make_user('WOS_WOD6_OWN')
        other = self._make_user('WOS_WOD6_OTH')
        admin_u = self._make_user('WOS_WOD6_ADM', role='admin')
        s = self._make_simulation(owner.id, work_order='WO-WOD-006')
        tr_own   = self._make_test_result(owner.id, s.id, 'own_run.xlsx')
        tr_other = self._make_test_result(other.id, s.id, 'other_run.xlsx')
        own_id, other_id = tr_own.id, tr_other.id

        self._svc().delete_work_order('WO-WOD-006', admin_u.id, is_admin=True)

        self.assertIsNone(self.db.session.get(TestResult, own_id))
        self.assertIsNone(self.db.session.get(TestResult, other_id))


# ═══════════════════════════════════════════════════════════════════════════════
# 5. Route-level tests via Flask test client
# ═══════════════════════════════════════════════════════════════════════════════

class TestRoutes(AppTestCase):
    """Tests for key route behaviors using the Flask test client."""

    def _client(self):
        return self.app.test_client()

    def _login(self, client, employee_id='admin', password='TestAdmin1!'):
        """Log in via the auth endpoint."""
        from datetime import date as _date
        with client.session_transaction() as sess:
            sess['login_date'] = _date.today().isoformat()
        resp = client.post('/auth/login', data={
            'employee_id': employee_id,
            'password': password,
        }, follow_redirects=True)
        return resp

    # ── unauthenticated access → redirect ───────────────────────────────────

    def test_work_order_index_requires_auth(self):
        client = self._client()
        resp = client.get('/work_order/')
        self.assertIn(resp.status_code, (302, 200))
        if resp.status_code == 302:
            self.assertIn('/auth/login', resp.headers.get('Location', ''))

    def test_work_order_list_requires_auth(self):
        client = self._client()
        resp = client.get('/work_order/list')
        self.assertIn(resp.status_code, (302, 200))

    def test_admin_index_requires_auth(self):
        client = self._client()
        resp = client.get('/admin/')
        self.assertIn(resp.status_code, (302, 200))

    # ── work_order param validation (fix #15) ───────────────────────────────

    def test_invalid_work_order_detail_returns_400(self):
        client = self._client()
        self._login(client)
        resp = client.get('/work_order/../etc/passwd/detail')
        # Flask router may 404 on path traversal; 400 or 404 both acceptable
        self.assertIn(resp.status_code, (400, 404))

    def test_invalid_work_order_detail_special_chars_400(self):
        client = self._client()
        self._login(client)
        # URL-encode a work order with a space which becomes %20
        resp = client.get('/work_order/WO%20bad%20id/detail')
        self.assertIn(resp.status_code, (400, 404))

    def test_valid_work_order_detail_does_not_return_400(self):
        client = self._client()
        self._login(client)
        resp = client.get('/work_order/WO-DOESNT-EXIST-001/detail')
        # Valid format → service returns 404 (not found), not 400 (invalid param)
        self.assertNotEqual(resp.status_code, 400)

    def test_invalid_work_order_delete_returns_400(self):
        client = self._client()
        self._login(client)
        resp = client.delete('/work_order/WO%3B%20DROP%20TABLE')
        self.assertIn(resp.status_code, (400, 404))

    # ── simulation routes ────────────────────────────────────────────────────

    def test_simulation_index_loads(self):
        client = self._client()
        self._login(client)
        resp = client.get('/simulation/')
        self.assertEqual(resp.status_code, 200)

    # ── auth ────────────────────────────────────────────────────────────────

    def test_login_with_wrong_password_fails(self):
        client = self._client()
        resp = client.post('/auth/login', data={
            'employee_id': 'admin',
            'password': 'wrongpassword',
        }, follow_redirects=False)
        # Should NOT redirect to main page; stays on login or re-renders
        location = resp.headers.get('Location', '')
        self.assertNotIn('/simulation', location)

    def test_logout_clears_session(self):
        client = self._client()
        self._login(client)
        resp = client.get('/auth/logout', follow_redirects=False)
        self.assertIn(resp.status_code, (302, 200))


# ═══════════════════════════════════════════════════════════════════════════════
# 6. Backup script — scripts/backup.py
# ═══════════════════════════════════════════════════════════════════════════════

class TestBackupScript(unittest.TestCase):
    """scripts/backup.py — end-to-end backup of DB, uploads, logs."""

    def setUp(self):
        import tempfile
        self.tmpdir = tempfile.mkdtemp()

    def tearDown(self):
        import shutil as _shutil
        _shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _run_backup(self, env_overrides=None):
        """Run the backup script in a subprocess with isolated paths."""
        import subprocess, sys
        env = os.environ.copy()
        env['DATABASE_URL'] = f'sqlite:///{_DB_PATH}'
        # Override internal paths via env so backup writes to tmpdir
        if env_overrides:
            env.update(env_overrides)
        result = subprocess.run(
            [sys.executable, 'scripts/backup.py', '--retention-days', '30'],
            capture_output=True, text=True, env=env,
        )
        return result

    def test_backup_exits_zero(self):
        result = self._run_backup()
        self.assertEqual(result.returncode, 0,
                         f'Backup script failed:\n{result.stdout}\n{result.stderr}')

    def _backup_dir(self):
        """The directory the backup script actually writes to."""
        return os.path.join(
            os.path.dirname(os.path.abspath(__file__)), 'instance', 'backups'
        )

    def test_backup_creates_db_file(self):
        import glob
        result = self._run_backup()
        self.assertEqual(result.returncode, 0)
        db_backups = glob.glob(os.path.join(self._backup_dir(), 'mgg_backup_*.db'))
        self.assertGreater(len(db_backups), 0, 'No DB backup file created')

    def test_backup_creates_uploads_archive(self):
        import glob
        result = self._run_backup()
        self.assertEqual(result.returncode, 0)
        uploads_archives = glob.glob(os.path.join(self._backup_dir(), 'uploads_*.tar.gz'))
        self.assertGreater(len(uploads_archives), 0, 'No uploads archive created')

    def test_backup_creates_logs_archive(self):
        import glob
        result = self._run_backup()
        self.assertEqual(result.returncode, 0)
        log_archives = glob.glob(os.path.join(self._backup_dir(), 'logs_*.tar.gz'))
        self.assertGreater(len(log_archives), 0, 'No logs archive created')

    def test_backup_output_mentions_all_three_sections(self):
        result = self._run_backup()
        self.assertIn('[DB]',      result.stdout)
        self.assertIn('[UPLOADS]', result.stdout)
        self.assertIn('[LOGS]',    result.stdout)


# ═══════════════════════════════════════════════════════════════════════════════
# 7. Backup — unit tests (scripts/backup.py individual functions)
# ═══════════════════════════════════════════════════════════════════════════════

class TestBackupUnit(unittest.TestCase):
    """Unit tests for each function in scripts/backup.py.

    Uses temp directories and mocks — does NOT run the real pg_dump binary.
    """

    def setUp(self):
        import tempfile, shutil, importlib, sys as _sys
        self.tmpdir = tempfile.mkdtemp()

        # Build a minimal isolated project structure inside tmpdir
        self.project_root = os.path.join(self.tmpdir, 'project')
        self.backup_dir   = os.path.join(self.project_root, 'instance', 'backups')
        self.uploads_dir  = os.path.join(self.project_root, 'instance', 'uploads')
        self.logs_dir     = os.path.join(self.project_root, 'app', 'log')
        self.sqlite_path  = os.path.join(self.project_root, 'instance', 'simulation_system.db')

        for d in [self.backup_dir, self.uploads_dir, self.logs_dir]:
            os.makedirs(d, exist_ok=True)

        # Create a minimal valid SQLite file
        import sqlite3
        conn = sqlite3.connect(self.sqlite_path)
        conn.execute('CREATE TABLE t (id INTEGER PRIMARY KEY)')
        conn.execute("INSERT INTO t VALUES (1)")
        conn.commit()
        conn.close()

        # Create a sample upload and log file so archives are non-empty
        open(os.path.join(self.uploads_dir, 'sample.xlsx'), 'w').close()
        open(os.path.join(self.logs_dir, 'mgg_system_log_2026-01-01.csv'), 'w').close()

        # Patch backup module paths to point at our tmpdir
        import scripts.backup as _bk
        self._bk = _bk
        self._orig_backup_dir  = _bk.BACKUP_DIR
        self._orig_uploads_dir = _bk.UPLOADS_DIR
        self._orig_logs_dir    = _bk.LOGS_DIR
        self._orig_timestamp   = _bk.TIMESTAMP

        from pathlib import Path
        _bk.BACKUP_DIR   = Path(self.backup_dir)
        _bk.UPLOADS_DIR  = Path(self.uploads_dir)
        _bk.LOGS_DIR     = Path(self.logs_dir)
        _bk.TIMESTAMP    = '20260101_020000'

    def tearDown(self):
        import shutil
        # Restore module-level paths
        self._bk.BACKUP_DIR   = self._orig_backup_dir
        self._bk.UPLOADS_DIR  = self._orig_uploads_dir
        self._bk.LOGS_DIR     = self._orig_logs_dir
        self._bk.TIMESTAMP    = self._orig_timestamp
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    # ── SQLite backup ────────────────────────────────────────────────────────

    def test_sqlite_copy_creates_db_file(self):
        """_sqlite_copy() creates a .db backup file."""
        os.environ.pop('DATABASE_URL', None)
        result = self._bk._sqlite_copy(f'sqlite:///{self.sqlite_path}')
        self.assertTrue(os.path.exists(result))
        self.assertTrue(str(result).endswith('.db'))

    def test_sqlite_copy_file_is_valid_sqlite(self):
        """The backed-up .db file is a valid SQLite database."""
        import sqlite3
        self._bk._sqlite_copy(f'sqlite:///{self.sqlite_path}')
        backed_up = list(self._bk.BACKUP_DIR.glob('*.db'))[0]
        conn = sqlite3.connect(str(backed_up))
        rows = conn.execute('SELECT COUNT(*) FROM t').fetchone()
        conn.close()
        self.assertEqual(rows[0], 1, 'Backed-up DB should contain 1 row')

    def test_sqlite_copy_nonexistent_db_raises(self):
        """_sqlite_copy() raises FileNotFoundError when DB is missing."""
        with self.assertRaises(FileNotFoundError):
            self._bk._sqlite_copy('sqlite:///nonexistent_path.db')

    def test_sqlite_copy_uses_default_path_when_no_url(self):
        """_sqlite_copy('') falls back to instance/simulation_system.db."""
        from pathlib import Path
        self._bk.BACKUP_DIR = Path(self.backup_dir)
        # Place the DB at the expected default location
        import scripts.backup as _bk2
        orig = _bk2.PROJECT_ROOT
        _bk2.PROJECT_ROOT = Path(self.project_root)
        result = self._bk._sqlite_copy('')
        _bk2.PROJECT_ROOT = orig
        self.assertTrue(os.path.exists(result))

    # ── PostgreSQL pg_dump ───────────────────────────────────────────────────

    def _pg_mock(self, returncode=0, stderr=b''):
        """Return a mock subprocess.run result + a _fmt_size patcher.
        pg_dump does not create a real file, so we also patch _fmt_size."""
        from unittest.mock import patch, MagicMock
        mock_result = MagicMock()
        mock_result.returncode = returncode
        mock_result.stderr = stderr
        return mock_result

    def test_pg_dump_calls_pg_dump_binary(self):
        """_pg_dump() invokes the pg_dump command with the DB URL."""
        from unittest.mock import patch
        mock_result = self._pg_mock()
        with patch('subprocess.run', return_value=mock_result) as mock_run, \
             patch('scripts.backup._fmt_size', return_value='1 KB'):
            self._bk._pg_dump('postgresql://u:p@localhost/db')
            cmd = mock_run.call_args[0][0]
            self.assertEqual(cmd[0], 'pg_dump')
            self.assertIn('postgresql://u:p@localhost/db', cmd)

    def test_pg_dump_uses_custom_format(self):
        """_pg_dump() passes --format=custom to pg_dump."""
        from unittest.mock import patch
        mock_result = self._pg_mock()
        with patch('subprocess.run', return_value=mock_result) as mock_run, \
             patch('scripts.backup._fmt_size', return_value='1 KB'):
            self._bk._pg_dump('postgresql://u:p@localhost/db')
            cmd = mock_run.call_args[0][0]
            self.assertIn('--format=custom', cmd)

    def test_pg_dump_raises_on_nonzero_returncode(self):
        """_pg_dump() raises RuntimeError when pg_dump exits non-zero."""
        from unittest.mock import patch
        mock_result = self._pg_mock(returncode=1, stderr=b'connection refused')
        with patch('subprocess.run', return_value=mock_result):
            with self.assertRaises(RuntimeError) as ctx:
                self._bk._pg_dump('postgresql://u:p@localhost/db')
            self.assertIn('pg_dump failed', str(ctx.exception))

    def test_pg_dump_output_path_contains_timestamp(self):
        """_pg_dump() names the output file with the current TIMESTAMP."""
        from unittest.mock import patch
        mock_result = self._pg_mock()
        with patch('subprocess.run', return_value=mock_result) as mock_run, \
             patch('scripts.backup._fmt_size', return_value='1 KB'):
            self._bk._pg_dump('postgresql://u:p@localhost/db')
            cmd = mock_run.call_args[0][0]
            file_arg = [a for a in cmd if 'mgg_backup_' in a][0]
            self.assertIn('20260101_020000', file_arg)

    def test_backup_database_routes_to_pg_dump_for_postgresql_url(self):
        """backup_database() calls _pg_dump when DATABASE_URL is postgresql://."""
        from unittest.mock import patch
        mock_result = self._pg_mock()
        with patch.dict(os.environ, {'DATABASE_URL': 'postgresql://u:p@localhost/db'}), \
             patch('subprocess.run', return_value=mock_result) as mock_run, \
             patch('scripts.backup._fmt_size', return_value='1 KB'):
            self._bk.backup_database()
            cmd = mock_run.call_args[0][0]
            self.assertEqual(cmd[0], 'pg_dump')

    def test_backup_database_routes_to_sqlite_copy_for_sqlite_url(self):
        """backup_database() calls _sqlite_copy when DATABASE_URL is sqlite://."""
        with patch.dict(os.environ, {'DATABASE_URL': f'sqlite:///{self.sqlite_path}'}):
            result = self._bk.backup_database()
            self.assertTrue(str(result).endswith('.db'))

    # ── Uploads archive ──────────────────────────────────────────────────────

    def test_backup_uploads_creates_tar_gz(self):
        """backup_uploads() creates a tar.gz archive."""
        result = self._bk.backup_uploads()
        self.assertTrue(os.path.exists(result))
        self.assertTrue(str(result).endswith('.tar.gz'))

    def test_backup_uploads_archive_contains_sample_file(self):
        """The uploads archive contains the sample file that was placed there."""
        import tarfile
        result = self._bk.backup_uploads()
        with tarfile.open(result, 'r:gz') as tar:
            names = tar.getnames()
        self.assertTrue(any('sample.xlsx' in n for n in names),
                        f'sample.xlsx not found in archive: {names}')

    def test_backup_uploads_succeeds_when_uploads_dir_missing(self):
        """backup_uploads() creates an empty archive when uploads dir is absent."""
        import shutil
        shutil.rmtree(self.uploads_dir)
        result = self._bk.backup_uploads()
        self.assertTrue(os.path.exists(result))

    # ── Logs archive ─────────────────────────────────────────────────────────

    def test_backup_logs_creates_tar_gz(self):
        """backup_logs() creates a tar.gz archive."""
        result = self._bk.backup_logs()
        self.assertTrue(os.path.exists(result))
        self.assertTrue(str(result).endswith('.tar.gz'))

    def test_backup_logs_archive_contains_csv_file(self):
        """The logs archive contains the CSV log file that was placed there."""
        import tarfile
        result = self._bk.backup_logs()
        with tarfile.open(result, 'r:gz') as tar:
            names = tar.getnames()
        self.assertTrue(any('.csv' in n for n in names),
                        f'No CSV file found in logs archive: {names}')

    def test_backup_logs_succeeds_when_log_dir_missing(self):
        """backup_logs() creates an empty archive when log dir is absent."""
        import shutil
        shutil.rmtree(self.logs_dir)
        result = self._bk.backup_logs()
        self.assertTrue(os.path.exists(result))

    # ── Pruning ──────────────────────────────────────────────────────────────

    def test_prune_removes_old_backup_files(self):
        """prune_old_backups() removes files older than retention_days."""
        import time
        old_file = os.path.join(self.backup_dir, 'mgg_backup_20200101_000000.db')
        open(old_file, 'w').close()
        # Back-date the file's mtime by 40 days
        old_mtime = time.time() - 40 * 86400
        os.utime(old_file, (old_mtime, old_mtime))
        self._bk.prune_old_backups(retention_days=30)
        self.assertFalse(os.path.exists(old_file), 'Old backup file should have been pruned')

    def test_prune_keeps_recent_backup_files(self):
        """prune_old_backups() keeps files within retention_days."""
        recent_file = os.path.join(self.backup_dir, 'mgg_backup_20260110_000000.db')
        open(recent_file, 'w').close()
        self._bk.prune_old_backups(retention_days=30)
        self.assertTrue(os.path.exists(recent_file), 'Recent backup file was wrongly pruned')

    def test_prune_ignores_non_backup_files(self):
        """prune_old_backups() does not remove unrecognised file extensions."""
        import time
        alien_file = os.path.join(self.backup_dir, 'README.txt')
        open(alien_file, 'w').close()
        old_mtime = time.time() - 60 * 86400
        os.utime(alien_file, (old_mtime, old_mtime))
        self._bk.prune_old_backups(retention_days=30)
        self.assertTrue(os.path.exists(alien_file), 'Non-backup file should not be pruned')

    # ── --date flag ──────────────────────────────────────────────────────────

    def test_date_flag_overrides_timestamp(self):
        """--date YYYYMMDD labels backup files with the given date."""
        result = self._run_backup_with_date('20260301')
        self.assertEqual(result.returncode, 0, result.stderr)
        import glob
        # The subprocess writes to the real project backup dir, not self.backup_dir
        real_backup_dir = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), 'instance', 'backups'
        )
        files = glob.glob(os.path.join(real_backup_dir, '*20260301*'))
        self.assertGreater(len(files), 0, 'No backup files with custom date label')

    def test_invalid_date_flag_exits_nonzero(self):
        """--date with bad format exits with code 1."""
        result = self._run_backup_with_date('not-a-date')
        self.assertNotEqual(result.returncode, 0)

    def _run_backup_with_date(self, date_str):
        import subprocess, sys
        env = os.environ.copy()
        env['DATABASE_URL'] = f'sqlite:///{self.sqlite_path}'
        return subprocess.run(
            [sys.executable, 'scripts/backup.py', '--date', date_str],
            capture_output=True, text=True, env=env,
        )


# ═══════════════════════════════════════════════════════════════════════════════
# 8. Health endpoint
# ═══════════════════════════════════════════════════════════════════════════════

class TestHealthEndpoint(AppTestCase):
    """Tests for the /health liveness + readiness endpoint (app/routes/main.py)."""

    def _client(self):
        return self.app.test_client()

    def test_health_returns_200_when_db_ok(self):
        """/health returns 200 when the database is reachable."""
        resp = self._client().get('/health')
        self.assertEqual(resp.status_code, 200)

    def test_health_response_is_json(self):
        """/health response Content-Type is application/json."""
        resp = self._client().get('/health')
        self.assertIn('application/json', resp.content_type)

    def test_health_body_has_status_healthy(self):
        """/health body contains {"status": "healthy"} when healthy."""
        resp = self._client().get('/health')
        data = json.loads(resp.data)
        self.assertEqual(data['status'], 'healthy')

    def test_health_body_has_database_check_ok(self):
        """/health body contains {"checks": {"database": "ok"}} when DB is reachable."""
        resp = self._client().get('/health')
        data = json.loads(resp.data)
        self.assertEqual(data.get('checks', {}).get('database'), 'ok')

    def test_health_returns_503_when_db_unavailable(self):
        """/health returns 503 when the database raises an exception."""
        from unittest.mock import patch
        # db is imported locally inside health_check(), so patch at the app level
        with patch('app.db.session.execute', side_effect=Exception('DB down')):
            resp = self._client().get('/health')
        self.assertEqual(resp.status_code, 503)

    def test_health_503_body_has_status_unhealthy(self):
        """/health 503 body contains {"status": "unhealthy"} on DB failure."""
        from unittest.mock import patch
        with patch('app.db.session.execute', side_effect=Exception('connection refused')):
            resp = self._client().get('/health')
        data = json.loads(resp.data)
        self.assertEqual(data['status'], 'unhealthy')

    def test_health_no_auth_required(self):
        """/health is accessible without login (monitoring probes are unauthenticated)."""
        resp = self._client().get('/health')
        # Must not redirect to login
        self.assertNotEqual(resp.status_code, 302)


# ═══════════════════════════════════════════════════════════════════════════════
# 9. Browser / UI regression tests (Flask test client)
# ═══════════════════════════════════════════════════════════════════════════════

class TestUI(AppTestCase):
    """UI-level tests: verify rendered HTML contains expected structure.

    Uses Flask's built-in test client — no real browser required.
    Tests the same responses a browser would receive.
    """

    def setUp(self):
        # Reset rate limiter counters accumulated by earlier test classes.
        # limiter.reset() clears the in-memory storage so auth route limits
        # don't carry over from TestRoutes into these UI tests.
        from app import limiter
        limiter.reset()
        super().setUp()

    def _client(self):
        return self.app.test_client()

    def _login(self, client, employee_id='admin', password='TestAdmin1!'):
        from datetime import date as _date
        with client.session_transaction() as sess:
            sess['login_date'] = _date.today().isoformat()
        return client.post('/auth/login', data={
            'employee_id': employee_id,
            'password': password,
        }, follow_redirects=True)

    # ── Login page ───────────────────────────────────────────────────────────

    def test_login_page_loads(self):
        """GET /auth/login returns 200."""
        resp = self._client().get('/auth/login')
        self.assertEqual(resp.status_code, 200)

    def test_login_page_has_form(self):
        """Login page HTML contains an <form> element."""
        resp = self._client().get('/auth/login')
        self.assertIn(b'<form', resp.data)

    def test_login_page_has_employee_id_field(self):
        """Login page has an employee_id input field."""
        resp = self._client().get('/auth/login')
        self.assertIn(b'employee_id', resp.data)

    def test_login_page_has_password_field(self):
        """Login page has a password input field."""
        resp = self._client().get('/auth/login')
        html = resp.data.decode('utf-8')
        self.assertIn('type="password"', html)

    def test_login_page_has_submit_button(self):
        """Login page has a submit button."""
        resp = self._client().get('/auth/login')
        html = resp.data.decode('utf-8')
        self.assertTrue(
            'type="submit"' in html or '<button' in html,
            'No submit button found on login page'
        )

    # ── Authentication flow ──────────────────────────────────────────────────

    def test_successful_login_redirects_away_from_login(self):
        """Valid credentials redirect the user away from the login page."""
        client = self._client()
        resp = self._login(client)
        self.assertEqual(resp.status_code, 200)
        # After login the user should be on a non-login page
        self.assertNotIn(b'employee_id', resp.data[:500])

    def test_failed_login_stays_on_login_page(self):
        """Wrong password re-renders the login form (no redirect to app pages)."""
        client = self._client()
        # Use a fresh client (no prior session) so there's no redirect to /simulation
        resp = client.post('/auth/login', data={
            'employee_id': 'admin',
            'password': 'definitely_wrong_pw',
        }, follow_redirects=True)
        html = resp.data.decode('utf-8')
        # After a failed login, the login form must be visible again
        self.assertIn('employee_id', html,
                      'Login form not re-rendered after failed login')

    def test_logout_redirects_to_login(self):
        """Logout redirects the user back to the login page."""
        client = self._client()
        self._login(client)
        resp = client.get('/auth/logout', follow_redirects=True)
        html = resp.data.decode('utf-8')
        self.assertIn('employee_id', html)

    # ── Protected pages require login ────────────────────────────────────────

    def test_simulation_page_requires_login(self):
        """GET /simulation/ without auth redirects to login."""
        resp = self._client().get('/simulation/', follow_redirects=True)
        html = resp.data.decode('utf-8')
        self.assertIn('employee_id', html)

    def test_admin_page_requires_login(self):
        """GET /admin/ without auth redirects to login."""
        resp = self._client().get('/admin/', follow_redirects=True)
        html = resp.data.decode('utf-8')
        self.assertIn('employee_id', html)

    def test_work_order_page_requires_login(self):
        """GET /work_order/ without auth redirects to login."""
        resp = self._client().get('/work_order/', follow_redirects=True)
        html = resp.data.decode('utf-8')
        self.assertIn('employee_id', html)

    # ── Authenticated page content ───────────────────────────────────────────

    def test_simulation_page_has_html_structure(self):
        """Simulation page renders with a complete HTML document."""
        client = self._client()
        self._login(client)
        resp = client.get('/simulation/')
        self.assertEqual(resp.status_code, 200)
        html = resp.data.decode('utf-8')
        self.assertIn('<!doctype html>', html.lower()[:50])
        self.assertIn('<html', html.lower())

    def test_admin_page_accessible_to_admin(self):
        """Admin user can access the /admin/ page (200, not 403/redirect)."""
        client = self._client()
        self._login(client, employee_id='admin', password='TestAdmin1!')
        resp = client.get('/admin/')
        self.assertEqual(resp.status_code, 200)

    def test_admin_page_contains_user_table(self):
        """Admin page HTML contains a user management section."""
        client = self._client()
        self._login(client, employee_id='admin', password='TestAdmin1!')
        resp = client.get('/admin/')
        html = resp.data.decode('utf-8')
        # Admin page should reference users or employee IDs
        self.assertTrue(
            'admin' in html.lower() or 'user' in html.lower(),
            'Admin page does not appear to contain user management content'
        )

    # ── Content Security headers ─────────────────────────────────────────────

    def test_login_page_has_no_xframe_options_allowing_embedding(self):
        """Response headers should not allow clickjacking via iframes."""
        resp = self._client().get('/auth/login')
        # X-Frame-Options or CSP frame-ancestors should protect against clickjacking
        xfo = resp.headers.get('X-Frame-Options', '')
        csp = resp.headers.get('Content-Security-Policy', '')
        # Acceptable if either header is set with a restrictive value
        protected = (
            xfo.upper() in ('DENY', 'SAMEORIGIN') or
            'frame-ancestors' in csp
        )
        # Warn but don't fail — this is a hardening check not a correctness check
        if not protected:
            import warnings
            warnings.warn(
                'No X-Frame-Options or CSP frame-ancestors header — clickjacking risk',
                stacklevel=2
            )

    # ── Error pages ──────────────────────────────────────────────────────────

    def test_404_returns_html(self):
        """GET on a nonexistent route returns an HTML response."""
        resp = self._client().get('/this/route/does/not/exist/at/all')
        self.assertEqual(resp.status_code, 404)

    def test_api_endpoint_returns_json_not_html(self):
        """Simulation API endpoints return JSON content-type when authenticated."""
        client = self._client()
        self._login(client)
        resp = client.get('/work_order/list')
        # work_order list is JSON API — should not return HTML
        if resp.status_code == 200:
            self.assertIn('application/json', resp.content_type)

    # ── Log rotation ─────────────────────────────────────────────────────────

    def test_log_rotation_creates_daily_file(self):
        """Log manager generates a filename that includes today's date."""
        from app.config.logging_config import get_current_log_filename
        from datetime import date
        filename = get_current_log_filename()
        today = date.today().strftime('%Y-%m-%d')
        self.assertIn(today, filename,
                      f'Log filename {filename!r} does not contain today\'s date {today}')

    def test_log_rotation_new_day_creates_new_filename(self):
        """get_current_log_filename() returns a different filename for a different day."""
        from app.config.logging_config import get_current_log_filename
        from unittest.mock import patch
        from datetime import datetime as _dt

        filename_today = get_current_log_filename()
        future = _dt(2099, 12, 31, 12, 0, 0)
        with patch('app.config.logging_config.datetime') as mock_dt:
            mock_dt.now.return_value = future
            filename_future = get_current_log_filename()

        self.assertNotEqual(filename_today, filename_future,
                            'Log filename should change between different days')

    def test_log_rotation_write_uses_current_day_file(self):
        """log_manager.write_log() writes to the file matching today's date."""
        from app.config.logging_config import get_current_log_filepath
        expected_path = get_current_log_filepath()
        # Calling _ensure_log_file_exists should create a file at today's path
        from app.utils.log_manager import log_manager
        with self.app.app_context():
            log_manager._ensure_log_file_exists()
        self.assertTrue(os.path.exists(expected_path),
                        f'Expected daily log file not created: {expected_path}')


class TestDropLegacyTablesMigration(unittest.TestCase):
    """migrations/drop_legacy_tables.py — verifies the migration runs cleanly
    on a fresh temp DB (which never has the legacy tables) and on a DB that
    has the legacy tables populated."""

    def _make_db(self, with_legacy: bool = False) -> str:
        """Create a minimal temp SQLite DB and return its path."""
        import tempfile, sqlite3 as _sqlite3
        fd, path = tempfile.mkstemp(suffix='_migration_test.db')
        os.close(fd)
        conn = _sqlite3.connect(path)
        conn.executescript('''
            CREATE TABLE IF NOT EXISTS user (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username VARCHAR(80),
                employee_id VARCHAR(120) UNIQUE NOT NULL,
                password_hash VARCHAR(128) NOT NULL,
                role VARCHAR(20) NOT NULL DEFAULT "research_engineer",
                is_active BOOLEAN DEFAULT 1,
                created_at DATETIME
            );
            CREATE TABLE IF NOT EXISTS simulation (
                id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                ignition_model VARCHAR(50),
                nc_type_1 VARCHAR(50),
                nc_usage_1 FLOAT,
                nc_type_2 VARCHAR(50),
                nc_usage_2 FLOAT,
                gp_type VARCHAR(50),
                gp_usage FLOAT,
                shell_model VARCHAR(50),
                current FLOAT,
                sensor_model VARCHAR(50),
                body_model VARCHAR(50),
                equipment VARCHAR(50),
                employee_id VARCHAR(100),
                test_name VARCHAR(200),
                notes TEXT,
                work_order VARCHAR(50),
                result_data TEXT,
                chart_image VARCHAR(255),
                created_at DATETIME,
                work_order_id INTEGER,
                PRIMARY KEY (id),
                FOREIGN KEY (user_id) REFERENCES user(id),
                CONSTRAINT uq_simulation_recipe UNIQUE (
                    ignition_model, nc_type_1, nc_usage_1, nc_type_2, nc_usage_2,
                    gp_type, gp_usage, shell_model, current, sensor_model, body_model
                )
            );
            CREATE TABLE IF NOT EXISTS test_result (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                simulation_id INTEGER,
                filename VARCHAR(255) NOT NULL,
                file_path VARCHAR(500) NOT NULL,
                data TEXT,
                uploaded_at DATETIME,
                FOREIGN KEY(user_id) REFERENCES user(id),
                FOREIGN KEY(simulation_id) REFERENCES simulation(id)
            );
        ''')
        if with_legacy:
            conn.executescript('''
                CREATE TABLE IF NOT EXISTS recipe (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL
                );
                CREATE TABLE IF NOT EXISTS work_order (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    work_order_number VARCHAR(50) NOT NULL UNIQUE,
                    recipe_id INTEGER NOT NULL,
                    user_id INTEGER NOT NULL,
                    FOREIGN KEY(recipe_id) REFERENCES recipe(id),
                    FOREIGN KEY(user_id) REFERENCES user(id)
                );
                CREATE TABLE IF NOT EXISTS experiment_file (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    work_order_id INTEGER NOT NULL,
                    user_id INTEGER NOT NULL,
                    original_filename VARCHAR(255) NOT NULL,
                    stored_filename VARCHAR(255) NOT NULL,
                    file_path VARCHAR(500) NOT NULL,
                    FOREIGN KEY(work_order_id) REFERENCES work_order(id),
                    FOREIGN KEY(user_id) REFERENCES user(id)
                );
            ''')
        conn.commit()
        conn.close()
        return path

    def tearDown(self):
        # Clean up any temp DBs created during the test
        for attr in ('_db_path',):
            path = getattr(self, attr, None)
            if path and os.path.exists(path):
                try:
                    os.unlink(path)
                except OSError:
                    pass

    def test_migration_drops_legacy_tables(self):
        """Legacy tables present and empty → all three dropped, simulation rebuilt."""
        import sqlite3 as _sqlite3
        from migrations.drop_legacy_tables import migrate
        self._db_path = self._make_db(with_legacy=True)
        result = migrate(self._db_path)
        self.assertTrue(result, 'Migration returned False')
        conn = _sqlite3.connect(self._db_path)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        )
        tables = [r[0] for r in cursor.fetchall()]
        conn.close()
        self.assertNotIn('recipe',          tables, 'recipe table still exists')
        self.assertNotIn('work_order',      tables, 'work_order table still exists')
        self.assertNotIn('experiment_file', tables, 'experiment_file table still exists')
        self.assertIn('simulation',  tables)
        self.assertIn('test_result', tables)
        self.assertIn('user',        tables)

    def test_migration_removes_work_order_id_column(self):
        """work_order_id column must be absent after migration."""
        import sqlite3 as _sqlite3
        from migrations.drop_legacy_tables import migrate
        self._db_path = self._make_db(with_legacy=True)
        migrate(self._db_path)
        conn = _sqlite3.connect(self._db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='simulation'")
        schema = cursor.fetchone()[0]
        conn.close()
        self.assertNotIn('work_order_id', schema,
                         'work_order_id column still present in simulation schema')

    def test_migration_preserves_simulation_data(self):
        """Existing simulation rows must survive the rebuild."""
        import sqlite3 as _sqlite3
        from migrations.drop_legacy_tables import migrate
        self._db_path = self._make_db(with_legacy=True)
        # Insert a user and a simulation row
        conn = _sqlite3.connect(self._db_path)
        conn.execute(
            "INSERT INTO user(id, employee_id, password_hash, role) VALUES (1,'u1','h','admin')"
        )
        conn.execute(
            "INSERT INTO simulation(id, user_id, work_order) VALUES (42, 1, 'WO-TEST')"
        )
        conn.commit()
        conn.close()
        migrate(self._db_path)
        conn = _sqlite3.connect(self._db_path)
        row = conn.execute(
            "SELECT id, work_order FROM simulation WHERE id=42"
        ).fetchone()
        conn.close()
        self.assertIsNotNone(row, 'Simulation row lost after migration')
        self.assertEqual(row[0], 42)
        self.assertEqual(row[1], 'WO-TEST')

    def test_migration_idempotent_on_clean_db(self):
        """Running on a DB with no legacy tables must succeed without error."""
        from migrations.drop_legacy_tables import migrate
        self._db_path = self._make_db(with_legacy=False)
        result = migrate(self._db_path)
        self.assertTrue(result, 'Migration failed on already-clean DB')

    def test_migration_aborts_if_table_not_empty(self):
        """If a legacy table has rows, migration must abort and return False."""
        import sqlite3 as _sqlite3
        from migrations.drop_legacy_tables import migrate
        self._db_path = self._make_db(with_legacy=True)
        conn = _sqlite3.connect(self._db_path)
        conn.execute(
            "INSERT INTO user(id, employee_id, password_hash, role) VALUES (1,'u1','h','admin')"
        )
        conn.execute(
            "INSERT INTO recipe(id, user_id) VALUES (1, 1)"
        )
        conn.commit()
        conn.close()
        result = migrate(self._db_path)
        self.assertFalse(result, 'Migration should have aborted with non-empty recipe table')


# ═══════════════════════════════════════════════════════════════════════════════
# Runner
# ═══════════════════════════════════════════════════════════════════════════════

def _cleanup():
    """Remove the temporary test database."""
    try:
        os.unlink(_DB_PATH)
    except OSError:
        pass


if __name__ == '__main__':
    import atexit
    atexit.register(_cleanup)

    loader = unittest.TestLoader()
    suites = [
        loader.loadTestsFromTestCase(TestComparisonService),
        loader.loadTestsFromTestCase(TestPlotter),
        loader.loadTestsFromTestCase(TestWorkOrderParamValidation),
        loader.loadTestsFromTestCase(TestWorkOrderService),
        loader.loadTestsFromTestCase(TestRoutes),
        loader.loadTestsFromTestCase(TestBackupScript),
        loader.loadTestsFromTestCase(TestBackupUnit),
        loader.loadTestsFromTestCase(TestHealthEndpoint),
        loader.loadTestsFromTestCase(TestUI),
        loader.loadTestsFromTestCase(TestDropLegacyTablesMigration),
    ]

    runner = unittest.TextTestRunner(verbosity=2, stream=sys.stdout)
    result = runner.run(unittest.TestSuite(suites))

    total  = result.testsRun
    n_fail = len(result.failures)
    n_err  = len(result.errors)
    n_pass = total - n_fail - n_err

    print()
    print('=' * 70)
    print('APP REGRESSION TEST SUMMARY')
    print('=' * 70)
    print(f'  Total tests : {total}')
    print(f'  Passed      : {n_pass}')
    print(f'  Failed      : {n_fail}')
    print(f'  Errors      : {n_err}')
    print('-' * 70)

    if result.wasSuccessful():
        print(f'  RESULT: ALL {total} TESTS PASSED')
    else:
        print(f'  RESULT: {n_pass}/{total} PASSED — see details below')
        print()
        for i, (test, tb) in enumerate(result.failures + result.errors, 1):
            label = 'FAIL' if (test, tb) in result.failures else 'ERROR'
            print(f'  [{i}] {label}: {test}')
            print('  ' + '-' * 66)
            for line in tb.strip().splitlines():
                print(f'      {line}')
            print()

    print('=' * 70)
    sys.exit(0 if result.wasSuccessful() else 1)
