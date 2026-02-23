"""Database regression tests.

Tests all 6 models, relationships, constraints, backup logic, WAL mode,
and seeding.  Uses a temporary SQLite database so the production database
is never touched.

Run from the project root:
    python database/tests.py
"""
import json
import os
import sys
import tempfile
import unittest
from datetime import date, timedelta

# Ensure project root is on the path when run directly
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _make_test_app(db_path):
    """Create a minimal Flask app pointing at a temp SQLite file."""
    from flask import Flask
    from database import db, login_manager, bcrypt, init_database

    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SECRET_KEY'] = 'test-secret'
    app.config['WTF_CSRF_ENABLED'] = False

    db.init_app(app)
    login_manager.init_app(app)
    bcrypt.init_app(app)

    init_database(app)
    return app


# ---------------------------------------------------------------------------
# Base class: creates a fresh temp DB for every test
# ---------------------------------------------------------------------------

class DatabaseTestCase(unittest.TestCase):
    def setUp(self):
        self.db_fd, self.db_path = tempfile.mkstemp(suffix='.db')
        self.app = _make_test_app(self.db_path)
        self.ctx = self.app.app_context()
        self.ctx.push()
        from database.extensions import db
        self.db = db

    def tearDown(self):
        self.db.session.remove()
        self.ctx.pop()
        os.close(self.db_fd)
        os.unlink(self.db_path)


# ---------------------------------------------------------------------------
# 1. Extensions
# ---------------------------------------------------------------------------

class TestExtensions(unittest.TestCase):
    """database/extensions.py — db, login_manager, bcrypt are importable."""

    def test_db_instance(self):
        from database.extensions import db
        from flask_sqlalchemy import SQLAlchemy
        self.assertIsInstance(db, SQLAlchemy)

    def test_login_manager_instance(self):
        from database.extensions import login_manager
        from flask_login import LoginManager
        self.assertIsInstance(login_manager, LoginManager)

    def test_bcrypt_instance(self):
        from database.extensions import bcrypt
        from flask_bcrypt import Bcrypt
        self.assertIsInstance(bcrypt, Bcrypt)

    def test_public_api_exports(self):
        import database
        for name in ['db', 'login_manager', 'bcrypt', 'init_database', 'daily_backup',
                     'User', 'Simulation', 'TestResult', 'Recipe', 'WorkOrder', 'ExperimentFile']:
            self.assertTrue(hasattr(database, name), f'database.{name} not exported')


# ---------------------------------------------------------------------------
# 2. Init / seeding / WAL mode
# ---------------------------------------------------------------------------

class TestInitDatabase(DatabaseTestCase):
    """database/manager.py — init_database() creates tables and seeds admin."""

    def test_all_tables_exist(self):
        from sqlalchemy import inspect
        tables = inspect(self.db.engine).get_table_names()
        for expected in ['user', 'recipe', 'work_order', 'experiment_file',
                         'simulation', 'test_result']:
            self.assertIn(expected, tables, f'Table "{expected}" missing')

    def test_admin_user_seeded(self):
        from database import User
        admin = User.query.filter_by(employee_id='admin').first()
        self.assertIsNotNone(admin, 'Default admin not created')
        self.assertEqual(admin.role, 'admin')
        self.assertTrue(admin.check_password('admin123'))

    def test_wal_mode_enabled(self):
        from sqlalchemy import text
        result = self.db.session.execute(text('PRAGMA journal_mode')).fetchone()
        self.assertEqual(result[0], 'wal', 'WAL mode not enabled')

    def test_init_idempotent(self):
        """Calling init_database a second time must not raise or duplicate admin."""
        from database import init_database, User
        init_database(self.app)
        admins = User.query.filter_by(employee_id='admin').all()
        self.assertEqual(len(admins), 1, 'Duplicate admin created on second init')


# ---------------------------------------------------------------------------
# 3. User model
# ---------------------------------------------------------------------------

