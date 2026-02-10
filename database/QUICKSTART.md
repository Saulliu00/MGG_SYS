# Database Quick Start Guide

**5-Minute Setup** - Get the MGG database running quickly

---

## Prerequisites Check

```bash
# Check PostgreSQL installation
psql --version
# Should show: psql (PostgreSQL) 15.x or higher

# Check Python version
python3 --version
# Should show: Python 3.9 or higher
```

---

## Step 1: Create Database (1 min)

```bash
# Create the database
createdb mgg_simulation

# Verify it was created
psql -l | grep mgg_simulation
```

---

## Step 2: Install Python Dependencies (1 min)

```bash
cd database/

# Install required packages
pip install -r requirements.txt

# Verify installation
python3 -c "import sqlalchemy; print(f'SQLAlchemy {sqlalchemy.__version__}')"
```

---

## Step 3: Configure Environment (1 min)

```bash
# Copy example environment file
cp .env.example .env

# Edit .env with your settings (optional - defaults work for local development)
nano .env
```

**Default settings work for local PostgreSQL installation.**

---

## Step 4: Load Schema (30 seconds)

```bash
# Validate schema first (optional)
python3 check_schema.py

# Load schema into database
psql mgg_simulation < schema.sql
```

Expected output:
```
CREATE TABLE
CREATE TABLE
...
CREATE VIEW
CREATE VIEW
INSERT 0 6
```

---

## Step 5: Initialize Data (30 seconds)

```bash
# Initialize with default data
python3 init_db.py
```

Expected output:
```
Testing database connection...
✓ Database connection successful
Creating database tables...
✓ All tables created successfully
Seeding initial data...
✓ Seeded 3 igniter types
✓ Seeded 3 NC types
✓ Seeded 2 GP types
✓ Seeded 3 test devices
✓ Seeded 6 retention policies
✓ Created admin user (username: admin, password: admin123)
```

---

## Step 6: Verify Installation (30 seconds)

```bash
# Test database connection
python3 -c "from db_config import test_db_connection; test_db_connection()"

# Check tables were created
psql mgg_simulation -c "\dt"

# Check admin user was created
psql mgg_simulation -c "SELECT username, employee_id, role FROM users;"
```

---

## ✅ Done!

Your database is now ready to use.

### Default Admin Credentials:
- **Username**: `admin`
- **Password**: `admin123`

⚠️ **IMPORTANT**: Change the admin password immediately!

---

## Optional: Add Sample Data

```bash
# Add sample simulations, tests, and comparisons for testing
python3 seed_data.py
```

This creates:
- 2 sample users (engineer1, user1)
- 2 sample work orders
- 1 sample forward simulation with PT curve
- 1 sample test result with PT curve
- 1 sample PT comparison
- 4 sample operation logs

---

## Quick Commands Reference

```bash
# View all tables
psql mgg_simulation -c "\dt"

# View table structure
psql mgg_simulation -c "\d users"

# Count records in a table
psql mgg_simulation -c "SELECT COUNT(*) FROM users;"

# Reset database (WARNING: Deletes all data!)
python3 init_db.py --reset

# Backup database
pg_dump -Fc mgg_simulation > backup.dump

# Restore database
pg_restore -d mgg_simulation backup.dump
```

---

## Troubleshooting

### "Command not found: createdb"
PostgreSQL is not installed or not in PATH.
```bash
# macOS
brew install postgresql@15
brew services start postgresql@15

# Ubuntu
sudo apt-get install postgresql-15
```

### "Connection refused"
PostgreSQL is not running.
```bash
# macOS
brew services start postgresql@15

# Ubuntu
sudo systemctl start postgresql
```

### "Permission denied"
Need to create PostgreSQL user or grant permissions.
```bash
# Create user (as postgres user)
sudo -u postgres createuser -s $USER

# Or grant permissions
psql -d postgres -c "GRANT ALL PRIVILEGES ON DATABASE mgg_simulation TO $USER;"
```

### "Module not found: sqlalchemy"
Python dependencies not installed.
```bash
pip install -r requirements.txt
```

---

## Next Steps

1. ✅ Database is set up
2. 🔧 Integrate with Flask app (see main project README)
3. 🔒 Change admin password
4. 📊 Start using the system

---

## Need Help?

- **Full Setup Guide**: See [SETUP.md](SETUP.md)
- **Architecture Details**: See [README.md](README.md)
