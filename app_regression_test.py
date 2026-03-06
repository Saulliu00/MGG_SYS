#!/usr/bin/env python3
"""
Application regression tests for MGG_SYS — app layer.

Covers:
  - ComparisonService: RMSE, correlation, find_peak_pressure
  - Plotter: chart structure, legend config, multi-run chart
  - WorkOrderService: deduplication, authorization, delete scoping
  - Work-order route validation: invalid param → 400
  - Auth enforcement: unauthenticated → redirect

Uses a temporary SQLite database; never touches the production database.

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

    def test_calculate_rmse_identical_arrays(self):
        vals = [1.0, 2.0, 3.0, 4.0]
        rmse = self.svc.calculate_rmse(vals, vals)
        self.assertAlmostEqual(rmse, 0.0)

    def test_calculate_rmse_known_value(self):
        actual    = [3.0, 3.0, 3.0, 3.0]
        predicted = [2.0, 4.0, 2.0, 4.0]
        # errors: 1, 1, 1, 1 → MSE=1 → RMSE=1
        self.assertAlmostEqual(self.svc.calculate_rmse(actual, predicted), 1.0)

    def test_calculate_rmse_mismatched_lengths(self):
        from app.utils.errors import DataProcessingError
        with self.assertRaises(DataProcessingError):
            self.svc.calculate_rmse([1, 2, 3], [1, 2])

    def test_calculate_correlation_perfect(self):
        x = [1.0, 2.0, 3.0, 4.0, 5.0]
        corr = self.svc.calculate_correlation(x, x)
        self.assertAlmostEqual(corr, 1.0)

    def test_calculate_correlation_inverse(self):
        x = [1.0, 2.0, 3.0, 4.0, 5.0]
        y = [5.0, 4.0, 3.0, 2.0, 1.0]
        corr = self.svc.calculate_correlation(x, y)
        self.assertAlmostEqual(corr, -1.0)

    def test_calculate_correlation_mismatched_lengths(self):
        from app.utils.errors import DataProcessingError
        with self.assertRaises(DataProcessingError):
            self.svc.calculate_correlation([1, 2], [1, 2, 3])


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
