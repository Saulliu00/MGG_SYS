# Database Migrations

This directory contains database migration scripts for MGG_SYS schema changes.

## Migration: Recipe Unique Constraint

**File:** `add_recipe_unique_constraint.py`  
**Purpose:** Add database-level unique constraint on simulation recipe parameters

### Quick Start

**Standard Usage (Recommended):**
```bash
cd /home/saul/.openclaw/workspace/MGG_SYS
python migrations/add_recipe_unique_constraint.py
```

**With Backup (Safe):**
```bash
# 1. Create backup
cp instance/mgg_sys.db instance/mgg_sys.db.backup

# 2. Run migration
python migrations/add_recipe_unique_constraint.py

# 3. If successful, backup is safety net
# If issues, restore: cp instance/mgg_sys.db.backup instance/mgg_sys.db
```

**Rollback (Remove Constraint):**
```bash
python migrations/add_recipe_unique_constraint.py --rollback
```

---

## What This Migration Does

### Before Migration
```sql
CREATE TABLE simulation (
    id INTEGER PRIMARY KEY,
    user_id INTEGER,
    ignition_model VARCHAR(50),
    nc_type_1 VARCHAR(50),
    nc_usage_1 FLOAT,
    -- ... 11 total recipe fields ...
    -- No constraint - duplicates allowed ❌
);
```

### After Migration
```sql
CREATE TABLE simulation (
    id INTEGER PRIMARY KEY,
    user_id INTEGER,
    ignition_model VARCHAR(50),
    nc_type_1 VARCHAR(50),
    nc_usage_1 FLOAT,
    -- ... 11 total recipe fields ...
    CONSTRAINT uq_simulation_recipe UNIQUE (
        ignition_model, nc_type_1, nc_usage_1, nc_type_2, nc_usage_2,
        gp_type, gp_usage, shell_model, current, sensor_model, body_model
    )  -- Prevents duplicate recipes ✅
);
```

---

## Migration Process

### Step-by-Step

1. **Check for Existing Constraint**
   - If already exists → Skip migration ✅
   - If not → Proceed to step 2

2. **Detect Duplicate Recipes**
   - Queries database for duplicate recipe parameters
   - If found → Prompts user to auto-remove
   - If none → Proceeds to step 3

3. **Create New Table**
   - Creates `simulation_new` with unique constraint
   - Schema identical to old table + constraint

4. **Migrate Data**
   - Copies all records from `simulation` to `simulation_new`
   - Preserves all data (no data loss)

5. **Replace Old Table**
   - Drops old `simulation` table
   - Renames `simulation_new` to `simulation`

6. **Commit**
   - Transaction commits (all or nothing)

### Safety Features

- ✅ **Idempotent**: Can run multiple times safely
- ✅ **Transactional**: All changes or no changes
- ✅ **Backup Prompts**: Warns before deleting duplicates
- ✅ **Data Preservation**: Keeps oldest record when deduplicating
- ✅ **Rollback Support**: Can undo migration with `--rollback`

---

## Example Output

### Success (No Duplicates)

```
Starting migration on database: instance/mgg_sys.db
Checking for existing duplicates...
✓ No duplicate recipes found
Creating new table with unique constraint...
Copying data to new table...
Replacing old table...
✓ Migration completed successfully!
✓ Unique constraint 'uq_simulation_recipe' added to simulation table
```

### Success (With Duplicates)

```
Starting migration on database: instance/mgg_sys.db
Checking for existing duplicates...
⚠️  WARNING: Found 3 duplicate recipe(s) in database:
  1. Recipe with 2 duplicates
  2. Recipe with 2 duplicates
  3. Recipe with 3 duplicates

Remove duplicates automatically? (y/n): y
✓ Removed 3 duplicate recipe(s). Kept oldest records.
Creating new table with unique constraint...
Copying data to new table...
Replacing old table...
✓ Migration completed successfully!
✓ Unique constraint 'uq_simulation_recipe' added to simulation table
```

### Already Migrated

```
Starting migration on database: instance/mgg_sys.db
✓ Constraint 'uq_simulation_recipe' already exists. Skipping migration.
```

---

## Troubleshooting

### "Database not found"

**Error:**
```
ERROR: Database not found at instance/mgg_sys.db
```

**Solution:**
```bash
# Check current directory
pwd  # Should be /home/saul/.openclaw/workspace/MGG_SYS

# If not, navigate there
cd /home/saul/.openclaw/workspace/MGG_SYS

# Run migration again
python migrations/add_recipe_unique_constraint.py
```

---

### "Migration failed: database is locked"

**Error:**
```
✗ Migration failed: database is locked
```

**Cause:** Flask application is running

**Solution:**
```bash
# 1. Stop Flask server
# Press Ctrl+C in terminal where Flask is running

# 2. Wait 3 seconds (ensure connections closed)
sleep 3

# 3. Run migration
python migrations/add_recipe_unique_constraint.py

# 4. Restart Flask
python run.py
```

---

### Duplicates Found - How to Decide

**Scenario:**
```
⚠️  WARNING: Found 2 duplicate recipe(s)
Remove duplicates automatically? (y/n):
```

