# Database Migrations

Migration scripts for MGG_SYS schema changes.

---

## Migration: Recipe Unique Constraint

**File:** `add_recipe_unique_constraint.py`
**Purpose:** Add `UNIQUE(ignition_model, nc_type_1, nc_usage_1, nc_type_2, nc_usage_2, gp_type, gp_usage, shell_model, current, sensor_model, body_model)` to the `simulation` table.

> **Status:** Already applied to `instance/simulation_system.db` as of 2026-03-05.

### Usage

```bash
# From project root, with Flask stopped
python migrations/add_recipe_unique_constraint.py

# Rollback (remove constraint)
python migrations/add_recipe_unique_constraint.py --rollback
```

**Safe to run multiple times** — script skips if constraint already exists.

### Before running

```bash
# 1. Stop the Flask server (avoids database lock)
# 2. Backup the database
cp instance/simulation_system.db instance/simulation_system.db.backup

# 3. Run migration
python migrations/add_recipe_unique_constraint.py

# 4. Restart Flask
python run.py
```

### What it does

SQLite doesn't support `ADD CONSTRAINT`, so the migration:
1. Checks for and (optionally) removes duplicate recipes
2. Creates `simulation_new` with the unique constraint
3. Copies all data from `simulation`
4. Drops `simulation`, renames `simulation_new` → `simulation`

### Constraint fields (11 total)

| Field | Type |
|-------|------|
| ignition_model | String |
| nc_type_1, nc_type_2 | String |
| nc_usage_1, nc_usage_2 | Float |
| gp_type | String |
| gp_usage | Float |
| shell_model, sensor_model, body_model | String |
| current | Float |

Metadata fields (`user_id`, `work_order`, `employee_id`, `notes`, `created_at`) are excluded — the same recipe can be tracked under different work orders.

### Troubleshooting

| Error | Solution |
|-------|---------|
| `Database not found` | Run from project root: `cd /home/saul_liu/Desktop/MGG_SYS` |
| `database is locked` | Stop Flask server first, then retry |
| `table simulation_new already exists` | Prior attempt failed — `DROP TABLE simulation_new;` in sqlite3, then retry |
| Duplicates found | Script prompts to auto-remove (keeps oldest record) |

### Verification

```bash
sqlite3 instance/simulation_system.db \
  "SELECT sql FROM sqlite_master WHERE type='table' AND name='simulation';"
```

Output should contain `CONSTRAINT uq_simulation_recipe UNIQUE`.
