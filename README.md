# MGG Simulation System

**Gas Generator Simulation and Analysis Platform**
**Branch:** `db-optimized`
**Last Updated:** 2026-03-06

---

## Overview

MGG_SYS is a multi-user web platform for gas generator simulation, experimental data management, and statistical analysis. It supports forward/reverse ML-based simulation, PT curve comparison, work order tracking, and lab-wide data sharing across three user roles.

---

## Features

### 1. 正向仿真 (Forward Simulation) — 研发工程师
- Input recipe parameters (ignition model, NC type/usage, GP type/usage, shell, current, sensor, volume)
- Run ML-based pressure-time simulation
- View PT curve in an interactive Plotly chart
- **Lab-wide recipe deduplication:** if an identical recipe already exists (any user), the cached result is returned instantly — no redundant ML inference

### 2. PT 曲线对比 (PT Curve Comparison) — 研发工程师
- Upload experimental `.xlsx` test data (two-column: time ms, pressure MPa)
- Two-step file validation before committing to the database
- Overlay simulated vs experimental PT curves on one chart
- Comparison metrics: RMSE, Pearson correlation, peak pressure/time differences
- **Cross-user data pooling:** all uploads sharing the same recipe are averaged for comparison

### 3. 逆向仿真 (Reverse Simulation) — 研发工程师
- Input target peak pressure to predict NC usage
- ML-based reverse inference

### 4. 工单查询 (Work Order Query) — 研发工程师

Three-column interface for browsing all work orders lab-wide:

| Column | Content |
|--------|---------|
| Left | Searchable work order list (real-time client-side filter) |
| Middle | PT curves — all experimental runs for the selected work order overlaid, one colour per run |
| Right | Statistics: peak pressure and peak time per run; mean / std / CV across runs |

**Access control:**
- All 研发工程师 users can view all work orders (lab-wide read access)
- Each user can only delete their own uploaded test results (`TestResult.user_id`)
- Admin can delete any test result or entire work order

### 5. 实验记录 (Experiment History) — 实验室工程师
- View uploaded experiment file history
- Batch-upload multiple `.xlsx` files linked to a work order ticket

### 6. 管理员 (Admin Panel) — admin
- **User management:** create, activate/deactivate, delete, reset password, force logout
- **Role assignment:** `admin`, `research_engineer`, `lab_engineer`
- **System logs:** view, filter, and download JSON-formatted audit logs
- **System monitor:** real-time CPU, memory, disk, and database status

---

## User Roles

| Role | 正向仿真 | PT对比 | 逆向仿真 | 工单查询 | 实验记录 | 管理员 |
|------|---------|--------|---------|---------|---------|--------|
| `admin` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| `research_engineer` | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ |
| `lab_engineer` | ❌ | ❌ | ❌ | ❌ | ✅ | ❌ |

---

## Quick Start

### 1. Clone & Setup
```bash
git clone https://github.com/Saulliu00/MGG_SYS.git
cd MGG_SYS
git checkout db-optimized

python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Set Environment Variables
```bash
# Required
export SECRET_KEY=$(python -c "import secrets; print(secrets.token_hex(32))")

# Optional — custom admin password (default: admin123)
export ADMIN_PASSWORD=your_secure_password
```

### 3. Run (Development)
```bash
python run.py
```

The server starts on `http://0.0.0.0:5001` (accessible on the local network).
On first launch, a default admin account is created and its credentials are printed to the console.

**Default login:**
```
Employee ID: admin
Password:    admin123   (or value of ADMIN_PASSWORD)
```

### 4. Run (Production)
```bash
export SECRET_KEY=<your-secret-key>
export ADMIN_PASSWORD=<secure-password>
gunicorn -c gunicorn.conf.py "app:create_app()"
```

Gunicorn starts 5 workers × 5 threads each (25 concurrent handlers), bound to `0.0.0.0:5001`.

---

## Project Structure