class TestUserModel(DatabaseTestCase):

    def _make_user(self, employee_id='EMP001', role='research_engineer'):
        from database import User
        u = User(username='Test User', employee_id=employee_id, role=role)
        u.set_password('password123')
        self.db.session.add(u)
        self.db.session.commit()
        return u

    def test_create_user(self):
        u = self._make_user()
        self.assertIsNotNone(u.id)
        self.assertEqual(u.employee_id, 'EMP001')

    def test_password_hash_not_plaintext(self):
        u = self._make_user()
        self.assertNotEqual(u.password_hash, 'password123')

    def test_check_password_correct(self):
        u = self._make_user()
        self.assertTrue(u.check_password('password123'))

    def test_check_password_wrong(self):
        u = self._make_user()
        self.assertFalse(u.check_password('wrongpassword'))

    def test_role_properties_research_engineer(self):
        u = self._make_user(role='research_engineer')
        self.assertTrue(u.is_research_engineer)
        self.assertFalse(u.is_admin)
        self.assertFalse(u.is_lab_engineer)

    def test_role_properties_lab_engineer(self):
        u = self._make_user(employee_id='EMP002', role='lab_engineer')
        self.assertTrue(u.is_lab_engineer)
        self.assertFalse(u.is_admin)

    def test_role_properties_admin(self):
        from database import User
        admin = User.query.filter_by(employee_id='admin').first()
        self.assertTrue(admin.is_admin)

    def test_employee_id_unique_constraint(self):
        from sqlalchemy.exc import IntegrityError
        self._make_user(employee_id='DUP001')
        with self.assertRaises(IntegrityError):
            self._make_user(employee_id='DUP001')

    def test_is_active_default_true(self):
        u = self._make_user()
        self.assertTrue(u.is_active)

    def test_query_by_employee_id(self):
        from database import User
        self._make_user(employee_id='FIND001')
        found = User.query.filter_by(employee_id='FIND001').first()
        self.assertIsNotNone(found)
        self.assertEqual(found.username, 'Test User')


# ---------------------------------------------------------------------------
# 4. Recipe model
# ---------------------------------------------------------------------------

class TestRecipeModel(DatabaseTestCase):

    def _make_recipe(self, user):
        from database import Recipe
        r = Recipe(
            user_id=user.id,
            ignition_model='IGN-A',
            nc_type_1='NC-1', nc_usage_1=50.0,
            nc_type_2='NC-2', nc_usage_2=30.0,
            gp_type='GP-X',   gp_usage=20.0,
            shell_model='SH-10',
            current_condition='1A/1ms',
            sensor_range='0-50MPa',
            body_model='VOL-5',
            equipment='EQ-01',
        )
        self.db.session.add(r)
        self.db.session.commit()
        return r

    def _make_user(self, eid='R001'):
        from database import User
        u = User(employee_id=eid, role='research_engineer')
        u.set_password('pw')
        self.db.session.add(u)
        self.db.session.commit()
        return u

    def test_create_recipe(self):
        u = self._make_user()
        r = self._make_recipe(u)
        self.assertIsNotNone(r.id)
        self.assertEqual(r.ignition_model, 'IGN-A')
        self.assertEqual(r.nc_usage_1, 50.0)
        self.assertEqual(r.current_condition, '1A/1ms')
        self.assertEqual(r.sensor_range, '0-50MPa')

    def test_recipe_belongs_to_user(self):
        from database import Recipe
        u = self._make_user()
        self._make_recipe(u)
        r = Recipe.query.filter_by(user_id=u.id).first()
        self.assertIsNotNone(r)
        self.assertEqual(r.user_id, u.id)

    def test_all_condition_fields_stored(self):
        u = self._make_user(eid='R002')
        r = self._make_recipe(u)
        self.assertEqual(r.gp_type, 'GP-X')
        self.assertEqual(r.gp_usage, 20.0)
        self.assertEqual(r.shell_model, 'SH-10')
        self.assertEqual(r.body_model, 'VOL-5')
        self.assertEqual(r.equipment, 'EQ-01')


# ---------------------------------------------------------------------------
# 5. WorkOrder model
# ---------------------------------------------------------------------------

