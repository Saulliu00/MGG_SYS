# MGG Database — Current Schema

**Version:** 4.0 (Live / Implemented)
**Engine:** SQLite (dev) — PostgreSQL-compatible
**Tables:** 3 (`user`, `simulation`, `test_result`)
**Last Updated:** 2026-03-02 (rev 2)

> This document describes the schema that is **actually running** in the application.
> For the future optimized design (time-series tables, archival, etc.) see `DATABASE_SCHEMA_VISUALIZATION.md`.

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
| `employee_id` | VARCHAR(120) UNIQUE | Login credential (工号) |
| `username` | VARCHAR(80) | Display name |
| `email` | VARCHAR(120) | Optional |
| `password_hash` | VARCHAR(128) | Bcrypt |
| `role` | VARCHAR(20) | `admin` \| `research_engineer` \| `lab_engineer` |
| `department` | VARCHAR(50) | Optional |
| `is_active` | BOOLEAN | Account enabled flag |
| `session_token` | VARCHAR(100) | Remember-me token |
| `created_at` | DATETIME | Auto |

---

### 2. `simulation`

One record per **unique recipe** (lab-wide). If two users run the same recipe, the second call
returns the first user's existing record — no duplicate is created.

**Recipe fields** (define uniqueness — 11 fields):

| Column | Type | Label |
|--------|------|-------|
| `ignition_model` | VARCHAR(50) | 点火具型号 |
| `nc_type_1` | VARCHAR(50) | NC类型1 |
| `nc_usage_1` | FLOAT | NC用量1 (mg) |
| `nc_type_2` | VARCHAR(50) | NC类型2 |
| `nc_usage_2` | FLOAT | NC用量2 (mg) |
| `gp_type` | VARCHAR(50) | GP类型 |
| `gp_usage` | FLOAT | GP用量 (mg) |
| `shell_model` | VARCHAR(50) | 管壳高度 (mm) |
| `current` | FLOAT | 通电条件 (A) — options: 1.2, 1.75 |
| `sensor_model` | VARCHAR(50) | 传感器量程 (/MPa) — options: 30, 60, 100, 200, 300 |
| `body_model` | VARCHAR(50) | 容积 (mL) — options: 3.5, 6, 8-1082, 10-892, 10-1027, 10-6008, 10-6044, 11.5-6056, 27 |

**UI dropdown reference** (valid values per field):

| Field | UI Label | Valid Options |
|-------|----------|---------------|
| `ignition_model` | 点火具型号 | 60, 85, 115, 135, 235, 自定义 |
| `nc_type_1` | NC类型1 | A, B, C, E, F, G, M, 自定义 |
| `nc_type_2` | NC类型2 | 无, A, B, C, E, F, G, M, 自定义 |
| `gp_type` | GP类型 | D, GP-3, J, K, L, GG, 自定义 |
| `shell_model` | 管壳高度 (mm) | 17.8, 18, 18.3, 22, 24, 31.4, 34, 自定义 |
| `current` | 通电条件 (A) | 1.2, 1.75, 自定义 |
| `sensor_model` | 传感器量程 (/MPa) | 30, 60, 100, 200, 300, 自定义 |
| `body_model` | 容积 (mL) | 3.5, 6, 8-1082, 10-892, 10-1027, 10-6008, 10-6044, 11.5-6056, 27, 自定义 |

**Metadata fields** (not part of recipe uniqueness):

| Column | Type | Label |
|--------|------|-------|
| `user_id` | INTEGER FK | Who created this record (first runner) |
| `equipment` | VARCHAR(50) | 测试设备 — options: Y-M, Y-H, J-H1_1, J-H2_2, 自定义 |
| `employee_id` | VARCHAR(100) | 工号 (operator) |
| `test_name` | VARCHAR(200) | 测试名称 |
| `notes` | TEXT | 备注 |
| `work_order` | VARCHAR(50) | 工单号 |

**Result fields**:

| Column | Type | Notes |
|--------|------|-------|
| `result_data` | TEXT | JSON: `{time:[], pressure:[], ...}` from ML model |
| `chart_image` | VARCHAR(255) | Path to generated chart (optional) |
| `created_at` | DATETIME | Auto |

---

### 3. `test_result`

Stores an uploaded experiment file and its parsed PT data. Linked to a `simulation` via
`simulation_id` to enable recipe-aware PT comparison.

