#!/usr/bin/env python3
"""
Migrate data from SQLite → PostgreSQL for MGG_SYS.

Copies all rows from the SQLite instance/simulation_system.db into the
PostgreSQL database specified by DATABASE_URL, preserving all IDs and
timestamps. Safe to run multiple times (skips rows that already exist).

Usage:
    export DATABASE_URL=postgresql://mgg_user:mgg_secure_2026@localhost:5432/mgg_simulation
    export SECRET_KEY=any_value_for_migration
    python migrations/sqlite_to_postgresql.py

Prerequisites:
    - PostgreSQL server running with mgg_simulation database created
    - DATABASE_URL env var set
    - Python venv active (pip install -r requirements.txt)
"""

import os
import sys
import sqlite3
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.resolve()
SQLITE_PATH  = PROJECT_ROOT / 'instance' / 'simulation_system.db'


def _create_indexes(pg_db):
    """Create performance indexes concurrently (no table lock, safe on live DB)."""
    indexes = [
        # INDEX 1: work_order lookups — 5+ query paths, currently full scan
        (
            'ix_simulation_work_order',
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_simulation_work_order "
            "ON simulation (work_order) "
            "WHERE work_order IS NOT NULL AND work_order != ''"
        ),
        # INDEX 2: simulation history page — filter+sort without extra heap sort
        (
            'ix_simulation_user_id_created_at',
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_simulation_user_id_created_at "
            "ON simulation (user_id, created_at)"
        ),
        # INDEX 3: test_result.simulation_id FK — 3x IN-clause queries, no auto-index in PG
        (
            'ix_test_result_simulation_id',
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_test_result_simulation_id "
            "ON test_result (simulation_id)"
        ),
        # INDEX 4: test_result.user_id — authorization check filter
        (
            'ix_test_result_user_id',
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_test_result_user_id "
            "ON test_result (user_id)"
        ),
    ]

    # CONCURRENTLY requires autocommit (cannot run inside a transaction block)
    with pg_db.engine.connect().execution_options(isolation_level='AUTOCOMMIT') as conn:
        for name, sql in indexes:
            conn.execute(pg_db.text(sql))
            print(f'  [index]       {name}  OK')


def main():
    db_url = os.environ.get('DATABASE_URL', '')
    if not db_url.startswith('postgresql'):
        print('ERROR: DATABASE_URL must point to PostgreSQL.')
        print('  export DATABASE_URL=postgresql://mgg_user:<password>@localhost:5432/mgg_simulation')
        sys.exit(1)

    if not SQLITE_PATH.is_file():
        print(f'ERROR: SQLite database not found at {SQLITE_PATH}')
        sys.exit(1)

    # Bootstrap Flask app so SQLAlchemy creates tables in PostgreSQL
    os.environ.setdefault('SECRET_KEY', 'migration_temp_key')
    sys.path.insert(0, str(PROJECT_ROOT))
    from app import create_app, db as pg_db
    app = create_app()

    # Open SQLite source
    src = sqlite3.connect(str(SQLITE_PATH))
    src.row_factory = sqlite3.Row

    with app.app_context():
        pg_db.create_all()

        # ── 0. Indexes ────────────────────────────────────────────────────────
        # CREATE INDEX CONCURRENTLY cannot run inside a transaction, so we use
        # a raw AUTOCOMMIT connection. IF NOT EXISTS makes this idempotent.
        _create_indexes(pg_db)

        # ── 1. Users ──────────────────────────────────────────────────────────
        rows = src.execute('SELECT * FROM user').fetchall()
        inserted = skipped = 0
        for r in rows:
            from app.models import User
            if pg_db.session.get(User, r['id']):
                skipped += 1
                continue
            row = dict(r)
            row['is_active'] = bool(row['is_active'])  # SQLite int → PG boolean
            pg_db.session.execute(
                pg_db.text(
                    'INSERT INTO "user" (id, username, employee_id, password_hash, phone, '
                    'role, is_active, created_at, last_seen_at, session_token) '
                    'VALUES (:id, :username, :employee_id, :password_hash, :phone, '
                    ':role, :is_active, :created_at, :last_seen_at, :session_token)'
                ),
                row
            )
            inserted += 1
        pg_db.session.commit()
        # Reset PG sequence so next auto-increment ID doesn't collide
        if rows:
            max_id = max(r['id'] for r in rows)
            pg_db.session.execute(
                pg_db.text(f"SELECT setval('user_id_seq', {max_id}, true)")
            )
            pg_db.session.commit()
        print(f'  [user]        inserted={inserted}  skipped={skipped}')

        # ── 2. Simulations ────────────────────────────────────────────────────
        rows = src.execute('SELECT * FROM simulation').fetchall()
        inserted = skipped = 0
        for r in rows:
            from app.models import Simulation
            if pg_db.session.get(Simulation, r['id']):
                skipped += 1
                continue
            pg_db.session.execute(
                pg_db.text(
                    'INSERT INTO simulation (id, user_id, ignition_model, nc_type_1, nc_usage_1, '
                    'nc_type_2, nc_usage_2, gp_type, gp_usage, shell_model, current, '
                    'sensor_model, body_model, equipment, employee_id, test_name, notes, '
                    'work_order, result_data, chart_image, created_at) '
                    'VALUES (:id, :user_id, :ignition_model, :nc_type_1, :nc_usage_1, '
                    ':nc_type_2, :nc_usage_2, :gp_type, :gp_usage, :shell_model, :current, '
                    ':sensor_model, :body_model, :equipment, :employee_id, :test_name, :notes, '
                    ':work_order, :result_data, :chart_image, :created_at)'
                ),
                dict(r)
            )
            inserted += 1
        pg_db.session.commit()
        if rows:
            max_id = max(r['id'] for r in rows)
            pg_db.session.execute(
                pg_db.text(f"SELECT setval('simulation_id_seq', {max_id}, true)")
            )
            pg_db.session.commit()
        print(f'  [simulation]  inserted={inserted}  skipped={skipped}')

        # ── 3. TestResults ────────────────────────────────────────────────────
        rows = src.execute('SELECT * FROM test_result').fetchall()
        inserted = skipped = 0
        for r in rows:
            from app.models import TestResult
            if pg_db.session.get(TestResult, r['id']):
                skipped += 1
                continue
            pg_db.session.execute(
                pg_db.text(
                    'INSERT INTO test_result (id, user_id, simulation_id, filename, '
                    'file_path, data, uploaded_at) '
                    'VALUES (:id, :user_id, :simulation_id, :filename, '
                    ':file_path, :data, :uploaded_at)'
                ),
                dict(r)
            )
            inserted += 1
        pg_db.session.commit()
        if rows:
            max_id = max(r['id'] for r in rows)
            pg_db.session.execute(
                pg_db.text(f"SELECT setval('test_result_id_seq', {max_id}, true)")
            )
            pg_db.session.commit()
        print(f'  [test_result] inserted={inserted}  skipped={skipped}')

    src.close()
    print('\nMigration complete. Verify with:')
    print(f'  psql {db_url} -c "SELECT COUNT(*) FROM \\"user\\"; SELECT COUNT(*) FROM simulation; SELECT COUNT(*) FROM test_result;"')


if __name__ == '__main__':
    print(f'SQLite source: {SQLITE_PATH}')
    print(f'PostgreSQL target: {os.environ.get("DATABASE_URL", "(DATABASE_URL not set)")}')
    print()
    main()