class TestWorkOrderModel(DatabaseTestCase):

    def _setup(self):
        from database import User, Recipe, WorkOrder
        u = User(employee_id='WO001', role='research_engineer')
        u.set_password('pw')
        self.db.session.add(u)
        self.db.session.flush()

        r = Recipe(user_id=u.id, ignition_model='IGN-B', current_condition='2A')
        self.db.session.add(r)
        self.db.session.flush()

        wo = WorkOrder(
            work_order_number='WO-2026-001',
            recipe_id=r.id,
            user_id=u.id,
            employee_id='WO001',
            test_name='Batch Test 1',
            test_date=date(2026, 2, 18),
            test_time='09:30',
            source='simulation',
        )
        self.db.session.add(wo)
        self.db.session.commit()
        return u, r, wo

    def test_create_work_order(self):
        _, _, wo = self._setup()
        self.assertIsNotNone(wo.id)
        self.assertEqual(wo.work_order_number, 'WO-2026-001')
        self.assertEqual(wo.source, 'simulation')

    def test_work_order_number_unique(self):
        from database import User, Recipe, WorkOrder
        from sqlalchemy.exc import IntegrityError
        u, r, _ = self._setup()
        self.db.session.rollback()
        # Rebuild to avoid state pollution from previous commit
        u2 = User(employee_id='WO002', role='research_engineer')
        u2.set_password('pw')
        self.db.session.add(u2)
        self.db.session.flush()
        r2 = Recipe(user_id=u2.id)
        self.db.session.add(r2)
        self.db.session.flush()
        dup = WorkOrder(work_order_number='WO-2026-001', recipe_id=r2.id, user_id=u2.id)
        self.db.session.add(dup)
        with self.assertRaises(IntegrityError):
            self.db.session.commit()

    def test_work_order_date_and_time(self):
        _, _, wo = self._setup()
        self.assertEqual(wo.test_date, date(2026, 2, 18))
        self.assertEqual(wo.test_time, '09:30')

    def test_work_order_links_recipe(self):
        _, r, wo = self._setup()
        self.assertEqual(wo.recipe_id, r.id)
        self.assertEqual(wo.recipe.ignition_model, 'IGN-B')

    def test_source_values(self):
        _, _, wo = self._setup()
        self.assertIn(wo.source, ('simulation', 'experiment'))


# ---------------------------------------------------------------------------
# 6. ExperimentFile model
# ---------------------------------------------------------------------------

class TestExperimentFileModel(DatabaseTestCase):

    def _setup(self):
        from database import User, Recipe, WorkOrder, ExperimentFile
        u = User(employee_id='EF001', role='lab_engineer')
        u.set_password('pw')
        self.db.session.add(u)
        self.db.session.flush()

        r = Recipe(user_id=u.id)
        self.db.session.add(r)
        self.db.session.flush()

        wo = WorkOrder(work_order_number='WO-EF-001', recipe_id=r.id, user_id=u.id,
                       source='experiment')
        self.db.session.add(wo)
        self.db.session.flush()

        ef1 = ExperimentFile(work_order_id=wo.id, user_id=u.id,
                             original_filename='test_run_1.xlsx',
                             stored_filename='abc-uuid-1.xlsx',
                             file_path='/uploads/abc-uuid-1.xlsx', file_size=4096)
        ef2 = ExperimentFile(work_order_id=wo.id, user_id=u.id,
                             original_filename='test_run_2.xlsx',
                             stored_filename='abc-uuid-2.xlsx',
                             file_path='/uploads/abc-uuid-2.xlsx', file_size=5120)
        self.db.session.add_all([ef1, ef2])
        self.db.session.commit()
        return u, wo, [ef1, ef2]

    def test_create_experiment_files(self):
        _, wo, files = self._setup()
        self.assertEqual(len(files), 2)
        self.assertIsNotNone(files[0].id)

    def test_multiple_files_per_work_order(self):
        from database import ExperimentFile
        _, wo, _ = self._setup()
        results = ExperimentFile.query.filter_by(work_order_id=wo.id).all()
        self.assertEqual(len(results), 2)

    def test_original_and_stored_filenames(self):
        _, _, files = self._setup()
        self.assertEqual(files[0].original_filename, 'test_run_1.xlsx')
        self.assertNotEqual(files[0].original_filename, files[0].stored_filename)

    def test_cascade_delete_with_work_order(self):
        from database import ExperimentFile
        _, wo, _ = self._setup()
        wo_id = wo.id
        self.db.session.delete(wo)
        self.db.session.commit()
        remaining = ExperimentFile.query.filter_by(work_order_id=wo_id).all()
        self.assertEqual(len(remaining), 0, 'ExperimentFiles not cascade-deleted')


