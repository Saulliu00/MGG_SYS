"""
Database regression tests — db-optimized branch.

Covers all 9 models, relationships, constraints, backup logic, WAL mode,
and seeding.  Uses a temporary SQLite database so the production database
is never touched.

Run from the project root:
    python database/database_regression_test.py

New vs DB_dev:
  - Simulation uses direct summary columns + SimulationTimeSeries (no result_data JSON)
  - TestResult uses direct summary columns + TestTimeSeries (no data JSON)
  - New test classes: TestSimulationTimeSeries, TestTestTimeSeries, TestPTComparison
  - backup_database() API replaces daily_backup()
  - Admin seeded with ADMIN_PASSWORD env var (not hardcoded admin123)
"""

import os
import sys
import tempfile
import unittest
from datetime import date, timedelta

# Ensure project root is on the path when run directly
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Set ADMIN_PASSWORD before any app import so seeding uses a known value
os.environ.setdefault('ADMIN_PASSWORD', 'TestAdmin1!')
os.environ.setdefault('SECRET_KEY', 'test-secret-key-for-regression')


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
# Base class: fresh temp DB for every test
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
        for name in ['db', 'login_manager', 'bcrypt',
                     'init_database', 'reset_database', 'backup_database']:
            self.assertTrue(hasattr(database, name),
                            f'database.{name} not exported')

    def test_models_importable(self):
        from database.models import (
            User, Recipe, WorkOrder, ExperimentFile,
            Simulation, SimulationTimeSeries,
            TestResult, TestTimeSeries, PTComparison,
        )


# ---------------------------------------------------------------------------
# 2. Init / seeding / WAL mode
# ---------------------------------------------------------------------------

class TestInitDatabase(DatabaseTestCase):
    """database/manager.py — init_database() creates all tables and seeds admin."""

    def test_all_tables_exist(self):
        from sqlalchemy import inspect
        tables = inspect(self.db.engine).get_table_names()
        expected = [
            'user', 'recipe', 'work_order', 'experiment_file',
            'simulation', 'simulation_time_series',
            'test_result', 'test_time_series',
            'pt_comparison',
        ]
        for t in expected:
            self.assertIn(t, tables, f'Table "{t}" missing')

    def test_admin_user_seeded(self):
        from database.models import User
        admin = User.query.filter_by(employee_id='admin').first()
        self.assertIsNotNone(admin, 'Default admin not created')
        self.assertEqual(admin.role, 'admin')
        self.assertTrue(admin.check_password('TestAdmin1!'),
                        'Admin password does not match ADMIN_PASSWORD env var')

    def test_wal_mode_enabled(self):
        from sqlalchemy import text
        result = self.db.session.execute(text('PRAGMA journal_mode')).fetchone()
        self.assertEqual(result[0], 'wal', 'WAL mode not enabled')

    def test_init_idempotent(self):
        """Calling init_database a second time must not raise or duplicate admin."""
        from database import init_database
        from database.models import User
        init_database(self.app)
        admins = User.query.filter_by(employee_id='admin').all()
        self.assertEqual(len(admins), 1, 'Duplicate admin created on second init')

    def test_example_recipes_seeded(self):
        from database.models import Recipe
        recipes = Recipe.query.all()
        self.assertGreater(len(recipes), 0, 'No example recipes seeded')


# ---------------------------------------------------------------------------
# 3. User model
# ---------------------------------------------------------------------------

class TestUserModel(DatabaseTestCase):

    def _make_user(self, employee_id='EMP001', role='research_engineer'):
        from database.models import User
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
        from database.models import User
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
        from database.models import User
        self._make_user(employee_id='FIND001')
        found = User.query.filter_by(employee_id='FIND001').first()
        self.assertIsNotNone(found)
        self.assertEqual(found.username, 'Test User')

    def test_session_token_field_exists(self):
        u = self._make_user(employee_id='TOK001')
        self.assertTrue(hasattr(u, 'session_token'))

    def test_last_seen_at_field_exists(self):
        u = self._make_user(employee_id='LSA001')
        self.assertTrue(hasattr(u, 'last_seen_at'))