```
MGG_SYS/
├── app/
│   ├── __init__.py              # App factory — extensions, services, blueprints
│   ├── models.py                # SQLAlchemy models: User, Simulation, TestResult
│   ├── routes/
│   │   ├── auth.py              # Login, logout, registration, settings
│   │   ├── main.py              # Home redirect, /health
│   │   ├── admin.py             # User management, logs, system monitor
│   │   ├── simulation.py        # Forward/reverse simulation, file upload, history
│   │   └── work_order.py        # 工单查询 — list, detail, delete
│   ├── services/
│   │   ├── simulation_service.py  # Forward sim, recipe dedup, reverse prediction
│   │   ├── file_service.py        # File validation, Excel parsing, storage
│   │   ├── comparison_service.py  # PT analysis, peak detection, RMSE/correlation
│   │   └── work_order_service.py  # Work order queries, statistics, deletion
│   ├── utils/
│   │   ├── decorators.py        # @research_required, @lab_required role guards
│   │   ├── plotter.py           # Plotly chart generation (single/comparison/multi-run)
│   │   ├── file_handler.py      # Excel parsing and validation
│   │   ├── model_runner.py      # ML inference wrapper (path-traversal hardened)
│   │   ├── subprocess_runner.py # Python subprocess execution with timeout
│   │   ├── log_manager.py       # File-based JSON logging
│   │   ├── system_monitor.py    # CPU, memory, disk metrics (SQL-whitelist hardened)
│   │   ├── validators.py        # Input validation helpers
│   │   ├── errors.py            # Custom exception hierarchy
│   │   └── paths.py             # Directory path utilities
│   ├── middleware/
│   │   ├── timeout.py           # Per-request timeouts (30s default, 120s for simulation)
│   │   └── logging_middleware.py # Request/response audit logging
│   ├── config/
│   │   ├── constants.py         # Error/success messages, timeouts, file limits
│   │   ├── plot_config.py       # Plotly colours, fonts, legend position
│   │   └── network_config.py    # CORS, session, worker, pool settings
│   ├── templates/
│   │   ├── base.html
│   │   ├── auth/
│   │   ├── admin/
│   │   ├── simulation/          # index.html (正向), reverse.html (逆向), history.html
│   │   └── work_order/          # index.html (工单查询)
│   └── static/
│       ├── css/style.css
│       └── js/
│           ├── simulation.js    # 正向仿真 frontend
│           └── work_order.js    # 工单查询 frontend (XSS-safe via _escapeHtml)
│
├── database/
│   ├── README.md                # Current schema documentation
│   ├── SETUP.md                 # PostgreSQL migration guide
│   ├── QUICKSTART.md            # Quick operations reference
│   ├── manager.py               # init_database(), backup_database(), reset_database()
│   ├── models.py                # Future normalized schema (migration target)
│   └── database_regression_test.py  # Database-layer regression tests
│
├── instance/
│   └── simulation_system.db    # SQLite database (auto-created on first run)
│
├── run.py                       # Development entry point (Flask dev server)
├── gunicorn.conf.py             # Production Gunicorn configuration
├── config.py                    # Flask environment configs (Development/Production)
├── requirements.txt             # Python dependencies
├── app_regression_test.py       # App-layer regression tests (services + routes)
└── load_test.py                 # Concurrent load test (configurable via CLI args)
```

---

## Database Schema

Three tables power the application. See [`database/README.md`](database/README.md) for full column-level detail.

### `user`
Stores credentials and role assignment.

| Column | Description |
|--------|-------------|
| `employee_id` | Login credential (工号), unique |
| `username` | Display name |
| `password_hash` | Bcrypt hash |
| `role` | `admin` \| `research_engineer` \| `lab_engineer` |
| `phone` | Contact number (optional) |
| `is_active` | Account enabled flag |
| `session_token` | Used for admin force-logout |
| `last_seen_at` | Throttled update (at most once per minute) |

### `simulation`
One record per **unique recipe** (lab-wide). All 11 recipe fields together define uniqueness; a second user running the same recipe retrieves the existing record.

| Key fields | Description |
|-----------|-------------|
| `work_order` | Work order number string (links to 工单查询) |
| `ignition_model`, `nc_type_1/2`, `nc_usage_1/2`, … | 11 recipe parameters |
| `result_data` | JSON: `{time: [...], pressure: [...]}` from ML model |

### `test_result`
One record per uploaded `.xlsx` file.

| Key fields | Description |
|-----------|-------------|
| `simulation_id` | FK → `simulation.id` (nullable — links run to a work order) |
| `user_id` | Who uploaded (always recorded; governs delete permission) |
| `filename`, `file_path` | Secure filename and absolute disk path |
| `data` | JSON: `{time: [...], pressure: [...]}` parsed from the xlsx |

---

## API Endpoints

### Auth (`/auth`)
| Method | Path | Description |
|--------|------|-------------|
| GET/POST | `/auth/login` | Login (rate-limited: 10/min) |
| GET | `/auth/logout` | Clear session |
| GET/POST | `/auth/register` | Self-service registration |
| GET/POST | `/auth/settings` | Profile & password update |

### Simulation (`/simulation`)
| Method | Path | Role | Description |
|--------|------|------|-------------|
| GET | `/simulation/` | research | Forward simulation page |
| GET | `/simulation/reverse` | research | Reverse simulation page |
| POST | `/simulation/run` | Any | Run forward simulation |
| POST | `/simulation/upload` | Any | Upload test result (.xlsx) |
| GET | `/simulation/history` | lab | Experiment file history |
| POST | `/simulation/experiment` | lab | Batch experiment upload |
| POST | `/simulation/predict` | Any | Reverse prediction |
| POST | `/simulation/validate_upload` | Any | Validate file without saving |
| POST | `/simulation/fetch_recipe_test_data` | Any | Fetch averaged test data for recipe |
| POST | `/simulation/generate_comparison_chart` | Any | Generate comparison chart |