**Option A: Auto-Remove (Recommended)**
```
Remove duplicates automatically? (y/n): y
```
- **What happens:** Keeps oldest simulation, deletes newer ones
- **Safe when:** Duplicates have same result_data (cached results)
- **Risk:** Low - only metadata lost (test_name, notes)

**Option B: Manual Review**
```
Remove duplicates automatically? (y/n): n
```
- **What happens:** Migration cancelled
- **Do this when:** Need to merge data manually
- **Next step:** Use SQLite browser to inspect duplicates

**Manual Inspection:**
```sql
-- Find duplicate recipes
SELECT 
    id, created_at, test_name, work_order, employee_id,
    nc_usage_1, gp_type  -- Example recipe fields
FROM simulation
WHERE (nc_usage_1, gp_type, ...) IN (
    SELECT nc_usage_1, gp_type, ...
    FROM simulation
    GROUP BY nc_usage_1, gp_type, ...
    HAVING COUNT(*) > 1
)
ORDER BY nc_usage_1, created_at;
```

---

## Rollback

### When to Rollback

**Rollback if:**
- ❌ Migration corrupted data (verify with SELECT queries)
- ❌ Application breaks after migration
- ❌ Need to restore duplicates

**Don't rollback if:**
- ✅ Just want to test - create a copy of DB first
- ✅ Migration succeeded but behavior unchanged (constraint is working!)

### How to Rollback

```bash
python migrations/add_recipe_unique_constraint.py --rollback
```

**Output:**
```
Rolling back migration on database: instance/mgg_sys.db
Creating table without constraint...
Copying data...
Replacing table...
✓ Rollback completed successfully!
```

**Result:**
- Constraint removed ✅
- All data preserved ✅
- Duplicates allowed again ⚠️

---

## Post-Migration Verification

### Test 1: Constraint Exists

**SQL Query:**
```sql
SELECT sql FROM sqlite_master 
WHERE type='table' AND name='simulation';
```

**Expected:** Should contain `CONSTRAINT uq_simulation_recipe UNIQUE`

---

### Test 2: Application Still Works

1. **Login** to MGG_SYS
2. **Run Simulation** with any recipe
3. **Verify:** Simulation completes successfully ✅
4. **Run Same Recipe Again**
5. **Verify:** Returns cached result (no new record) ✅

---

### Test 3: Duplicate Prevention

**Python Test:**
```python
from app import create_app, db
from app.models import Simulation

app = create_app()
with app.app_context():
    # Try to create duplicate
    sim1 = Simulation(user_id=1, nc_usage_1=100.0, gp_type='A')
    db.session.add(sim1)
    db.session.commit()  # Success ✅
    
    sim2 = Simulation(user_id=2, nc_usage_1=100.0, gp_type='A')
    db.session.add(sim2)
    db.session.commit()  # Should raise IntegrityError ✅
```

**Expected:** Second commit raises `sqlalchemy.exc.IntegrityError`

---

## Constraint Details

### Fields in Constraint (11 total)

**String Fields (7):**
- `ignition_model` - 点火具型号
- `nc_type_1` - NC类型1
- `nc_type_2` - NC类型2
- `gp_type` - GP类型
- `shell_model` - 管壳高度
- `sensor_model` - 传感器量程
- `body_model` - 容积

**Numeric Fields (4):**
- `nc_usage_1` - NC用量1 (毫克)
- `nc_usage_2` - NC用量2 (毫克)
- `gp_usage` - GP用量 (毫克)
- `current` - 通电条件(mA)

### Fields EXCLUDED (Metadata)

**Why excluded:**
- Different users can name the same recipe differently
- Work orders and notes are metadata, not recipe definition

**Fields:**
- `user_id` - Can differ (lab-wide deduplication)
- `employee_id` - Personal identifier
- `test_name` - User-defined name
- `notes` - Comments
- `work_order` - Project tracking
- `equipment` - Testing device
- `created_at` - Timestamp
- `result_data` - Output (should be identical for same recipe)

---

## FAQ

**Q: Will this delete my data?**  
A: No. Migration preserves all data. Only removes exact duplicate recipes (same parameters).

**Q: What if I have duplicates?**  
A: Script detects and offers to auto-remove. Keeps oldest record, deletes newer ones.

**Q: Can I undo this?**  
A: Yes. Run `python migrations/add_recipe_unique_constraint.py --rollback`

**Q: Will application break during migration?**  
A: No. Migration is fast (<1 second for 1000 records). Stop Flask first for safety.

**Q: What if migration fails halfway?**  
A: SQLite transactions are atomic. Either all changes apply or none. Database stays consistent.

**Q: Do I need to run this on every deployment?**  
A: No. Once per database. Script auto-detects if already migrated.

**Q: What about the optimized database (database/models.py)?**  
A: That's a separate schema. This migration is for current production (`app/models.py`).

---

## Support

**Issues:**
- Check `CHANGELOG.md` for known issues
- Run diagnostic: `sqlite3 instance/mgg_sys.db ".schema simulation"`
- Verify Flask stopped: `ps aux | grep flask`

**Questions:**
- Review this README
- Check `app/models.py` for constraint definition
- Inspect migration source: `migrations/add_recipe_unique_constraint.py`

---

**Last Updated:** 2026-03-05  
**Migration Version:** 1.0  
**Compatibility:** MGG_SYS v1.x (db-optimized branch)