# ---------------------------------------------------------------------------
# 7. Simulation model
# ---------------------------------------------------------------------------

class TestSimulationModel(DatabaseTestCase):

    def _setup(self):
        from database import User, Recipe, WorkOrder, Simulation
        u = User(employee_id='SIM001', role='research_engineer')
        u.set_password('pw')
        self.db.session.add(u)
        self.db.session.flush()

        r = Recipe(user_id=u.id, ignition_model='IGN-C', nc_type_1='NC-A',
                   nc_usage_1=40.0, gp_type='GP-Y', gp_usage=15.0)
        self.db.session.add(r)
        self.db.session.flush()

        wo = WorkOrder(work_order_number='WO-SIM-001', recipe_id=r.id,
                       user_id=u.id, source='simulation')
        self.db.session.add(wo)
        self.db.session.flush()

        result_data = json.dumps({'peak_pressure': 35.2, 'rise_time': 1.8, 'r_squared': 0.99})
        sim = Simulation(
            user_id=u.id,
            work_order_id=wo.id,
            ignition_model='IGN-C',
            nc_type_1='NC-A', nc_usage_1=40.0,
            gp_type='GP-Y', gp_usage=15.0,
            test_name='Forward Simulation 1',
            result_data=result_data,
        )
        self.db.session.add(sim)
        self.db.session.commit()
        return u, wo, sim

    def test_create_simulation(self):
        _, _, sim = self._setup()
        self.assertIsNotNone(sim.id)
        self.assertEqual(sim.test_name, 'Forward Simulation 1')

    def test_result_data_json(self):
        _, _, sim = self._setup()
        data = json.loads(sim.result_data)
        self.assertAlmostEqual(data['peak_pressure'], 35.2)
        self.assertAlmostEqual(data['r_squared'], 0.99)

    def test_simulation_linked_to_work_order(self):
        _, wo, sim = self._setup()
        self.assertEqual(sim.work_order_id, wo.id)
        self.assertEqual(sim.work_order_ref.work_order_number, 'WO-SIM-001')

    def test_simulation_history_query(self):
        from database import Simulation
        u, _, _ = self._setup()
        results = Simulation.query.filter_by(user_id=u.id).order_by(
            Simulation.created_at.desc()).limit(50).all()
        self.assertEqual(len(results), 1)


# ---------------------------------------------------------------------------
# 8. TestResult model
# ---------------------------------------------------------------------------

class TestTestResultModel(DatabaseTestCase):

    def test_create_test_result(self):
        from database import User, Simulation, TestResult
        u = User(employee_id='TR001', role='lab_engineer')
        u.set_password('pw')
        self.db.session.add(u)
        self.db.session.flush()

        sim = Simulation(user_id=u.id, test_name='TR Test')
        self.db.session.add(sim)
        self.db.session.flush()

        data = json.dumps({'time': [0, 1, 2], 'pressure': [0.0, 10.5, 35.2]})
        tr = TestResult(user_id=u.id, simulation_id=sim.id,
                        filename='result.xlsx', file_path='/uploads/result.xlsx',
                        data=data)
        self.db.session.add(tr)
        self.db.session.commit()

        self.assertIsNotNone(tr.id)
        parsed = json.loads(tr.data)
        self.assertEqual(parsed['pressure'][2], 35.2)

    def test_test_result_without_simulation(self):
        """simulation_id is nullable — upload without linking to simulation."""
        from database import User, TestResult
        u = User(employee_id='TR002', role='lab_engineer')
        u.set_password('pw')
        self.db.session.add(u)
        self.db.session.flush()

        tr = TestResult(user_id=u.id, simulation_id=None,
                        filename='standalone.xlsx',
                        file_path='/uploads/standalone.xlsx')
        self.db.session.add(tr)
        self.db.session.commit()
        self.assertIsNone(tr.simulation_id)


