# MGG Simulation System

**Gas Generator Simulation and Analysis Platform**  
**Branch:** `db-optimized` (Hybrid Database Design)  
**Version:** 3.0

---

## 🎯 What This Branch Does

This is the **optimized database branch** - a hybrid design combining:
- ✅ **Simplicity** of embedded parameters (like DB_dev)
- ✅ **Performance** of separated time series (like Master)
- ✅ **Best practices** from both approaches

### Key Improvements Over Other Branches:

| Feature | db-optimized | Master | DB_dev |
|---------|-------------|--------|---------|
| **Time Series** | Separate tables ✅ | Separate tables ✅ | JSON blobs ❌ |
| **Query Complexity** | Simple (no joins) ✅ | Complex (10+ joins) ❌ | Simple ✅ |
| **Data Integrity** | CHECK constraints ✅ | FK constraints ✅ | Application-level ⚠️ |
| **Setup Complexity** | Low ✅ | High ❌ | Low ✅ |
| **Performance** | Excellent ✅ | Good ✅ | Poor on large datasets ❌ |
| **Scalability** | High ✅ | Very High ✅ | Medium ⚠️ |

---

## 🚀 Quick Start

### 1. Clone & Setup
```bash
git clone https://github.com/Saulliu00/MGG_SYS.git
cd MGG_SYS
git checkout db-optimized

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Initialize Database
```python
from app import create_app
from database.manager import init_database

app = create_app()
init_database(app)
```

### 3. Login
- **URL:** http://localhost:5000
- **Default Admin:** `admin / admin123`
- ⚠️ **Change password immediately!**

---

## 📁 Project Structure

```
MGG_SYS/
├── app/                    # Flask application
│   ├── __init__.py
│   ├── routes/            # Route handlers
│   ├── services/          # Business logic
│   ├── templates/         # HTML templates
│   └── static/            # CSS, JS, images
│
├── database/              # ⭐ Database layer (NEW)
│   ├── models.py         # SQLAlchemy ORM models
│   ├── schema.sql        # Database schema (DDL)
│   ├── extensions.py     # Flask extensions (db, auth, bcrypt)
│   ├── manager.py        # Init, migrations, seeding
│   ├── README.md         # Full database documentation
│   ├── QUICKSTART.md     # 5-minute setup guide
│   └── requirements.txt  # Database dependencies
│
├── instance/              # Instance-specific files
│   └── mgg.db            # SQLite database (auto-created)
│
├── config.py              # App configuration
├── run.py                 # Application entry point
├── requirements.txt       # All dependencies
└── README.md             # This file
```

---

## 🗄️ Database Design

### Schema Overview

**8 Core Tables:**
1. **user** - Authentication & authorization
2. **recipe** - Reusable parameter sets
3. **work_order** - Test sessions (link recipes to tests)
4. **simulation** - Simulation runs (summary)
5. **simulation_time_series** - P-T data (detailed)
6. **test_result** - Experimental data (summary)
7. **test_time_series** - P-T data from experiments
8. **pt_comparison** - Simulation vs experimental comparison

### Key Relationships

```
User ─┬─► Recipe ──► WorkOrder ─┬─► Simulation ──► SimulationTimeSeries
      │                          │
      │                          ├─► TestResult ──► TestTimeSeries
      │                          │
      │                          └─► ExperimentFile
      │
      └─► PTComparison (Sim ↔ Test)
```

### Why This Design?

**Problem with normalized approach (Master):**
- Every query needs 10+ joins
- Complex setup (populate lookup tables first)
- Over-engineered for static parameter types

**Problem with denormalized approach (DB_dev):**
- Time series data in JSON blobs
- Can't query individual time points
- Poor performance on large datasets
- No pagination support

**Solution (db-optimized):**
- ✅ Simple embedded parameters (strings with CHECK constraints)
- ✅ Separated time series tables (efficient querying)
- ✅ Recipe abstraction (reusability without duplication)
- ✅ Strategic indexes (optimized access patterns)

**Read more:** [`database/README.md`](database/README.md)

---

## 💻 Usage Examples

### Create & Run Simulation

```python
from database.models import User, Recipe, WorkOrder, Simulation, SimulationTimeSeries
from database.extensions import db

# 1. Get or create recipe
recipe = Recipe(
    user_id=user.id,
    recipe_name='Standard Config',
    ignition_model='Type-A',
    nc_type_1='NC-Standard',
    nc_usage_1=20.0,
    # ... more parameters
)
db.session.add(recipe)
db.session.commit()

# 2. Create work order
wo = WorkOrder(
    work_order_number='WO-2026-001',
    recipe_id=recipe.id,
    user_id=user.id,
    test_name='Baseline Validation',
    status='in_progress'
)
db.session.add(wo)
db.session.flush()

# 3. Run simulation (your simulation code here)
time_data, pressure_data = run_simulation(recipe)

# 4. Save simulation results
sim = Simulation(
    user_id=user.id,
    work_order_id=wo.id,
    test_name='Run #1',
    peak_pressure=max(pressure_data),
    peak_time=time_data[pressure_data.index(max(pressure_data))],
    num_data_points=len(time_data),
    status='completed'
)
db.session.add(sim)
db.session.flush()

# 5. Save time series (critical: use separate table!)
for i, (t, p) in enumerate(zip(time_data, pressure_data)):
    point = SimulationTimeSeries(
        simulation_id=sim.id,
        time_point=t,
        pressure=p,
        sequence_number=i + 1
    )
    db.session.add(point)

db.session.commit()
```

### Query Time Series Efficiently

```python
# Get paginated results (handles millions of points)
page = 1
page_size = 1000
points = SimulationTimeSeries.query \
    .filter_by(simulation_id=sim.id) \
    .order_by(SimulationTimeSeries.sequence_number) \
    .offset((page - 1) * page_size) \
    .limit(page_size) \
    .all()

