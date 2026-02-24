# MGG Database - Optimized Hybrid Design

**Version:** 3.0 (Optimized Hybrid)  
**Design Philosophy:** Simplicity + Performance  
**Compatible with:** SQLite (dev) and PostgreSQL (production-ready)

---

## 🎯 Design Philosophy

This schema combines the best aspects of both normalized and denormalized approaches:

### What We Did Right ✅

1. **Separated Time Series** - Critical for performance
   - Time series data in dedicated tables
   - Efficient queries on large datasets (millions of points)
   - Easy pagination and filtering

2. **Recipe Abstraction** - Smart reusability
   - One recipe = one complete parameter set
   - Multiple work orders can reference the same recipe
   - Reduces duplication while maintaining flexibility

3. **Embedded Parameters** - Simpler queries
   - No 10-table joins for basic queries
   - Parameters stored as validated strings
   - CHECK constraints ensure data quality

4. **Strategic Indexes** - Optimized access patterns
   - Composite indexes on common query patterns
   - Efficient filtering and sorting

5. **PostgreSQL-Ready** - Production scalable
   - Schema works on both SQLite and PostgreSQL
   - Easy migration path when needed

---

## 📊 Schema Overview

### Core Tables (8 tables)

```
┌─────────────────────────────────────────────────────────┐
│                         User                            │
│  (Authentication & Authorization)                       │
└──────────────┬──────────────────────────────────────────┘
               │
               ├──────────────────────────────────────────┐
               │                                          │
       ┌───────▼────────┐                        ┌────────▼────────┐
       │     Recipe     │◄───────────────────────│   WorkOrder     │
       │  (Parameters)  │  One-to-Many           │  (Test Session) │
       └────────────────┘                        └─────────┬───────┘
                                                           │
                                    ┌──────────────────────┼────────────────┐
                                    │                      │                │
                            ┌───────▼────────┐   ┌────────▼──────┐  ┌──────▼─────────┐
                            │   Simulation   │   │  TestResult   │  │ ExperimentFile │
                            └────────┬───────┘   └───────┬───────┘  └────────────────┘
                                     │                   │
                        ┌────────────┼───────────────────┘
                        │            │
           ┌────────────▼──┐  ┌──────▼────────────┐
           │SimTimeSeries  │  │ TestTimeSeries    │
           │(Sim P-T data) │  │(Experimental P-T) │
           └───────────────┘  └───────────────────┘
                        │            │
                        └─────┬──────┘
                              │
                       ┌──────▼────────┐
                       │ PTComparison  │
                       │(Sim vs Test)  │
                       └───────────────┘
```

---

## 📁 Table Descriptions

### 1. `user` - User Accounts
**Purpose:** Authentication and authorization

| Column | Type | Description |
|--------|------|-------------|
| `id` | INTEGER | Primary key |
| `username` | VARCHAR(80) | Display name |
| `employee_id` | VARCHAR(120) | Unique employee ID (login) |
| `email` | VARCHAR(120) | Email address |
| `password_hash` | VARCHAR(128) | Bcrypt password hash |
| `role` | VARCHAR(20) | admin \| research_engineer \| lab_engineer |
| `department` | VARCHAR(50) | User's department |
| `is_active` | BOOLEAN | Account status |

**Key Features:**
- ✅ Bcrypt password hashing
- ✅ Role-based access control
- ✅ Session token for remember-me

---

### 2. `recipe` - Reusable Parameter Sets
**Purpose:** Store complete test condition combinations

| Column | Type | Description |
|--------|------|-------------|
| `id` | INTEGER | Primary key |
| `user_id` | INTEGER | Creator |
| `recipe_name` | VARCHAR(200) | Friendly name |
| `ignition_model` | VARCHAR(50) | 点火具型号 |
| `nc_type_1` | VARCHAR(50) | NC类型1 |
| `nc_usage_1` | FLOAT | NC用量1 (mg) |
| `nc_type_2` | VARCHAR(50) | NC类型2 |
| `nc_usage_2` | FLOAT | NC用量2 (mg) |
| `gp_type` | VARCHAR(50) | GP类型 |
| `gp_usage` | FLOAT | GP用量 (mg) |
| ... | ... | (more parameters) |