# ---------------------------------------------------------------------------
# 9. Relationships
# ---------------------------------------------------------------------------

class TestRelationships(DatabaseTestCase):

    def _full_setup(self):
        from database import User, Recipe, WorkOrder, ExperimentFile, Simulation
        u = User(employee_id='REL001', role='research_engineer')
        u.set_password('pw')
        self.db.session.add(u)
        self.db.session.flush()

        r = Recipe(user_id=u.id, ignition_model='IGN-REL')
        self.db.session.add(r)
        self.db.session.flush()

        wo = WorkOrder(work_order_number='WO-REL-001', recipe_id=r.id,
                       user_id=u.id, source='simulation')
        self.db.session.add(wo)
        self.db.session.flush()

        ef = ExperimentFile(work_order_id=wo.id, user_id=u.id,
                            original_filename='f.xlsx', stored_filename='uuid.xlsx',
                            file_path='/u/uuid.xlsx')
        sim = Simulation(user_id=u.id, work_order_id=wo.id, test_name='REL sim')
        self.db.session.add_all([ef, sim])
        self.db.session.commit()
        return u, r, wo, ef, sim

    def test_user_has_recipes(self):
        u, r, _, _, _ = self._full_setup()
        self.assertIn(r, u.recipes)

    def test_user_has_work_orders(self):
        u, _, wo, _, _ = self._full_setup()
        self.assertIn(wo, u.work_orders)

    def test_recipe_has_work_orders(self):
        _, r, wo, _, _ = self._full_setup()
        self.assertIn(wo, r.work_orders)

    def test_work_order_has_experiment_files(self):
        _, _, wo, ef, _ = self._full_setup()
        self.assertIn(ef, wo.experiment_files)

    def test_work_order_has_simulations(self):
        _, _, wo, _, sim = self._full_setup()
        self.assertIn(sim, wo.simulations)

    def test_backref_from_simulation_to_work_order(self):
        _, _, wo, _, sim = self._full_setup()
        self.assertEqual(sim.work_order_ref.work_order_number, 'WO-REL-001')

    def test_backref_from_experiment_file_to_work_order(self):
        _, _, wo, ef, _ = self._full_setup()
        self.assertEqual(ef.work_order.work_order_number, 'WO-REL-001')


# ---------------------------------------------------------------------------
# 10. Backup
# ---------------------------------------------------------------------------

