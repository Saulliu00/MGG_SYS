# MGG Simulation System

**Gas Generator Simulation and Analysis Platform**
**Branch:** `db-optimized`
**Last Updated:** 2026-03-02

---

## Overview

MGG_SYS is a web-based platform for gas generator simulation, experimental data management, and statistical analysis. It supports forward/reverse simulation, PT curve comparison, and work order tracking across a multi-user lab environment.

---

## Features

### 1. 正向仿真 (Forward Simulation) — 研发工程师
- Input recipe parameters (ignition model, NC type/usage, GP type/usage, shell, current, sensor, volume, equipment)
- Run ML-based pressure-time simulation
- View PT curve result with Plotly chart
- **Recipe deduplication:** if an identical recipe already exists in the database (any user), the stored result is returned instantly without re-running inference

### 2. PT 曲线对比 (PT Curve Comparison) — 研发工程师
- Upload experimental `.xlsx` test data (two-column format: time ms, pressure MPa)
- Two-step validation before committing to database
- Overlay simulated vs experimental PT curves
- **Cross-user data pooling:** test data from all users with the same recipe is averaged for comparison

### 3. 逆向仿真 (Reverse Simulation) — 研发工程师
- Input target peak pressure to predict NC usage
- ML-based reverse inference

### 4. 工单查询 (Work Order Query) — 研发工程师
Three-column interface for browsing all work orders in the lab:

| Column | Content |
|--------|---------|
| Left | All work orders with real-time search filter |
| Middle | PT curves — all experimental runs for the selected work order overlaid on one chart, one colour per run |
| Right | Statistical summary: peak pressure and peak time per run, plus mean / std / CV across runs when multiple runs exist |

**Access control:**
- All 研发工程师 users can read all work orders (lab-wide visibility)
- Each user can only delete their own test result records (identified by `TestResult.user_id`)

### 5. 实验记录 (Experiment History) — 实验室工程师
- View uploaded experiment file history

### 6. 管理员 (Admin Panel) — admin
- User management: create, edit, activate/deactivate, force logout
- Role assignment: `admin`, `research_engineer`, `lab_engineer`

---

## User Roles

| Role | 正向仿真 | PT 曲线对比 | 逆向仿真 | 工单查询 | 实验记录 | 管理员 |
|------|---------|------------|---------|---------|---------|--------|
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
export SECRET_KEY=$(python -c "import secrets; print(secrets.token_hex(32))")
# Optional — set your own admin password:
export ADMIN_PASSWORD=your_secure_password
```

### 3. Run
```bash
python run.py
```
The server starts on `http://0.0.0.0:5000` (accessible on the local network).
On first launch, a default admin account is created and the password is printed to the console.

---

## Project Structure

```
MGG_SYS/
├── app/
│   ├── __init__.py              # App factory, service wiring, blueprint registration
│   ├── models.py                # SQLAlchemy models (User, Simulation, TestResult)
│   ├── routes/
│   │   ├── auth.py              # Login / logout
│   │   ├── main.py              # Home page
│   │   ├── admin.py             # Admin panel
│   │   ├── simulation.py        # Forward/reverse simulation, upload
│   │   └── work_order.py        # 工单查询 API endpoints
│   ├── services/
│   │   ├── simulation_service.py  # Forward sim, recipe dedup, reverse prediction
│   │   ├── file_service.py        # Excel upload, validation, storage
│   │   ├── comparison_service.py  # PT comparison, peak detection
│   │   └── work_order_service.py  # Work order list, detail, statistics, delete
│   ├── utils/
│   │   ├── decorators.py        # research_required, lab_required role guards
│   │   ├── plotter.py           # Plotly chart generation (single/comparison/multi-run)
│   │   ├── file_handler.py      # Excel parsing and validation
│   │   └── ...
│   ├── templates/
│   │   ├── base.html
│   │   ├── simulation/          # index.html (正向), reverse.html (逆向)
│   │   └── work_order/          # index.html (工单查询)
│   ├── static/
│   │   ├── css/style.css
│   │   └── js/
│   │       ├── simulation.js    # 正向仿真 frontend
│   │       └── work_order.js    # 工单查询 frontend
│   └── config/
│       ├── plot_config.py       # Plotly layout/colour constants
│       └── network_config.py    # CORS, session, rate-limit settings
│
├── database/
│   └── README.md                # Database schema documentation
│
├── instance/
│   └── simulation_system.db     # SQLite database (auto-created)
│
├── run.py                       # Entry point
└── requirements.txt
```