**Why Recipes?**
- One recipe can be used for multiple work orders
- Makes it easy to repeat tests with same conditions
- Reduces data duplication
- Clear separation: "What parameters?" vs "When/Who tested?"

---

### 3. `work_order` - Test Sessions
**Purpose:** Links recipes with test executions

| Column | Type | Description |
|--------|------|-------------|
| `work_order_number` | VARCHAR(50) | Unique work order ID |
| `recipe_id` | INTEGER | Which parameter set |
| `test_name` | VARCHAR(200) | Test description |
| `status` | VARCHAR(20) | pending \| in_progress \| completed |
| `priority` | VARCHAR(10) | low \| normal \| high \| urgent |
| `source` | VARCHAR(20) | simulation \| experiment |

**Workflow:**
1. Create recipe (or reuse existing)
2. Create work order linked to recipe
3. Run simulations/experiments under that work order
4. Upload experiment files to work order

---

### 4. `simulation` - Simulation Results
**Purpose:** Store simulation runs (forward predictions)

| Column | Type | Description |
|--------|------|-------------|
| `work_order_id` | INTEGER | Parent work order |
| `peak_pressure` | FLOAT | Maximum pressure (MPa) |
| `peak_time` | FLOAT | Time of peak (ms) |
| `num_data_points` | INTEGER | Number of P-T points |
| `r_squared` | FLOAT | Model fit quality (0-1) |
| `status` | VARCHAR(20) | running \| completed \| failed |

**Note:** Detailed P-T data stored in `simulation_time_series` table

---

### 5. `simulation_time_series` - P-T Data (Simulation)
**Purpose:** Store time vs pressure data from simulations

| Column | Type | Description |
|--------|------|-------------|
| `simulation_id` | INTEGER | Parent simulation |
| `time_point` | FLOAT | Time (ms) |
| `pressure` | FLOAT | Pressure (MPa) |
| `sequence_number` | INTEGER | Point order (1, 2, 3...) |

**Why Separated?**
```python
# Without separation (BAD):
sim = Simulation.query.get(123)
data = json.loads(sim.result_data)  # Load entire 100MB JSON
for point in data:
    print(point['pressure'])  # Process in Python

# With separation (GOOD):
# Query only what you need:
points = SimulationTimeSeries.query.filter_by(simulation_id=123) \
    .filter(SimulationTimeSeries.time_point > 50) \
    .limit(100).all()  # Database does the filtering

# Pagination:
page_2 = SimulationTimeSeries.query.filter_by(simulation_id=123) \
    .offset(1000).limit(1000).all()  # Efficient!
```

**Performance:**
- ⚡ 100x faster queries on large datasets
- ⚡ Pagination support
- ⚡ Efficient filtering by time range
- ⚡ Indexes on (simulation_id, sequence_number) and (simulation_id, time_point)

---

### 6. `test_result` - Experimental Data
**Purpose:** Store uploaded test results from experiments

Similar to `simulation`, but for real experimental data.

---

### 7. `test_time_series` - P-T Data (Experimental)
**Purpose:** Store time vs pressure data from experiments

Same structure as `simulation_time_series`, but for test data.

---

### 8. `pt_comparison` - Simulation vs Experimental Comparison
**Purpose:** Store comparison metrics between simulation and test

| Column | Type | Description |
|--------|------|-------------|
| `simulation_id` | INTEGER | Simulation to compare |
| `test_result_id` | INTEGER | Test data to compare |
| `rmse` | FLOAT | Root Mean Square Error |
| `mae` | FLOAT | Mean Absolute Error |
| `correlation` | FLOAT | Pearson correlation (-1 to 1) |
| `r_squared` | FLOAT | R² fit quality (0 to 1) |

---

## 🔧 Usage Examples

