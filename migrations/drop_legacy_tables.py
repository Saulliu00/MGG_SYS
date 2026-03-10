"""
Migration: Drop legacy tables and clean up simulation schema

Removes three empty, abandoned tables from an earlier design iteration:
  - experiment_file   (was linked to work_order via FK)
  - work_order        (separate work-order table, replaced by simulation.work_order string)
  - recipe            (separate recipe table, replaced by columns on simulation)

Also removes the stale work_order_id column from simulation that referenced
the old work_order table.  The column has always been NULL; no data is lost.

Safe to run: verifies all three tables are empty before dropping.

Usage:
    python migrations/drop_legacy_tables.py
    python migrations/drop_legacy_tables.py --rollback   # not supported — one-way only

Author: MGG_SYS
Date:   2026-03-09
"""

import sqlite3
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

_DEFAULT_DB = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    'instance', 'simulation_system.db'
)

_LEGACY_TABLES = ['experiment_file', 'work_order', 'recipe']


def migrate(db_path: str = _DEFAULT_DB) -> bool:
    print(f'Starting migration on: {db_path}')

    if not os.path.exists(db_path):
        print(f'ERROR: Database not found at {db_path}')
        return False

    conn = sqlite3.connect(db_path)
    conn.execute('PRAGMA foreign_keys = OFF')
    cursor = conn.cursor()

    try:
        # 1. Verify legacy tables are empty ─────────────────────────────────
        for table in _LEGACY_TABLES:
            cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
                (table,)
            )
            if not cursor.fetchone():
                print(f'  [SKIP]  Table "{table}" does not exist — already clean.')
                continue
            cursor.execute(f'SELECT COUNT(*) FROM "{table}"')
            count = cursor.fetchone()[0]
            if count > 0:
                print(
                    f'  [ERROR] Table "{table}" has {count} row(s). '
                    f'Aborting — manual review required.'
                )
                conn.rollback()
                return False

        # 2. Drop legacy tables (order matters: child before parent) ─────────
        for table in _LEGACY_TABLES:
            cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
                (table,)
            )
            if cursor.fetchone():
                cursor.execute(f'DROP TABLE "{table}"')
                print(f'  [DROP]  Table "{table}" dropped.')
            else:
                print(f'  [SKIP]  Table "{table}" not found.')

        # 3. Rebuild simulation without the stale work_order_id column ───────
        cursor.execute(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name='simulation'"
        )
        row = cursor.fetchone()
        if row and 'work_order_id' in row[0]:
            print('  [REBUILD] Removing work_order_id column from simulation…')
            cursor.execute('''
                CREATE TABLE simulation_clean (
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
                    PRIMARY KEY (id),
                    FOREIGN KEY (user_id) REFERENCES user(id),
                    CONSTRAINT uq_simulation_recipe UNIQUE (
                        ignition_model, nc_type_1, nc_usage_1, nc_type_2, nc_usage_2,
                        gp_type, gp_usage, shell_model, current, sensor_model, body_model
                    )
                )
            ''')
            cursor.execute('''
                INSERT INTO simulation_clean
                SELECT id, user_id, ignition_model, nc_type_1, nc_usage_1,
                       nc_type_2, nc_usage_2, gp_type, gp_usage, shell_model,
                       current, sensor_model, body_model, equipment, employee_id,
                       test_name, notes, work_order, result_data, chart_image, created_at
                FROM simulation
            ''')
            cursor.execute('DROP TABLE simulation')
            cursor.execute('ALTER TABLE simulation_clean RENAME TO simulation')
            print('  [REBUILD] simulation table rebuilt without work_order_id.')
        else:
            print('  [SKIP]  work_order_id not present in simulation — already clean.')

        conn.commit()
        print()
        print('Migration completed successfully.')
        print('Tables remaining:', _list_tables(cursor))
        return True

    except sqlite3.Error as e:
        print(f'ERROR: {e}')
        conn.rollback()
        return False
    finally:
        try:
            conn.execute('PRAGMA foreign_keys = ON')
        except sqlite3.Error:
            pass
        conn.close()


def _list_tables(cursor) -> list:
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    return [r[0] for r in cursor.fetchall()]


if __name__ == '__main__':
    if '--rollback' in sys.argv:
        print('Rollback is not supported for this migration (tables were empty — no data lost).')
        sys.exit(1)
    success = migrate()
    sys.exit(0 if success else 1)
