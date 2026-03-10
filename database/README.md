# MGG Database — Current Schema

**Version:** 4.1 (Live / Implemented)
**Engine:** PostgreSQL (production) · SQLite (development/testing, when `DATABASE_URL` is not set)
**Tables:** 3 (`user`, `simulation`, `test_result`)
**Last Updated:** 2026-03-09

> This document describes the schema **actually running** in the application (`app/models.py`).
> For the future normalized design (time-series tables, archival, etc.) see `DATABASE_SCHEMA_VISUALIZATION.md`.

---

## Schema Overview

```
┌──────────────────────────────────────┐
│               user                   │
│  Authentication & Authorization      │
└──────────┬───────────────────────────┘
           │ user_id (FK)
           │
┌──────────▼───────────────────────────┐
│             simulation               │
│  Recipe params + ML result (JSON)    │
│                                      │
│  LAB-WIDE DEDUP: one record per      │
│  unique recipe, regardless of user   │
└──────────┬───────────────────────────┘
           │ simulation_id (FK, nullable)
           │
┌──────────▼───────────────────────────┐
│            test_result               │
│  Uploaded experiment file + PT data  │
│  user_id = who uploaded (always set) │
└──────────────────────────────────────┘
```

---

## Table Descriptions

### 1. `user`

| Column | Type | Notes |
|--------|------|-------|
| `id` | INTEGER PK | Auto-increment |
| `employee_id` | VARCHAR(120) UNIQUE NOT NULL | Login credential (工号) |
| `username` | VARCHAR(80) NOT NULL | Display name |
| `password_hash` | VARCHAR(128) | Bcrypt hash |
| `role` | VARCHAR(20) | `admin` \| `research_engineer` \| `lab_engineer` |
| `phone` | VARCHAR(20) | Contact number (optional) |
| `is_active` | BOOLEAN | Account enabled flag (default: True) |
| `session_token` | VARCHAR(100) | Remember-me / force-logout token (nullable) |
| `last_seen_at` | DATETIME | Last activity timestamp, throttled update (nullable) |
| `created_at` | DATETIME | Auto-set on insert |

**Notes:**
- `session_token` is set to `NULL` by admin force-logout ("kick") — the user's next request fails authentication.
- `last_seen_at` is updated at most once per minute per session to reduce write pressure.

---

### 2. `simulation`

One record per **unique recipe** (lab-wide). If two users run the same 11-parameter recipe, the second call returns the first user's existing record — no duplicate inference.

**Recipe fields** (define uniqueness — 11 fields):

| Column | Type | UI Label | Valid Options |
|--------|------|----------|---------------|
| `ignition_model` | VARCHAR(50) | 点火具型号 | 60, 85, 115, 135, 235, 自定义 |
| `nc_type_1` | VARCHAR(50) | NC类型1 | A, B, C, E, F, G, M, 自定义 |
| `nc_usage_1` | FLOAT | NC用量1 (mg) | numeric |
| `nc_type_2` | VARCHAR(50) | NC类型2 | 无, A, B, C, E, F, G, M, 自定义 |
| `nc_usage_2` | FLOAT | NC用量2 (mg) | numeric |
| `gp_type` | VARCHAR(50) | GP类型 | D, GP-3, J, K, L, GG, 自定义 |
| `gp_usage` | FLOAT | GP用量 (mg) | numeric |
| `shell_model` | VARCHAR(50) | 管壳高度 (mm) | 17.8, 18, 18.3, 22, 24, 31.4, 34, 自定义 |
| `current` | FLOAT | 通电条件 (A) | 1.2, 1.75, 自定义 |
| `sensor_model` | VARCHAR(50) | 传感器量程 (/MPa) | 30, 60, 100, 200, 300, 自定义 |
| `body_model` | VARCHAR(50) | 容积 (mL) | 3.5, 6, 8-1082, 10-892, 10-1027, 10-6008, 10-6044, 11.5-6056, 27, 自定义 |

**Metadata fields** (not part of recipe uniqueness):

| Column | Type | Description |
|--------|------|-------------|
| `user_id` | INTEGER FK | Who created this record (first to run the recipe) |
| `equipment` | VARCHAR(50) | 测试设备 (Y-M, Y-H, J-H1_1, J-H2_2, 自定义) |
| `employee_id` | VARCHAR(100) | Operator 工号 |
| `test_name` | VARCHAR(200) | 测试名称 |
| `notes` | TEXT | 备注 |
| `work_order` | VARCHAR(50) | 工单号 — used by 工单查询 feature |

**Result fields**:

| Column | Type | Notes |
|--------|------|-------|
| `result_data` | TEXT | JSON: `{"time": [...], "pressure": [...]}` from ML model |
| `chart_image` | VARCHAR(255) | Path to generated chart file (optional) |
| `created_at` | DATETIME | Auto-set on insert |

---

### 3. `test_result`

Stores an uploaded experiment file and its parsed PT data. Linked to a `simulation` to enable recipe-aware PT comparison and work order grouping.