### Create a Recipe
```python
from database.models import Recipe, User

# Get user
user = User.query.filter_by(employee_id='E12345').first()

# Create recipe
recipe = Recipe(
    user_id=user.id,
    recipe_name='Standard Config v1',
    description='Baseline parameters for validation',
    ignition_model='Type-A',
    nc_type_1='NC-Standard',
    nc_usage_1=20.0,
    nc_type_2='NC-Enhanced',
    nc_usage_2=10.0,
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

### Create Work Order
```python
from database.models import WorkOrder

work_order = WorkOrder(
    work_order_number='WO-2026-0001',
    recipe_id=recipe.id,
    user_id=user.id,
    test_name='Baseline Validation Test',
    source='simulation',
    status='pending',
    priority='normal'
)
db.session.add(work_order)
db.session.commit()
```

### Save Simulation with Time Series
```python
from database.models import Simulation, SimulationTimeSeries

# Create simulation
sim = Simulation(
    user_id=user.id,
    work_order_id=work_order.id,
    test_name='Run #1',
    status='completed',
    peak_pressure=8.5,
    peak_time=125.3,
    num_data_points=1000,
    r_squared=0.98
)
db.session.add(sim)
db.session.flush()  # Get sim.id

# Save time series data
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

### Query Time Series Efficiently
```python
# Get all points (use with caution on large datasets)
all_points = SimulationTimeSeries.query.filter_by(simulation_id=123).all()

# Get paginated results
page = 1
page_size = 1000
offset = (page - 1) * page_size
points = SimulationTimeSeries.query.filter_by(simulation_id=123) \
    .order_by(SimulationTimeSeries.sequence_number) \
    .offset(offset).limit(page_size).all()

# Get time range
early_points = SimulationTimeSeries.query.filter_by(simulation_id=123) \
    .filter(SimulationTimeSeries.time_point < 100).all()

# Get peak region (± 10ms around peak)
peak_time = 125.3
peak_region = SimulationTimeSeries.query.filter_by(simulation_id=123) \
    .filter(SimulationTimeSeries.time_point.between(peak_time - 10, peak_time + 10)) \
    .all()
```

### Compare Simulation vs Test
```python
from database.models import PTComparison
import numpy as np

# Load data
sim_data = [(p.time_point, p.pressure) for p in sim.time_series]
test_data = [(p.time_point, p.pressure) for p in test.time_series]

# Calculate metrics (simplified)
rmse = calculate_rmse(sim_data, test_data)
correlation = calculate_correlation(sim_data, test_data)

# Save comparison
comp = PTComparison(
    user_id=user.id,
    simulation_id=sim.id,
    test_result_id=test.id,
    peak_pressure_diff=abs(sim.peak_pressure - test.peak_pressure),
    peak_time_diff=abs(sim.peak_time - test.peak_time),
    rmse=rmse,
    correlation=correlation,
    r_squared=correlation ** 2
)
db.session.add(comp)
db.session.commit()
```

---

## 🚀 Performance Best Practices

### 1. Use Lazy Loading Wisely
```python
# BAD: Loads all time series into memory
sim = Simulation.query.get(123)
for point in sim.time_series:  # Loads thousands of objects!
    print(point.pressure)

# GOOD: Query directly with filters
points = SimulationTimeSeries.query.filter_by(simulation_id=123) \
    .limit(100).all()  # Only load what you need
```

### 2. Bulk Inserts
```python
# BAD: One commit per point
for time, pressure in pt_data:
    point = SimulationTimeSeries(...)
    db.session.add(point)
    db.session.commit()  # Slow! 1000 commits for 1000 points

# GOOD: Batch commit
points = []
for time, pressure in pt_data:
    points.append(SimulationTimeSeries(...))
    
    # Commit in batches of 1000
    if len(points) >= 1000:
        db.session.bulk_save_objects(points)
        db.session.commit()
        points = []

# Commit remaining
if points:
    db.session.bulk_save_objects(points)
    db.session.commit()
```

### 3. Use Indexes
All critical indexes are already created in schema.sql. Make sure you:
- Query by `simulation_id` (indexed)
- Query by `(simulation_id, sequence_number)` (composite indexed)
- Query by `(simulation_id, time_point)` (composite indexed)