### Work Order (`/work_order`)
| Method | Path | Description |
|--------|------|-------------|
| GET | `/work_order/` | 工单查询 page |
| GET | `/work_order/list` | All work orders (JSON) |
| GET | `/work_order/<wo>/detail` | Chart + statistics + files for one work order |
| DELETE | `/work_order/test_result/<id>` | Delete test result (own or admin) |
| DELETE | `/work_order/<wo>` | Delete entire work order (creator or admin) |

### Admin (`/admin`)
| Method | Path | Description |
|--------|------|-------------|
| GET | `/admin/` | User management dashboard |
| POST | `/admin/user/add` | Create user |
| POST | `/admin/user/<id>/toggle` | Activate/deactivate |
| POST | `/admin/user/<id>/delete` | Delete user |
| POST | `/admin/user/<id>/reset-password` | Reset password |
| POST | `/admin/user/<id>/kick` | Force logout |
| GET | `/admin/logs` | Logs viewer page |
| GET | `/admin/logs/view` | Log entries (JSON) |
| GET | `/admin/logs/download/<file>` | Download log file |
| GET | `/admin/monitor` | System health dashboard |
| GET | `/admin/monitor/data` | Live system metrics (JSON) |

### Misc
| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/` | Yes | Home (role-based redirect) |
| GET | `/health` | No | Health check (DB + filesystem) |

---

## Uploading Test Data (`.xlsx` Format)

Files must have exactly two columns:

| Column A | Column B |
|----------|----------|
| Time (ms) | Pressure (MPa) |
| 0.000 | 0.012 |
| 0.005 | 0.024 |
| … | … |

Validation rules enforced at upload:
- Exactly 2 columns
- First time value ≤ 1.0 ms (must start near zero)
- Time column monotonically non-decreasing
- At least 2 numeric rows

---

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `SECRET_KEY` | *(required)* | Flask session signing key |
| `ADMIN_PASSWORD` | `admin123` | Default admin account password |
| `DATABASE_URL` | SQLite (`instance/simulation_system.db`) | SQLAlchemy database URL |
| `FLASK_DEBUG` | `false` | Enable debug mode (dev only) |
| `CORS_ORIGINS` | `*` | Allowed CORS origins |

### Connection Pool (production)
Configured in `app/config/network_config.py`:
- `pool_size=25`, `max_overflow=25`, `pool_timeout=10s`, `pool_recycle=3600s`

---

## Security

| Feature | Implementation |
|---------|---------------|
| Password hashing | Flask-Bcrypt |
| Session management | Flask-Login with session token invalidation |
| CSRF protection | Flask-WTF globally enforced on all state-changing requests |
| Role-based access | `@research_required` / `@lab_required` decorators |
| XSS prevention | `_escapeHtml()` + `JSON.stringify` for all user data in DOM |
| Rate limiting | Flask-Limiter (10 req/min on `/auth/login`) |
| SQL injection | SQLAlchemy ORM (parameterised queries throughout) |
| SQL whitelist | Table names in system_monitor validated against a hardcoded whitelist |
| Path traversal | `os.path.realpath()` guard on ML model file loading |
| Daily re-login | Sessions invalidated at midnight (users must re-authenticate each day) |
| Force logout | Admin can invalidate any user's session via session_token=NULL |
| URL parameter validation | Work order strings validated against `^[\w\-]{1,100}$` regex |
| Audit logging | All admin actions (add/delete/reset/kick) written to structured logs |

---

## Testing

### App-layer regression tests
```bash
python app_regression_test.py
```
Covers: ComparisonService, Plotter, WorkOrderService (including delete permissions), work order URL validation, and Flask routes — all against an isolated in-memory SQLite database.

### Database-layer regression tests
```bash
python database/database_regression_test.py
```
Covers: all 3 ORM models, relationships, constraints, WAL mode, backup, `reset_database()`, and seeded data integrity.

### Load test (requires running server)
```bash
# Basic (100 users, localhost:5001)
python load_test.py

# Custom
python load_test.py --url http://192.168.1.100:5001 --users 50 --employee-id admin --password secret
```

---

## Troubleshooting

**No chart appears in 工单查询 after clicking a work order**
The test result must have a `simulation_id` pointing to a `Simulation` with the matching `work_order` string. Files uploaded without a work order/simulation link will not appear. Use the work order field when uploading.

**"Database is locked" on SQLite**
Increase the connection pool settings in `app/config/network_config.py`, or migrate to PostgreSQL for workloads above ~20 concurrent users.

**SECRET_KEY not set**
The app refuses to start without `SECRET_KEY`:
```bash
export SECRET_KEY=$(python -c "import secrets; print(secrets.token_hex(32))")
```

**Admin password forgotten**
Set `ADMIN_PASSWORD` env var and restart — the admin account is re-seeded on startup if the default admin does not exist. If the account already exists with a different password, use `database/manager.py` → `reset_database()` (destructive) or update via the `User` model directly.

**Login succeeds but redirects back to login**
The daily re-login check may have failed. Clear browser cookies and log in again.

---

## Contact

- **Email:** saul.liu00@gmail.com
- **Issues:** [GitHub Issues](https://github.com/Saulliu00/MGG_SYS/issues)
