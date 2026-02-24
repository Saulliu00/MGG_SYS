## Quickstart Guide - MGG Database

**Get up and running in 5 minutes.**

---

## 🚀 Quick Setup

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Initialize Database
```python
from app import create_app
from database.manager import init_database

app = create_app()
init_database(app)
```

**That's it!** The database is created with:
- ✅ All tables
- ✅ Indexes
- ✅ Default admin user (`admin/admin123`)
- ✅ 2 example recipes
- ✅ WAL mode enabled (SQLite)

---

## 📝 Common Tasks

### Create a User
```python
from database.models import User
from database.extensions import db

user = User(
    username='John Doe',
    employee_id='E12345',
    email='john@example.com',
    role='research_engineer',
    department='R&D'
)
user.set_password('secure_password')
db.session.add(user)
db.session.commit()
```

### Create a Recipe
```python
from database.models import Recipe

recipe = Recipe(
    user_id=user.id,
    recipe_name='Test Config #1',
    ignition_model='Type-A',
    nc_type_1='NC-Standard',
    nc_usage_1=20.0,
    gp_type='GP-Alpha',
    gp_usage=15.0,
    shell_model='Shell-100mm',
    current_condition='5A',
    sensor_range='0-10MPa',
    body_model='50cc',
    equipment='Tester-01'
)
db.session.add(recipe)
db.session.commit()
```

### Run a Simulation
```python
from database.models import Simulation, SimulationTimeSeries, WorkOrder

# 1. Create work order
wo = WorkOrder(
    work_order_number='WO-001',
    recipe_id=recipe.id,
    user_id=user.id,
    test_name='Baseline Test'
)
db.session.add(wo)
db.session.flush()

# 2. Run simulation (your simulation code here)
pt_data = [(0.0, 0.0), (10.0, 2.5), (20.0, 5.0), ...]  # Your simulation results

# 3. Save simulation
sim = Simulation(
    user_id=user.id,
    work_order_id=wo.id,
    test_name='Run #1',
    peak_pressure=max(p[1] for p in pt_data),
    num_data_points=len(pt_data),
    status='completed'
)
db.session.add(sim)
db.session.flush()

# 4. Save time series
for i, (time, pressure) in enumerate(pt_data):
    point = SimulationTimeSeries(
        simulation_id=sim.id,
        time_point=time,
        pressure=pressure,
        sequence_number=i + 1
    )
    db.session.add(point)

db.session.commit()
```

### Query Data
```python
# Get all simulations for a user
sims = Simulation.query.filter_by(user_id=user.id).all()

# Get time series for a simulation
points = SimulationTimeSeries.query.filter_by(simulation_id=sim.id).all()

# Get recent work orders
recent_wo = WorkOrder.query.order_by(WorkOrder.created_at.desc()).limit(10).all()

# Find simulations by peak pressure
high_pressure = Simulation.query.filter(Simulation.peak_pressure > 8.0).all()
```

---

## 🔧 Maintenance

### Backup Database
```python
from database.manager import backup_database

backup_path = backup_database(app)
print(f'Backup: {backup_path}')
```

### Reset Database (⚠️ Deletes all data!)
```python
from database.manager import reset_database

reset_database(app)  # Fresh start
```

### Check Schema
```bash
sqlite3 instance/mgg.db ".schema"
```

---

## 📚 Learn More

- Full documentation: `database/README.md`
- Schema visualization: `database/schema.sql`
- Model reference: `database/models.py`

---

## 🐛 Common Issues

### "No module named 'database'"
```bash
# Make sure you're in the project root:
cd /path/to/MGG_SYS
python your_script.py
```

### "Database is locked"
- Enable WAL mode (automatic on init)
- Or close other connections to the database

### "No such table: user"
```python
# Run initialization:
from database.manager import init_database
init_database(app)
```

---

**Need help?** Check `database/README.md` for detailed examples.