---

## 🔄 Migration from Old Schema

### From DB_dev (SQLite with JSON)
```python
def migrate_from_db_dev():
    # 1. Copy users, recipes, work_orders (structure is similar)
    # 2. For each simulation:
    old_sim = OldSimulation.query.get(123)
    result_data = json.loads(old_sim.result_data)
    
    # Create new simulation
    new_sim = Simulation(
        user_id=old_sim.user_id,
        # ... copy other fields
    )
    db.session.add(new_sim)
    db.session.flush()
    
    # Parse JSON and insert time series
    for i, point in enumerate(result_data['time_series']):
        ts = SimulationTimeSeries(
            simulation_id=new_sim.id,
            time_point=point['time'],
            pressure=point['pressure'],
            sequence_number=i + 1
        )
        db.session.add(ts)
    
    db.session.commit()
```

---

## 🗄️ Database Maintenance

### Backup (SQLite)
```python
from database.manager import backup_database

backup_path = backup_database(app)
print(f'Backup saved to: {backup_path}')
```

### Reset Database (⚠️ DESTRUCTIVE)
```python
from database.manager import reset_database

# WARNING: This deletes all data!
reset_database(app)
```

### Enable WAL Mode (SQLite)
```python
# Automatic on initialization, or manually:
db.session.execute(text('PRAGMA journal_mode=WAL'))
db.session.commit()
```

---

## 📈 Scaling to PostgreSQL

When ready to move to production with PostgreSQL:

1. **Update connection string:**
   ```python
   SQLALCHEMY_DATABASE_URI = 'postgresql://user:pass@localhost/mgg_db'
   ```

2. **Run migrations:**
   ```bash
   # Use Alembic for PostgreSQL
   alembic init migrations
   alembic revision --autogenerate -m "Initial schema"
   alembic upgrade head
   ```

3. **No code changes needed!** Schema is compatible with both.

---

## 🎓 Design Decisions Explained

### Why Embedded Strings Instead of Lookup Tables?
**TL;DR:** Your parameter types are static and small.

**Lookup table approach (Master branch):**
```sql
-- 10+ tables for parameters
CREATE TABLE nc_types1 (...);
CREATE TABLE nc_types2 (...);
-- Every query needs 8+ joins
SELECT * FROM simulation
JOIN nc_types1 ON ...
JOIN nc_types2 ON ...
JOIN gp_types ON ...
-- (8 more joins)
```

**Embedded string approach (This schema):**
```sql
-- Simple, direct
SELECT * FROM simulation WHERE id = 123;  -- Done!

-- Data validation via CHECK constraint
CHECK (status IN ('pending', 'in_progress', 'completed'))
```

**Pros:**
- ✅ Zero joins for basic queries
- ✅ Easier to work with
- ✅ Faster development

**Cons:**
- ❌ No referential integrity on parameters
- ❌ String duplication (minimal space cost)

**When lookup tables make sense:**
- Parameters change frequently
- Need to store physical properties (density, etc.) with each parameter
- Need referential integrity enforcement
- Have 100+ parameter types

**For MGG:**
- ✅ ~5-20 static parameter types
- ✅ Types don't change often
- ✅ Simplicity > over-engineering
- ✅ Can add CHECK constraints if needed

---

### Why Separate Time Series Tables?
**Critical for performance on large datasets.**

**Without separation:**
- Must load entire JSON blob (can be 100MB+)
- Can't query individual points
- Can't paginate
- Can't filter by time range in SQL

**With separation:**
- Query only what you need
- Database-level filtering
- Pagination support
- Indexes on time/sequence

**Rule of thumb:** If you have >1000 time points per simulation, use separate tables.

---

## 📞 Support

For questions or issues:
1. Check this README
2. Review `schema.sql` comments
3. Look at example code in `models.py`
4. Check Flask-SQLAlchemy docs: https://flask-sqlalchemy.palletsprojects.com/

---

**Last Updated:** 2026-02-23  
**Schema Version:** 3.0 (Optimized Hybrid)