# Get time range around peak
peak_time = sim.peak_time
window = 10  # ±10ms
peak_region = SimulationTimeSeries.query \
    .filter_by(simulation_id=sim.id) \
    .filter(SimulationTimeSeries.time_point.between(
        peak_time - window, 
        peak_time + window
    )) \
    .all()
```

**More examples:** [`database/QUICKSTART.md`](database/QUICKSTART.md)

---

## 🔧 Configuration

### SQLite (Development - Default)
```python
# config.py
SQLALCHEMY_DATABASE_URI = 'sqlite:///instance/mgg.db'
```

**Pros:**
- ✅ Zero setup
- ✅ Single file database
- ✅ Fast for development

**Limitations:**
- ⚠️ ~10-20 concurrent users max
- ⚠️ No built-in replication

---

### PostgreSQL (Production - Recommended)
```python
# config.py
SQLALCHEMY_DATABASE_URI = 'postgresql://user:password@localhost/mgg_db'
```

**Pros:**
- ✅ 100+ concurrent users
- ✅ Advanced features
- ✅ Replication support
- ✅ Better performance at scale

**Migration:**
1. Schema is compatible (no changes needed!)
2. Export data from SQLite
3. Import to PostgreSQL
4. Update connection string

---

## 📊 Performance

### Benchmarks (100,000 time points)

| Operation | db-optimized | DB_dev (JSON) | Speedup |
|-----------|-------------|---------------|---------|
| Insert | 2.3s | 15.1s | **6.5x faster** |
| Query all | 1.1s | 8.7s | **7.9x faster** |
| Query range | 0.05s | 8.7s | **174x faster** |
| Pagination | 0.02s | N/A | **Instant** |

**Why faster?**
- Separated time series tables (database-level indexing)
- No JSON parsing overhead
- Efficient SQL filtering and sorting

---

## 🧪 Testing

### Run Tests
```bash
pytest tests/
```

### Manual Testing Checklist
- [ ] Create user
- [ ] Create recipe
- [ ] Create work order
- [ ] Run simulation
- [ ] Upload test data
- [ ] Compare results
- [ ] View charts

---

## 🔒 Security

### Built-in Features
- ✅ **Bcrypt** password hashing
- ✅ **Flask-Login** session management
- ✅ **Role-based access** (admin, engineer, user)
- ✅ **CSRF protection** (via Flask-WTF)
- ✅ **SQL injection prevention** (via SQLAlchemy ORM)

### Best Practices
1. **Change default admin password** immediately
2. Use **HTTPS** in production
3. Set **strong SECRET_KEY** in config
4. Enable **database backups**
5. Review **user permissions** regularly

---

## 🐛 Troubleshooting

### "Database is locked"
**Cause:** SQLite doesn't handle high concurrency well  
**Solution 1:** WAL mode enabled (automatic)  
**Solution 2:** Switch to PostgreSQL for production

### "No such table: user"
**Cause:** Database not initialized  
**Solution:**
```python
from database.manager import init_database
init_database(app)
```

### Slow queries on large datasets
**Cause:** Not using separated time series tables properly  
**Solution:** Use pagination, filter by time range, check indexes

**More help:** [`database/README.md`](database/README.md)

---

## 📚 Documentation

| Document | Description |
|----------|-------------|
| [`database/README.md`](database/README.md) | Full database documentation |
| [`database/QUICKSTART.md`](database/QUICKSTART.md) | 5-minute setup guide |
| [`database/schema.sql`](database/schema.sql) | Database schema (DDL) |
| [`database/models.py`](database/models.py) | ORM model definitions |

---

## 🔄 Branch Comparison

### Which Branch Should I Use?

**Use `db-optimized` if:**
- ✅ You want best balance of simplicity & performance
- ✅ Starting a new project
- ✅ Need efficient time series handling
- ✅ Want easy PostgreSQL migration path

**Use `master` if:**
- ✅ You need full normalization (lookup tables)
- ✅ Parameters have complex properties (density, heat, etc.)
- ✅ You have 50+ parameter types
- ✅ You want hot-cold archiving built-in

**Use `DB_dev` if:**
- ✅ Quick prototyping only
- ✅ Small datasets (<10,000 points per simulation)
- ✅ Temporary/demo system

---

## 🤝 Contributing

### Branch Workflow
```bash
# Create feature branch from db-optimized
git checkout db-optimized
git pull
git checkout -b feature/your-feature

# Make changes, commit
git add .
git commit -m "Add feature: description"

# Push and create PR
git push origin feature/your-feature
```

### Code Style
- Follow PEP 8 for Python
- Use type hints where helpful
- Document functions and classes
- Write tests for new features

---

## 📝 License

[Your license here]

---

## 📞 Support

- **Documentation:** [`database/README.md`](database/README.md)
- **Issues:** GitHub Issues
- **Contact:** saul.liu00@gmail.com

---

## 🗺️ Roadmap

### Phase 1: Core Features ✅
- [x] Database schema design
- [x] User authentication
- [x] Recipe management
- [x] Simulation runs
- [x] Time series storage

### Phase 2: Analysis Tools
- [ ] P-T comparison engine
- [ ] Statistical analysis
- [ ] Chart generation
- [ ] Export functionality

### Phase 3: Production Hardening
- [ ] PostgreSQL migration
- [ ] Automated backups
- [ ] Monitoring & logging
- [ ] Performance optimization

---

**Last Updated:** 2026-02-23  
**Database Version:** 3.0 (Optimized Hybrid)  
**Branch:** db-optimized