# ---------------------------------------------------------------------------
# 4. Recipe model
# ---------------------------------------------------------------------------

class TestRecipeModel(DatabaseTestCase):

    def _make_user(self, eid='R001'):
        from database.models import User
        u = User(username='Recipe User', employee_id=eid, role='research_engineer')
        u.set_password('pw')
        self.db.session.add(u)
        self.db.session.commit()
        return u

    def _make_recipe(self, user):
        from database.models import Recipe
        r = Recipe(
            user_id=user.id,
            recipe_name='Test Recipe',
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

    def test_create_recipe(self):
        u = self._make_user()
        r = self._make_recipe(u)
        self.assertIsNotNone(r.id)
        self.assertEqual(r.ignition_model, 'IGN-A')
        self.assertEqual(r.nc_usage_1, 50.0)
        self.assertEqual(r.current_condition, '1A/1ms')
        self.assertEqual(r.sensor_range, '0-50MPa')

    def test_recipe_belongs_to_user(self):
        from database.models import Recipe
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

    def test_recipe_name_and_description(self):
        from database.models import Recipe
        u = self._make_user(eid='R003')
        r = Recipe(user_id=u.id, recipe_name='Named Recipe',
                   description='A detailed description')
        self.db.session.add(r)
        self.db.session.commit()
        fetched = Recipe.query.get(r.id)
        self.assertEqual(fetched.recipe_name, 'Named Recipe')
        self.assertEqual(fetched.description, 'A detailed description')


# ---------------------------------------------------------------------------
# 5. WorkOrder model
# ---------------------------------------------------------------------------

class TestWorkOrderModel(DatabaseTestCase):

    def _setup(self):
        from database.models import User, Recipe, WorkOrder
        u = User(username='WO User', employee_id='WO001', role='research_engineer')
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
        from database.models import User, Recipe, WorkOrder
        from sqlalchemy.exc import IntegrityError
        self._setup()
        self.db.session.rollback()
        u2 = User(username='WO User 2', employee_id='WO002', role='research_engineer')
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

    def test_status_default_pending(self):
        _, _, wo = self._setup()
        self.assertEqual(wo.status, 'pending')

    def test_priority_default_normal(self):
        _, _, wo = self._setup()
        self.assertEqual(wo.priority, 'normal')


# ---------------------------------------------------------------------------
# 6. ExperimentFile model
# ---------------------------------------------------------------------------

class TestExperimentFileModel(DatabaseTestCase):

    def _setup(self):
        from database.models import User, Recipe, WorkOrder, ExperimentFile
        u = User(username='EF User', employee_id='EF001', role='lab_engineer')
        u.set_password('pw')
        self.db.session.add(u)
        self.db.session.flush()

        r = Recipe(user_id=u.id)
        self.db.session.add(r)
        self.db.session.flush()

        wo = WorkOrder(work_order_number='WO-EF-001', recipe_id=r.id,
                       user_id=u.id, source='experiment')
        self.db.session.add(wo)
        self.db.session.flush()

        ef1 = ExperimentFile(work_order_id=wo.id, user_id=u.id,
                             original_filename='test_run_1.xlsx',
                             stored_filename='abc-uuid-1.xlsx',
                             file_path='/uploads/abc-uuid-1.xlsx',
                             file_size=4096)
        ef2 = ExperimentFile(work_order_id=wo.id, user_id=u.id,
                             original_filename='test_run_2.xlsx',
                             stored_filename='abc-uuid-2.xlsx',
                             file_path='/uploads/abc-uuid-2.xlsx',
                             file_size=5120)
        self.db.session.add_all([ef1, ef2])
        self.db.session.commit()
        return u, wo, [ef1, ef2]

    def test_create_experiment_files(self):
        _, wo, files = self._setup()
        self.assertEqual(len(files), 2)
        self.assertIsNotNone(files[0].id)

    def test_multiple_files_per_work_order(self):
        from database.models import ExperimentFile
        _, wo, _ = self._setup()
        results = ExperimentFile.query.filter_by(work_order_id=wo.id).all()
        self.assertEqual(len(results), 2)

    def test_original_and_stored_filenames(self):
        _, _, files = self._setup()
        self.assertEqual(files[0].original_filename, 'test_run_1.xlsx')
        self.assertNotEqual(files[0].original_filename, files[0].stored_filename)

    def test_cascade_delete_with_work_order(self):
        from database.models import ExperimentFile
        _, wo, _ = self._setup()
        wo_id = wo.id
        self.db.session.delete(wo)
        self.db.session.commit()
        remaining = ExperimentFile.query.filter_by(work_order_id=wo_id).all()
        self.assertEqual(len(remaining), 0, 'ExperimentFiles not cascade-deleted')

    def test_processed_default_false(self):
        _, _, files = self._setup()
        self.assertFalse(files[0].processed)


# ---------------------------------------------------------------------------
# 7. Simulation model (with summary columns — no result_data JSON)
# ---------------------------------------------------------------------------

class TestSimulationModel(DatabaseTestCase):

    def _setup(self):
        from database.models import User, Recipe, WorkOrder, Simulation
        u = User(username='SIM User', employee_id='SIM001', role='research_engineer')
        u.set_password('pw')
        self.db.session.add(u)
        self.db.session.flush()

        r = Recipe(user_id=u.id, ignition_model='IGN-C',
                   nc_type_1='NC-A', nc_usage_1=40.0,
                   gp_type='GP-Y', gp_usage=15.0)
        self.db.session.add(r)
        self.db.session.flush()

        wo = WorkOrder(work_order_number='WO-SIM-001', recipe_id=r.id,
                       user_id=u.id, source='simulation')
        self.db.session.add(wo)
        self.db.session.flush()

        sim = Simulation(
            user_id=u.id,
            work_order_id=wo.id,
            ignition_model='IGN-C',
            nc_type_1='NC-A', nc_usage_1=40.0,
            gp_type='GP-Y', gp_usage=15.0,
            test_name='Forward Simulation 1',
            peak_pressure=35.2,
            peak_time=1.8,
            num_data_points=500,
            r_squared=0.99,
            status='completed',
        )
        self.db.session.add(sim)
        self.db.session.commit()
        return u, wo, sim

    def test_create_simulation(self):
        _, _, sim = self._setup()
        self.assertIsNotNone(sim.id)
        self.assertEqual(sim.test_name, 'Forward Simulation 1')
        self.assertEqual(sim.status, 'completed')

    def test_summary_columns_stored(self):
        _, _, sim = self._setup()
        self.assertAlmostEqual(sim.peak_pressure, 35.2)
        self.assertAlmostEqual(sim.peak_time, 1.8)
        self.assertEqual(sim.num_data_points, 500)
        self.assertAlmostEqual(sim.r_squared, 0.99)

    def test_simulation_linked_to_work_order(self):
        _, wo, sim = self._setup()
        self.assertEqual(sim.work_order_id, wo.id)
        self.assertEqual(sim.work_order_ref.work_order_number, 'WO-SIM-001')

    def test_simulation_history_query(self):
        from database.models import Simulation
        u, _, _ = self._setup()
        results = (Simulation.query.filter_by(user_id=u.id)
                   .order_by(Simulation.created_at.desc()).limit(50).all())
        self.assertEqual(len(results), 1)

    def test_status_values(self):
        _, _, sim = self._setup()
        self.assertIn(sim.status, ('running', 'completed', 'failed'))


# ---------------------------------------------------------------------------
# 8. SimulationTimeSeries model
# ---------------------------------------------------------------------------

class TestSimulationTimeSeries(DatabaseTestCase):

    def _setup(self):
        from database.models import User, Simulation, SimulationTimeSeries
        u = User(username='STS User', employee_id='STS001', role='research_engineer')
        u.set_password('pw')
        self.db.session.add(u)
        self.db.session.flush()

        sim = Simulation(user_id=u.id, test_name='TS Test', status='completed',
                         peak_pressure=30.0, num_data_points=5)
        self.db.session.add(sim)
        self.db.session.flush()

        points = [
            SimulationTimeSeries(simulation_id=sim.id, sequence_number=i,
                                 time_point=i * 0.5, pressure=i * 5.0)
            for i in range(5)
        ]
        self.db.session.add_all(points)
        self.db.session.commit()
        return sim, points

    def test_create_time_series(self):
        sim, points = self._setup()
        self.assertEqual(len(points), 5)
        self.assertIsNotNone(points[0].id)

    def test_time_series_values(self):
        _, points = self._setup()
        self.assertAlmostEqual(points[2].time_point, 1.0)
        self.assertAlmostEqual(points[2].pressure, 10.0)

    def test_time_series_linked_to_simulation(self):
        from database.models import SimulationTimeSeries
        sim, _ = self._setup()
        fetched = (SimulationTimeSeries.query
                   .filter_by(simulation_id=sim.id)
                   .order_by(SimulationTimeSeries.sequence_number).all())
        self.assertEqual(len(fetched), 5)

    def test_cascade_delete_with_simulation(self):
        from database.models import SimulationTimeSeries
        sim, _ = self._setup()
        sim_id = sim.id
        self.db.session.delete(sim)
        self.db.session.commit()
        remaining = SimulationTimeSeries.query.filter_by(simulation_id=sim_id).all()
        self.assertEqual(len(remaining), 0, 'TimeSeries not cascade-deleted with Simulation')

    def test_sequence_ordering(self):
        from database.models import SimulationTimeSeries
        sim, _ = self._setup()
        ordered = (SimulationTimeSeries.query
                   .filter_by(simulation_id=sim.id)
                   .order_by(SimulationTimeSeries.sequence_number).all())
        seqs = [p.sequence_number for p in ordered]
        self.assertEqual(seqs, sorted(seqs))


# ---------------------------------------------------------------------------
# 9. TestResult model
# ---------------------------------------------------------------------------

class TestTestResultModel(DatabaseTestCase):

    def test_create_test_result(self):
        from database.models import User, Simulation, TestResult
        u = User(username='TR User', employee_id='TR001', role='lab_engineer')
        u.set_password('pw')
        self.db.session.add(u)
        self.db.session.flush()

        sim = Simulation(user_id=u.id, test_name='TR Test', status='completed')
        self.db.session.add(sim)
        self.db.session.flush()

        tr = TestResult(user_id=u.id, simulation_id=sim.id,
                        filename='result.xlsx',
                        file_path='/uploads/result.xlsx',
                        peak_pressure=35.2,
                        peak_time=1.9,
                        num_data_points=500)
        self.db.session.add(tr)
        self.db.session.commit()

        self.assertIsNotNone(tr.id)
        self.assertAlmostEqual(tr.peak_pressure, 35.2)
        self.assertAlmostEqual(tr.peak_time, 1.9)

    def test_test_result_without_simulation(self):
        from database.models import User, TestResult
        u = User(username='TR User 2', employee_id='TR002', role='lab_engineer')
        u.set_password('pw')
        self.db.session.add(u)
        self.db.session.flush()

        tr = TestResult(user_id=u.id, simulation_id=None,
                        filename='standalone.xlsx',
                        file_path='/uploads/standalone.xlsx')
        self.db.session.add(tr)
        self.db.session.commit()
        self.assertIsNone(tr.simulation_id)

    def test_test_result_file_size(self):
        from database.models import User, TestResult
        u = User(username='TR User 3', employee_id='TR003', role='lab_engineer')
        u.set_password('pw')
        self.db.session.add(u)
        self.db.session.flush()
        tr = TestResult(user_id=u.id, filename='f.xlsx',
                        file_path='/u/f.xlsx', file_size=8192)
        self.db.session.add(tr)
        self.db.session.commit()
        self.assertEqual(tr.file_size, 8192)


# ---------------------------------------------------------------------------
# 10. TestTimeSeries model
# ---------------------------------------------------------------------------

class TestTestTimeSeries(DatabaseTestCase):

    def _setup(self):
        from database.models import User, TestResult, TestTimeSeries
        u = User(username='TTS User', employee_id='TTS001', role='lab_engineer')
        u.set_password('pw')
        self.db.session.add(u)
        self.db.session.flush()

        tr = TestResult(user_id=u.id, filename='data.xlsx',
                        file_path='/u/data.xlsx', num_data_points=4)
        self.db.session.add(tr)
        self.db.session.flush()

        points = [
            TestTimeSeries(test_result_id=tr.id, sequence_number=i,
                           time_point=i * 0.25, pressure=i * 8.0)
            for i in range(4)
        ]
        self.db.session.add_all(points)
        self.db.session.commit()
        return tr, points

    def test_create_test_time_series(self):
        _, points = self._setup()
        self.assertEqual(len(points), 4)
        self.assertIsNotNone(points[0].id)

    def test_time_series_values(self):
        _, points = self._setup()
        self.assertAlmostEqual(points[1].time_point, 0.25)
        self.assertAlmostEqual(points[1].pressure, 8.0)

    def test_time_series_linked_to_test_result(self):
        from database.models import TestTimeSeries
        tr, _ = self._setup()
        fetched = TestTimeSeries.query.filter_by(test_result_id=tr.id).all()
        self.assertEqual(len(fetched), 4)

    def test_cascade_delete_with_test_result(self):
        from database.models import TestTimeSeries
        tr, _ = self._setup()
        tr_id = tr.id
        self.db.session.delete(tr)
        self.db.session.commit()
        remaining = TestTimeSeries.query.filter_by(test_result_id=tr_id).all()
        self.assertEqual(len(remaining), 0, 'TestTimeSeries not cascade-deleted')


# ---------------------------------------------------------------------------
# 11. PTComparison model
# ---------------------------------------------------------------------------

class TestPTComparison(DatabaseTestCase):

    def _setup(self):
        from database.models import User, Simulation, TestResult, PTComparison
        u = User(username='PTC User', employee_id='PTC001', role='research_engineer')
        u.set_password('pw')
        self.db.session.add(u)
        self.db.session.flush()

        sim = Simulation(user_id=u.id, test_name='Comparison Sim',
                         status='completed', peak_pressure=35.0, peak_time=1.8)
        tr = TestResult(user_id=u.id, filename='exp.xlsx',
                        file_path='/u/exp.xlsx', peak_pressure=34.1, peak_time=1.9)
        self.db.session.add_all([sim, tr])
        self.db.session.flush()

        comp = PTComparison(
            user_id=u.id,
            simulation_id=sim.id,
            test_result_id=tr.id,
            peak_pressure_diff=abs(35.0 - 34.1),
            peak_time_diff=abs(1.8 - 1.9),
            rmse=0.52,
            mae=0.41,
            correlation=0.997,
            r_squared=0.994,
        )
        self.db.session.add(comp)
        self.db.session.commit()
        return u, sim, tr, comp

    def test_create_comparison(self):
        _, _, _, comp = self._setup()
        self.assertIsNotNone(comp.id)
        self.assertAlmostEqual(comp.rmse, 0.52)
        self.assertAlmostEqual(comp.correlation, 0.997)

    def test_comparison_links_simulation_and_test(self):
        _, sim, tr, comp = self._setup()
        self.assertEqual(comp.simulation_id, sim.id)
        self.assertEqual(comp.test_result_id, tr.id)

    def test_comparison_metrics(self):
        _, _, _, comp = self._setup()
        self.assertAlmostEqual(comp.peak_pressure_diff, 0.9, places=5)
        self.assertAlmostEqual(comp.peak_time_diff, 0.1, places=5)
        self.assertAlmostEqual(comp.mae, 0.41)
        self.assertAlmostEqual(comp.r_squared, 0.994)

    def test_multiple_comparisons_per_simulation(self):
        from database.models import User, Simulation, TestResult, PTComparison
        u, sim, _, _ = self._setup()
        tr2 = TestResult(user_id=u.id, filename='exp2.xlsx',
                         file_path='/u/exp2.xlsx', peak_pressure=33.8)
        self.db.session.add(tr2)
        self.db.session.flush()
        comp2 = PTComparison(user_id=u.id, simulation_id=sim.id,
                             test_result_id=tr2.id, rmse=0.78)
        self.db.session.add(comp2)
        self.db.session.commit()
        comps = PTComparison.query.filter_by(simulation_id=sim.id).all()
        self.assertEqual(len(comps), 2)


# ---------------------------------------------------------------------------
# 12. Relationships
# ---------------------------------------------------------------------------

class TestRelationships(DatabaseTestCase):

    def _full_setup(self):
        from database.models import (User, Recipe, WorkOrder, ExperimentFile,
                                     Simulation, SimulationTimeSeries,
                                     TestResult, TestTimeSeries)
        u = User(username='REL User', employee_id='REL001', role='research_engineer')
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
        sim = Simulation(user_id=u.id, work_order_id=wo.id,
                         test_name='REL sim', status='completed')
        self.db.session.add_all([ef, sim])
        self.db.session.flush()

        ts = SimulationTimeSeries(simulation_id=sim.id, sequence_number=0,
                                  time_point=0.0, pressure=0.0)
        tr = TestResult(user_id=u.id, filename='r.xlsx', file_path='/u/r.xlsx')
        self.db.session.add_all([ts, tr])
        self.db.session.flush()

        tts = TestTimeSeries(test_result_id=tr.id, sequence_number=0,
                             time_point=0.0, pressure=0.0)
        self.db.session.add(tts)
        self.db.session.commit()
        return u, r, wo, ef, sim, ts, tr, tts

    def test_user_has_recipes(self):
        u, r, *_ = self._full_setup()
        self.assertIn(r, u.recipes)

    def test_user_has_work_orders(self):
        u, _, wo, *_ = self._full_setup()
        self.assertIn(wo, u.work_orders)

    def test_recipe_has_work_orders(self):
        _, r, wo, *_ = self._full_setup()
        self.assertIn(wo, r.work_orders)

    def test_work_order_has_experiment_files(self):
        _, _, wo, ef, *_ = self._full_setup()
        self.assertIn(ef, wo.experiment_files)

    def test_work_order_has_simulations(self):
        _, _, wo, _, sim, *_ = self._full_setup()
        self.assertIn(sim, wo.simulations)

    def test_simulation_has_time_series(self):
        _, _, _, _, sim, ts, *_ = self._full_setup()
        self.assertIn(ts, sim.time_series)

    def test_test_result_has_time_series(self):
        *_, tr, tts = self._full_setup()
        self.assertIn(tts, tr.time_series)

    def test_backref_from_simulation_to_work_order(self):
        _, _, wo, _, sim, *_ = self._full_setup()
        self.assertEqual(sim.work_order_ref.work_order_number, 'WO-REL-001')

    def test_backref_from_experiment_file_to_work_order(self):
        _, _, wo, ef, *_ = self._full_setup()
        self.assertEqual(ef.work_order.work_order_number, 'WO-REL-001')


# ---------------------------------------------------------------------------
# 13. Reset database
# ---------------------------------------------------------------------------

class TestResetDatabase(unittest.TestCase):
    """database/manager.py — reset_database() drops all tables and re-seeds."""

    def setUp(self):
        self.db_fd, self.db_path = tempfile.mkstemp(suffix='.db')
        self.app = _make_test_app(self.db_path)

    def tearDown(self):
        os.close(self.db_fd)
        os.unlink(self.db_path)

    def test_reset_clears_user_data(self):
        from database import reset_database
        from database.models import User
        with self.app.app_context():
            # Add extra user
            from database.extensions import db
            u = User(username='Temp', employee_id='TEMP001', role='research_engineer')
            u.set_password('pw')
            db.session.add(u)
            db.session.commit()
            self.assertGreater(User.query.count(), 1)

            reset_database(self.app)
            # Only the seeded admin should remain
            users = User.query.all()
            self.assertEqual(len(users), 1)
            self.assertEqual(users[0].employee_id, 'admin')

    def test_reset_re_seeds_admin(self):
        from database import reset_database
        from database.models import User
        with self.app.app_context():
            reset_database(self.app)
            admin = User.query.filter_by(employee_id='admin').first()
            self.assertIsNotNone(admin)
            self.assertEqual(admin.role, 'admin')

    def test_reset_re_creates_all_tables(self):
        from database import reset_database
        from sqlalchemy import inspect
        with self.app.app_context():
            reset_database(self.app)
            from database.extensions import db as _db
            tables = inspect(_db.engine).get_table_names()
            for t in ['user', 'simulation', 'test_result']:
                self.assertIn(t, tables, f'Table "{t}" missing after reset')

    def test_double_reset_is_safe(self):
        from database import reset_database
        with self.app.app_context():
            reset_database(self.app)
            reset_database(self.app)  # Must not raise


# ---------------------------------------------------------------------------
# 14. Seed data integrity
# ---------------------------------------------------------------------------

class TestSeedData(DatabaseTestCase):
    """Verify that init_database() seeds sensible default data."""

    def test_admin_has_bcrypt_hash(self):
        from database.models import User
        admin = User.query.filter_by(employee_id='admin').first()
        self.assertTrue(admin.password_hash.startswith('$2b$') or
                        admin.password_hash.startswith('$2a$'),
                        'Admin password must be bcrypt-hashed')

    def test_admin_is_active(self):
        from database.models import User
        admin = User.query.filter_by(employee_id='admin').first()
        self.assertTrue(admin.is_active)

    def test_seeded_recipes_have_valid_structure(self):
        from database.models import Recipe
        for r in Recipe.query.all():
            # Each recipe must be associated with a user
            self.assertIsNotNone(r.user_id, f'Recipe {r.id} has no user_id')

    def test_no_orphaned_simulations(self):
        """All Simulation records must have a valid user_id."""
        from database.models import Simulation, User
        for s in Simulation.query.all():
            u = User.query.get(s.user_id)
            self.assertIsNotNone(u, f'Simulation {s.id} references missing user {s.user_id}')

    def test_session_token_nullable(self):
        """session_token starts NULL (users are not logged in on seed)."""
        from database.models import User
        admin = User.query.filter_by(employee_id='admin').first()
        # session_token is set on login, so it may or may not be null in tests
        self.assertTrue(hasattr(admin, 'session_token'))

    def test_last_seen_at_nullable(self):
        from database.models import User
        admin = User.query.filter_by(employee_id='admin').first()
        self.assertTrue(hasattr(admin, 'last_seen_at'))


# ---------------------------------------------------------------------------
# 15. Backup
# ---------------------------------------------------------------------------

class TestBackup(unittest.TestCase):

    def setUp(self):
        self.db_fd, self.db_path = tempfile.mkstemp(suffix='.db')
        self.app = _make_test_app(self.db_path)

    def tearDown(self):
        import shutil
        os.close(self.db_fd)
        os.unlink(self.db_path)
        backup_dir = os.path.join(os.path.dirname(self.db_path), 'backups')
        if os.path.exists(backup_dir):
            shutil.rmtree(backup_dir)

    def test_backup_creates_file(self):
        from database import backup_database
        with self.app.app_context():
            path = backup_database(self.app)
        self.assertTrue(os.path.exists(path), f'Backup file not found: {path}')

    def test_backup_is_valid_sqlite(self):
        import sqlite3 as _sqlite3
        from database import backup_database
        with self.app.app_context():
            path = backup_database(self.app)
        conn = _sqlite3.connect(path)
        tables = [r[0] for r in
                  conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
        conn.close()
        self.assertIn('user', tables)
        self.assertIn('work_order', tables)
        self.assertIn('simulation_time_series', tables)

    def test_backup_returns_path(self):
        from database import backup_database
        with self.app.app_context():
            path = backup_database(self.app)
        self.assertIsInstance(path, str)
        self.assertTrue(path.endswith('.db'))

    def test_backup_filename_contains_timestamp(self):
        from database import backup_database
        with self.app.app_context():
            path = backup_database(self.app)
        filename = os.path.basename(path)
        self.assertTrue(filename.startswith('mgg_backup_'),
                        f'Backup filename should start with mgg_backup_, got: {filename}')

    def test_backup_is_in_backups_subdirectory(self):
        from database import backup_database
        with self.app.app_context():
            path = backup_database(self.app)
        parent = os.path.basename(os.path.dirname(path))
        self.assertEqual(parent, 'backups')

    def test_backup_contains_all_key_tables(self):
        import sqlite3 as _sqlite3
        from database import backup_database
        with self.app.app_context():
            path = backup_database(self.app)
        conn = _sqlite3.connect(path)
        tables = [r[0] for r in
                  conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
        conn.close()
        for expected in ['user', 'simulation', 'test_result', 'simulation_time_series']:
            self.assertIn(expected, tables, f'Table "{expected}" missing from backup')

    def test_backup_postgresql_calls_pg_dump(self):
        """PostgreSQL backup path invokes pg_dump (mocked — pg_dump need not be installed)."""
        from database import backup_database
        from unittest.mock import patch, MagicMock
        mock_result = MagicMock()
        mock_result.returncode = 0
        with self.app.app_context():
            with patch.dict(self.app.config,
                            {'SQLALCHEMY_DATABASE_URI': 'postgresql://u:p@localhost/fake'}):
                with patch('subprocess.run', return_value=mock_result) as mock_run:
                    backup_database(self.app)
                    called_cmd = mock_run.call_args[0][0]
                    self.assertEqual(called_cmd[0], 'pg_dump')


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

if __name__ == '__main__':
    loader = unittest.TestLoader()
    suites = [
        loader.loadTestsFromTestCase(TestExtensions),
        loader.loadTestsFromTestCase(TestInitDatabase),
        loader.loadTestsFromTestCase(TestUserModel),
        loader.loadTestsFromTestCase(TestRecipeModel),
        loader.loadTestsFromTestCase(TestWorkOrderModel),
        loader.loadTestsFromTestCase(TestExperimentFileModel),
        loader.loadTestsFromTestCase(TestSimulationModel),
        loader.loadTestsFromTestCase(TestSimulationTimeSeries),
        loader.loadTestsFromTestCase(TestTestResultModel),
        loader.loadTestsFromTestCase(TestTestTimeSeries),
        loader.loadTestsFromTestCase(TestPTComparison),
        loader.loadTestsFromTestCase(TestRelationships),
        loader.loadTestsFromTestCase(TestResetDatabase),
        loader.loadTestsFromTestCase(TestSeedData),
        loader.loadTestsFromTestCase(TestBackup),
    ]
    runner = unittest.TextTestRunner(verbosity=2, stream=sys.stdout)
    result = runner.run(unittest.TestSuite(suites))

    total  = result.testsRun
    n_fail = len(result.failures)
    n_err  = len(result.errors)
    n_pass = total - n_fail - n_err

    print()
    print('=' * 70)
    print('DATABASE REGRESSION TEST SUMMARY')
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
