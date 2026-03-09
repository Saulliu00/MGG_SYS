# MGG_SYS Changelog

All significant changes, bug fixes, and their root causes are logged here.
New entries go at the top.

---

## [2026-03-09] PostgreSQL support + automated daily backup

### Changes

**PostgreSQL support (`app/__init__.py`, `requirements.txt`):**
- Added `psycopg2-binary>=2.9.11` dependency
- `SQLALCHEMY_ENGINE_OPTIONS` is now conditional: PostgreSQL gets full connection pooling (`pool_size=25`, `max_overflow=25`, `pool_timeout=10`, `pool_recycle=3600`, `pool_pre_ping=True`); SQLite keeps `check_same_thread=False`
- Removed SQLite-only migration block that used raw `sqlite3.connect()` + `PRAGMA table_info`
- Setting `DATABASE_URL=postgresql://...` is all that is needed to switch from SQLite to PostgreSQL

**System monitor (`app/utils/system_monitor.py`):**
- Removed all `sqlite3.connect()` calls; replaced with SQLAlchemy ORM queries
- PostgreSQL DB size now retrieved via `pg_database_size(current_database())`
- Backup inventory updated to recognise both `.db` (SQLite) and `.dump` (pg_dump) files
- `_DB_TABLES` updated from stale 9-table list to current 3-table schema

**Database backup (`database/manager.py`, `scripts/backup.py`):**
- `backup_database()` now supports both SQLite (file copy) and PostgreSQL (`pg_dump --format=custom`)
- New `scripts/backup.py`: standalone cron-ready script that backs up database + `instance/uploads/` + `app/log/` as dated archives; `--retention-days N` (default 30)

**Tests (`app_regression_test.py`):**
- Added `TestBackupScript` (5 tests): zero exit code, DB archive, uploads archive, logs archive, stdout mentions all three sections
- Total: 62 tests, all passing

---

## [2026-03-09] Fix: UNIQUE constraint crash on test result upload

### Problem
Uploading a test file with a work order + recipe params that already existed in the DB caused `sqlite3.IntegrityError: UNIQUE constraint failed` on the `simulation` table. The session was then left in a rolled-back state, causing a secondary `PendingRollbackError` when the error handler tried to access `current_user.username`.

### Root Cause
`file_service.process_test_result_upload()` always created a new stub `Simulation` row when a work order had no associated simulation. If a simulation with the same recipe already existed (under a different or no work order), the `INSERT` violated the unique constraint added on 2026-03-05.

### Fix (`app/services/file_service.py`)
1. Before creating a stub, query for an existing simulation with identical recipe params. If found, reuse its ID (and assign the new work order if it had none).
2. Added `session.rollback()` in the exception handler so the session stays usable after any DB error.

---

## [2026-03-05] Database-Level Unique Constraint for Recipe Deduplication

### Problem
Recipe deduplication was enforced only in application logic. Direct DB insertions or race conditions could bypass it and create duplicates.

### Fix
- **`app/models.py`**: Added `UniqueConstraint` on 11 recipe fields (`ignition_model`, `nc_type_1/2`, `nc_usage_1/2`, `gp_type`, `gp_usage`, `shell_model`, `current`, `sensor_model`, `body_model`).
- **`app/services/simulation_service.py`**: `session.commit()` wrapped in `try/except IntegrityError`; on race-condition duplicate, rolls back and returns the existing record.
- **`migrations/add_recipe_unique_constraint.py`**: New migration script — detects/removes duplicates, rebuilds table with constraint, supports `--rollback`.

Migration applied to `instance/simulation_system.db` on 2026-03-05.

---

## [2026-03-04] Fix: Work Orders Not Visible in 工单查询 + Chart Legend

### Problem
Work orders uploaded via the 实验结果 (batch upload) page did not appear in 工单查询. The experiment route saved files to disk but created no `TestResult` DB records. Similarly, uploading a file in 正向 with a new work order created no `Simulation` stub.

### Fix
- **`app/routes/simulation.py`** (experiment route): Now creates a `Simulation` stub + `TestResult` record for each uploaded file.
- **`app/services/file_service.py`**: Now creates a `Simulation` stub when `work_order` is provided and no existing simulation matches.
- **`app/utils/plotter.py`**: Added `LEGEND_CONFIG` to the forward simulation chart.

---

## [2026-03-03] Fix: Browser Cache Breaking Work Order Clicks

### Problem
After `git pull`, work order items were not clickable in 工单查询 — browser cached old `work_order.js` with broken inline `onclick` handler.

### Fix
- **`app/static/js/work_order.js`**: Replaced inline `onclick` with event delegation.
- **`app/templates/work_order/index.html`**: Added `?v=2026030301` cache-busting parameter.

---

## [2026-03-03] Fix: PT曲线对比 Not Finding Experimental Data by Work Order

### Problem
Data uploaded with a work order was stored in a stub `Simulation` (recipe fields NULL). The PT comparison search only matched by recipe params → stub never found → data missing from chart.

### Fix
- **`app/services/simulation_service.py`**: Two-phase search — by recipe params, then also by `work_order` string (if provided). Results merged with no duplicates.
- **`app/templates/simulation/index.html`** + **`app/static/js/simulation.js`**: Added work order search input + 刷新数据 button to the PT曲线对比 tab.

---

## [2026-03-03] Fix: Admin Password Randomized on Each Restart

### Problem
Admin password was generated with `secrets.token_urlsafe(12)` on every Flask startup, making it unpredictable.

### Fix
- **`app/__init__.py`**: Changed to `os.environ.get('ADMIN_PASSWORD', 'admin123')`. Default `admin123`; override with env var for production.

---

## Logging Format

```
## [YYYY-MM-DD] Brief description

### Problem
What was observed.

### Root Cause
Why it happened.

### Fix
Files modified and what changed.
```