| Column | Type | Notes |
|--------|------|-------|
| `id` | INTEGER PK | Auto-increment |
| `user_id` | INTEGER FK | **Who uploaded** (always recorded, cross-user) |
| `simulation_id` | INTEGER FK NULLABLE | Linked simulation (recipe context) |
| `filename` | VARCHAR(255) | Secure filename |
| `file_path` | VARCHAR(500) | Absolute path on disk |
| `data` | TEXT | JSON: `{"time": [...], "pressure": [...]}` |
| `uploaded_at` | DATETIME | Auto |

---

## Key Design Decisions

### Recipe Deduplication (Lab-Wide)
Recipes are a physical concept — the same 11 parameters always produce the same simulation
result. Instead of one record per user per run, the system maintains **one record per unique
recipe** across all users:

```python
# In SimulationService.run_forward_simulation():
existing = self._build_recipe_query(params).first()  # cross-user query
if existing and existing.result_data:
    return {'simulation_id': existing.id, 'data': ...}  # reuse
# else: run ML model and persist new record
```

### Cross-User PT Comparison
When displaying PT曲线对比, **all test results linked to any simulation with the matching recipe
are pooled** — regardless of which user uploaded them. This gives better statistics and reflects
the shared-lab nature of the data.

### File Attribution
Even though recipe data is shared, `TestResult.user_id` always records the individual who
uploaded that specific file. This provides a complete audit trail.

### PT Data Storage (JSON in `test_result.data`)
Test data is stored as a JSON blob in `test_result.data`:
```json
{"time": [0, 0.01, 0.02, ...], "pressure": [0.0, 0.12, 0.45, ...]}
```
Typical row count: ~4000 points per file.

> **Future migration note**: For large-scale deployments, consider splitting this into a
> `test_time_series` table (one row per point) for efficient SQL filtering and pagination.
> See `DATABASE_SCHEMA_VISUALIZATION.md` for the full normalized design.

---

## Current Database State (2026-03-02)

| Table | Records |
|-------|---------|
| `user` | 3 (admin, 123, 321) |
| `simulation` | 3 |
| `test_result` | 4 |

### Simulations
| id | user_id | Recipe summary | created_at |
|----|---------|----------------|------------|
| 1 | 2 | ignition=135, nc1=B/750mg, shell=22, current=1.2, sensor=200, body=10-892 | 2026-03-02 18:43 |
| 2 | 2 | ignition=135, nc1=B/775mg, shell=22, current=1.2, sensor=200, body=10-892 | 2026-03-02 18:44 |
| 3 | 2 | ignition=135, nc1=B/810mg, shell=22, current=1.2, sensor=200, body=10-892 | 2026-03-02 18:46 |

### Test Results
| id | user_id | sim_id | filename | rows | uploaded_at |
|----|---------|--------|----------|------|-------------|
| 1 | 2 | None | 59_1_avg.xlsx | 4000 | 2026-03-02 18:43 |
| 2 | 2 | 1 | 59_2_avg.xlsx | 4000 | 2026-03-02 18:44 |
| 3 | 2 | 2 | 59_3_avg.xlsx | 4000 | 2026-03-02 18:46 |
| 4 | 2 | 3 | 59_4_avg.xlsx | 4000 | 2026-03-02 18:47 |

> Note: `test_result id=1` has `sim_id=None` because it was uploaded before the
> two-step validation flow was implemented (pre-dates the simulation_id link feature).

---

## Quick Query Reference

```python
# All simulations
Simulation.query.order_by(Simulation.created_at.desc()).all()

# All test results with their simulation recipe
TestResult.query.join(Simulation, TestResult.simulation_id == Simulation.id).all()

# Find all test results for a recipe (cross-user)
# Uses SimulationService._build_recipe_query(params).all() then
# TestResult.query.filter(TestResult.simulation_id.in_(sim_ids))

# Who uploaded what
TestResult.query.filter_by(user_id=user_id).all()
```

---

## File Locations

| Item | Path |
|------|------|
| SQLite database | `instance/app.db` |
| SQLAlchemy models | `app/models.py` |
| SimulationService | `app/services/simulation_service.py` |
| FileService | `app/services/file_service.py` |
| Uploaded files | `instance/uploads/` |
| Temp files | `instance/temp/` |