---

## Database Schema

Three tables power the application (see [`database/README.md`](database/README.md) for full detail):

### `user`
Stores credentials and role. Roles: `admin`, `research_engineer`, `lab_engineer`.

### `simulation`
One row per recipe run. Stores all recipe parameters inline alongside the work order number and JSON-encoded simulation result.

| Key fields | Description |
|-----------|-------------|
| `work_order` | Work order number string (links to 工单查询) |
| `ignition_model`, `nc_type_1`, `nc_usage_1`, … | Recipe parameters |
| `result_data` | JSON: `{time: [...], pressure: [...]}` from simulation |

**Recipe deduplication:** before running the ML model, `SimulationService` queries for an existing simulation with identical recipe parameters (all users). If found, the stored result is returned.

### `test_result`
One row per uploaded `.xlsx` file. Stores the parsed data as JSON and links back to a simulation (and therefore a work order).

| Key fields | Description |
|-----------|-------------|
| `simulation_id` | FK → `simulation.id` (connects the run to a work order) |
| `user_id` | Who uploaded the file (governs delete permission) |
| `filename`, `file_path` | Original filename and disk path |
| `data` | JSON: `{time: [...], pressure: [...]}` from the xlsx |

---

## 工单查询 — Technical Notes

**Backend (`WorkOrderService`):**
- `get_all_work_orders()` — returns all simulations with a non-empty `work_order`, newest first, with a recipe summary string
- `get_work_order_detail(work_order)` — finds **all** simulations sharing the same work_order string, collects all their linked test results, builds a multi-run Plotly chart and computes statistics
- `_compute_statistics(datasets, labels)` — per-run peak pressure/time via `ComparisonService.find_peak_pressure()`, then NumPy mean/std (ddof=1)/CV
- `delete_test_result(id, user_id)` — only deletes if `TestResult.user_id == user_id`; also removes the file from disk

**Frontend (`work_order.js`):**
- On page load: renders empty chart axes (no placeholder text)
- On work order click: fetches `/work_order/<wo>/detail`, calls `Plotly.newPlot` with server-rendered traces, renders statistics table
- Client-side search filter on the work order list (no extra round-trips)
- All user-controlled data escaped via `_escapeHtml()` / `JSON.stringify()` before DOM insertion

---

## Uploading Test Data (`.xlsx` Format)

Files must be exactly two columns, no required header:

| Column A | Column B |
|----------|----------|
| Time (ms) | Pressure (MPa) |
| 0.000 | 0.012 |
| 0.005 | 0.024 |
| … | … |

Rules enforced at upload:
- Exactly 2 columns
- First time value ≤ 1.0 ms (must start near zero)
- Time column monotonically non-decreasing
- At least 2 numeric rows

---

## Security

| Feature | Implementation |
|---------|---------------|
| Password hashing | Flask-Bcrypt |
| Session management | Flask-Login with session token invalidation |
| CSRF protection | Flask-WTF on all state-changing requests |
| Role-based access | `@research_required` / `@lab_required` decorators |
| XSS prevention | `_escapeHtml()` + `JSON.stringify` for all user data in DOM |
| Rate limiting | Flask-Limiter |
| SQL injection | SQLAlchemy ORM (parameterised queries) |

---

## Troubleshooting

**No plot appears in 工单查询 after clicking a work order**
Ensure the uploaded test result has a `simulation_id` that points to a simulation with the matching `work_order`. Test results uploaded without linking to a simulation will not appear.

**"Database is locked" on SQLite**
Increase the connection pool settings in `app/__init__.py`, or migrate to PostgreSQL for production workloads above ~20 concurrent users.

**SECRET_KEY not set**
The app refuses to start without `SECRET_KEY` set as an environment variable. Run:
```bash
export SECRET_KEY=$(python -c "import secrets; print(secrets.token_hex(32))")
```

---

## Contact

- **Email:** saul.liu00@gmail.com
- **Issues:** GitHub Issues
