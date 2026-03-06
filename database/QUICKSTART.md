# Database Quickstart — MGG_SYS

**Get up and running in 5 minutes.**

All examples use the live application models (`app/models.py`). Run snippets inside a Flask application context.

---

## Setup

```bash
# Install dependencies
pip install -r requirements.txt

# Run once to auto-create tables and seed admin
python run.py
```

On first start the database is created at `instance/simulation_system.db` with:
- All 3 tables (`user`, `simulation`, `test_result`)
- WAL mode enabled (SQLite)
- Default admin account (`admin` / `admin123` or `$ADMIN_PASSWORD`)

---

## Common Tasks

### Create a user (via Admin Panel or directly)

**Web interface:** Admin Panel → Add User

**Programmatic:**
```python
from app import create_app, db
from app.models import User
from flask_bcrypt import Bcrypt

app = create_app()
bcrypt = Bcrypt(app)

with app.app_context():
    user = User(
        employee_id='E12345',
        username='Zhang San',
        role='research_engineer',   # admin | research_engineer | lab_engineer
        phone='13800138000',
        is_active=True,
    )
    user.password_hash = bcrypt.generate_password_hash('SecurePass1!').decode('utf-8')
    db.session.add(user)
    db.session.commit()
    print(f'Created user id={user.id}')
```

---

### Query simulations

```python
from app.models import Simulation

with app.app_context():
    # All simulations, newest first
    sims = Simulation.query.order_by(Simulation.created_at.desc()).all()

    # Find by work order
    sims = Simulation.query.filter_by(work_order='WO-2026-001').all()

    # Find by recipe (dedup check — matches SimulationService logic)
    sim = Simulation.query.filter_by(
        ignition_model='135',
        nc_type_1='B',
        nc_usage_1=750.0,
        nc_type_2='无',
        nc_usage_2=0.0,
        gp_type='D',
        gp_usage=100.0,
        shell_model='22',
        current=1.2,
        sensor_model='200',
        body_model='10-892',
    ).first()
```

---

### Query test results

```python
from app.models import TestResult
import json

with app.app_context():
    # All uploads by a user
    results = TestResult.query.filter_by(user_id=1).all()

    # All results linked to a work order
    from app.models import Simulation
    sims = Simulation.query.filter_by(work_order='WO-2026-001').all()
    sim_ids = [s.id for s in sims]
    results = TestResult.query.filter(
        TestResult.simulation_id.in_(sim_ids)
    ).order_by(TestResult.uploaded_at.desc()).all()

    # Parse PT data from a result
    for r in results:
        data = json.loads(r.data)
        time = data['time']           # list of floats (ms)
        pressure = data['pressure']   # list of floats (MPa)
        print(f'{r.filename}: {len(time)} points, peak={max(pressure):.2f} MPa')
```

---

### Backup database

```python
from app import create_app
from database.manager import backup_database

app = create_app()
with app.app_context():
    path = backup_database(app)
    print(f'Backup saved to: {path}')
# → instance/backups/simulation_system_20260306_120000.db
```

---

### Reset database (destructive — deletes ALL data)

```python
from app import create_app
from database.manager import reset_database

app = create_app()
with app.app_context():
    reset_database(app)
    # Tables dropped and recreated; default admin re-seeded
```

---

### Inspect schema (SQLite)

```bash
sqlite3 instance/simulation_system.db ".schema"
sqlite3 instance/simulation_system.db "SELECT * FROM user;"
sqlite3 instance/simulation_system.db "SELECT count(*) FROM test_result;"
```

---

## Troubleshooting

| Error | Fix |
|-------|-----|
| `No module named 'app'` | Run from the project root: `cd /path/to/MGG_SYS` |
| `No such table: user` | Run `python run.py` once to trigger `db.create_all()` |
| `Database is locked` | WAL mode is auto-enabled; reduce concurrent writers or migrate to PostgreSQL |
| `OperationalError: unable to open database` | Ensure `instance/` directory exists and is writable |

---

## Learn More

- Full schema reference: `database/README.md`
- PostgreSQL migration: `database/SETUP.md`
- Future normalized schema: `database/DATABASE_SCHEMA_VISUALIZATION.md`
- Regression tests: `python database/database_regression_test.py`