class TestBackup(unittest.TestCase):

    def setUp(self):
        self.db_fd, self.db_path = tempfile.mkstemp(suffix='.db')
        self.backup_dir = os.path.join(os.path.dirname(self.db_path), 'test_backups')
        os.makedirs(self.backup_dir, exist_ok=True)
        self.app = _make_test_app(self.db_path)

    def tearDown(self):
        import shutil
        os.close(self.db_fd)
        os.unlink(self.db_path)
        if os.path.exists(self.backup_dir):
            shutil.rmtree(self.backup_dir)

    def _backup_dir_for_app(self):
        """Return the backup dir next to the DB file."""
        return os.path.join(os.path.dirname(self.db_path), 'backups')

    def test_backup_creates_file(self):
        from database import daily_backup
        with self.app.app_context():
            daily_backup(self.app)
        bdir = self._backup_dir_for_app()
        today = date.today().isoformat()
        backup_file = os.path.join(bdir, f'simulation_system_{today}.db')
        self.assertTrue(os.path.exists(backup_file), 'Backup file not created')

    def test_backup_is_valid_sqlite(self):
        import sqlite3 as _sqlite3
        from database import daily_backup
        with self.app.app_context():
            daily_backup(self.app)
        bdir = self._backup_dir_for_app()
        today = date.today().isoformat()
        backup_file = os.path.join(bdir, f'simulation_system_{today}.db')
        conn = _sqlite3.connect(backup_file)
        tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        conn.close()
        table_names = [t[0] for t in tables]
        self.assertIn('user', table_names)
        self.assertIn('work_order', table_names)

    def test_backup_idempotent(self):
        """Calling daily_backup twice on the same day must not raise."""
        from database import daily_backup
        with self.app.app_context():
            daily_backup(self.app)
            mtime_before = os.path.getmtime(
                os.path.join(self._backup_dir_for_app(),
                             f'simulation_system_{date.today().isoformat()}.db'))
            daily_backup(self.app)
            mtime_after = os.path.getmtime(
                os.path.join(self._backup_dir_for_app(),
                             f'simulation_system_{date.today().isoformat()}.db'))
        self.assertEqual(mtime_before, mtime_after, 'Backup overwritten on second call')

    def test_cleanup_removes_old_backups(self):
        """Backup files older than 30 days must be deleted after a new backup."""
        from database.backup import _cleanup_old_backups
        bdir = self._backup_dir_for_app()
        os.makedirs(bdir, exist_ok=True)

        # Plant an old backup file (31 days ago)
        old_date = (date.today() - timedelta(days=31)).isoformat()
        old_file = os.path.join(bdir, f'simulation_system_{old_date}.db')
        open(old_file, 'w').close()

        # Plant a recent backup file (5 days ago) — should be kept
        recent_date = (date.today() - timedelta(days=5)).isoformat()
        recent_file = os.path.join(bdir, f'simulation_system_{recent_date}.db')
        open(recent_file, 'w').close()

        with self.app.app_context():
            _cleanup_old_backups(bdir, self.app)

        self.assertFalse(os.path.exists(old_file), 'Old backup not deleted')
        self.assertTrue(os.path.exists(recent_file), 'Recent backup wrongly deleted')

    def test_backup_skipped_for_non_sqlite(self):
        """daily_backup must silently skip when DB URI is not sqlite:///."""
        from database import daily_backup
        from unittest.mock import patch
        # Patch the app config to look like a PostgreSQL URI without needing the driver
        with self.app.app_context():
            with patch.dict(self.app.config, {'SQLALCHEMY_DATABASE_URI': 'postgresql://user:pw@localhost/fake'}):
                bdir = self._backup_dir_for_app()
                files_before = set(os.listdir(bdir)) if os.path.exists(bdir) else set()
                try:
                    daily_backup(self.app)
                except Exception as e:
                    self.fail(f'daily_backup raised for non-SQLite URI: {e}')
                files_after = set(os.listdir(bdir)) if os.path.exists(bdir) else set()
                self.assertEqual(files_before, files_after, 'Backup created for non-SQLite URI')


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

if __name__ == '__main__':
    loader = unittest.TestLoader()
    # Run suites in logical order
    suites = [
        loader.loadTestsFromTestCase(TestExtensions),
        loader.loadTestsFromTestCase(TestInitDatabase),
        loader.loadTestsFromTestCase(TestUserModel),
        loader.loadTestsFromTestCase(TestRecipeModel),
        loader.loadTestsFromTestCase(TestWorkOrderModel),
        loader.loadTestsFromTestCase(TestExperimentFileModel),
        loader.loadTestsFromTestCase(TestSimulationModel),
        loader.loadTestsFromTestCase(TestTestResultModel),
        loader.loadTestsFromTestCase(TestRelationships),
        loader.loadTestsFromTestCase(TestBackup),
    ]
    runner = unittest.TextTestRunner(verbosity=2, stream=sys.stdout)
    result = runner.run(unittest.TestSuite(suites))

    # ── Summary ──────────────────────────────────────────────────────────────
    total   = result.testsRun
    n_fail  = len(result.failures)
    n_err   = len(result.errors)
    n_pass  = total - n_fail - n_err

    print()
    print('=' * 70)
    print(f'DATABASE REGRESSION TEST SUMMARY')
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

        for i, (test, tb) in enumerate(result.failures, 1):
            print(f'  [{i}] FAIL: {test}')
            print('  ' + '-' * 66)
            # Indent each traceback line for readability
            for line in tb.strip().splitlines():
                print(f'      {line}')
            print()

        for i, (test, tb) in enumerate(result.errors, 1):
            print(f'  [{i}] ERROR: {test}')
            print('  ' + '-' * 66)
            for line in tb.strip().splitlines():
                print(f'      {line}')
            print()

    print('=' * 70)
    sys.exit(0 if result.wasSuccessful() else 1)