| Column | Type | Notes |
|--------|------|-------|
| `id` | INTEGER PK | Auto-increment |
| `user_id` | INTEGER FK NOT NULL | Who uploaded (always recorded — cross-user attribution) |
| `simulation_id` | INTEGER FK NULLABLE | Linked simulation (recipe/work order context) |
| `filename` | VARCHAR(255) | Secure filename |
| `file_path` | VARCHAR(500) | Absolute path on disk |
| `data` | TEXT | JSON: `{"time": [...], "pressure": [...]}` |
| `uploaded_at` | DATETIME | Auto-set on insert |

---

## Key Design Decisions

### Recipe Deduplication (Lab-Wide)
Recipes are a physical concept — the same 11 parameters always produce the same simulation result. Instead of one record per user per run, the system maintains **one record per unique recipe** across all users:

```python
# In SimulationService.run_forward_simulation():
existing = self._build_recipe_query(params).first()  # cross-user query
if existing and existing.result_data:
    return {'simulation_id': existing.id, 'data': ...}  # instant reuse
# else: run ML inference and persist new record
```

### Cross-User PT Comparison
When displaying PT曲线对比, **all test results linked to any simulation with the matching recipe are pooled** — regardless of which user uploaded them. This gives better statistics and reflects the shared-lab nature of the data.

### Work Order — Stub Creation
If a test result is uploaded with a `work_order` string that has no matching simulation, a stub `Simulation` record is created automatically (with `work_order` set but no recipe parameters or result). This ensures the work order is immediately visible in 工单查询 without requiring a simulation run first.

### Delete Permissions
- **Regular user:** can delete only their own `TestResult` records (`TestResult.user_id == current_user.id`)
- **Admin:** can delete any test result or any work order and all linked records
- When a work order is deleted, only the deleting user's test results are physically removed (unless admin)

### File Attribution
Even though recipe data is shared, `TestResult.user_id` always records the individual who uploaded that specific file — providing a complete audit trail.

### PT Data Storage (JSON in `test_result.data`)
Test data is stored as a JSON blob:
```json
{"time": [0, 0.01, 0.02, ...], "pressure": [0.0, 0.12, 0.45, ...]}
```
Typical row count: ~4,000 points per file.

> **Future migration note:** For large-scale deployments, consider splitting this into a
> `test_time_series` table (one row per point) for efficient SQL filtering and pagination.
> See `DATABASE_SCHEMA_VISUALIZATION.md` for the full normalized design.

---

## Database Operations

### Initialization (automatic on `python run.py`)
```python
from database.manager import init_database
init_database(app)
# Creates all tables, seeds default admin (SQLite dev: also enables WAL mode)
```

### Backup

**Automated daily backup (recommended):**
```bash
# Run manually
python scripts/backup.py

# Cron — daily at 02:00
0 2 * * * cd /opt/mgg/MGG_SYS && \
          /opt/mgg/MGG_SYS/venv/bin/python scripts/backup.py \
          >> /var/log/mgg_backup.log 2>&1
```

Backs up: database (SQLite `.db` copy or PostgreSQL `.dump`), `instance/uploads/` (tar.gz), `app/log/` (tar.gz). Keeps 30 days by default (`--retention-days N` to change).

**From application code:**
```python
from database.manager import backup_database
path = backup_database(app)
print(f'Backup written to: {path}')
# SQLite:     instance/backups/mgg_backup_YYYYMMDD_HHMMSS.db
# PostgreSQL: instance/backups/mgg_backup_YYYYMMDD_HHMMSS.dump
```

### Reset (destructive — deletes all data)
```python
from database.manager import reset_database
reset_database(app)
# Drops all tables, re-creates schema, re-seeds default admin
```

### Common ORM Queries
```python
from app.models import User, Simulation, TestResult

# All simulations, newest first
Simulation.query.order_by(Simulation.created_at.desc()).all()

# All test results for a specific work order
sims = Simulation.query.filter_by(work_order='WO-001').all()
sim_ids = [s.id for s in sims]
TestResult.query.filter(TestResult.simulation_id.in_(sim_ids)).all()

# All uploads by a specific user
TestResult.query.filter_by(user_id=user_id).all()

# Find existing simulation by recipe (dedup check)
# → see SimulationService._build_recipe_query() in app/services/simulation_service.py
```

---

## File Locations

| Item | Path |
|------|------|
| SQLite database (dev only) | `instance/simulation_system.db` |
| Database backups | `instance/backups/` |
| Uploaded test files | `instance/uploads/` |
| Temp files (validation) | `instance/temp/` |
| SQLAlchemy models | `app/models.py` |
| SimulationService | `app/services/simulation_service.py` |
| FileService | `app/services/file_service.py` |
| WorkOrderService | `app/services/work_order_service.py` |
| Database manager | `database/manager.py` |

---

## Regression Tests

The database-layer test suite covers all models, constraints, relationships, WAL mode, backup logic, `reset_database()`, and seeded data integrity:

```bash
# Database-layer tests only
python database/database_regression_test.py

# Full application regression tests (62 tests, includes backup script tests)
python app_regression_test.py
```

All tests use a temporary SQLite file — the production database is never touched.
