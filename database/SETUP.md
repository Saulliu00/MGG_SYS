# Database Setup Guide

Complete guide for setting up the PostgreSQL database for the MGG Simulation System.

## Prerequisites

- PostgreSQL 15+ installed
- Python 3.9+ installed
- pip package manager

## Installation Steps

### 1. Install PostgreSQL

#### macOS
```bash
brew install postgresql@15
brew services start postgresql@15
```

#### Ubuntu/Debian
```bash
sudo apt-get update
sudo apt-get install postgresql-15 postgresql-contrib
sudo systemctl start postgresql
sudo systemctl enable postgresql
```

#### Windows
Download and install from: https://www.postgresql.org/download/windows/

### 2. Create Database and User

```bash
# Switch to postgres user (Linux only)
sudo -u postgres psql

# Or connect directly (macOS/Windows)
psql postgres
```

In PostgreSQL shell:
```sql
-- Create database
CREATE DATABASE mgg_simulation;

-- Create user
CREATE USER mgg_user WITH PASSWORD 'mgg_password';

-- Grant privileges
GRANT ALL PRIVILEGES ON DATABASE mgg_simulation TO mgg_user;

-- Exit
\q
```

### 3. Install Python Dependencies

```bash
cd database/
pip install -r requirements.txt
```

### 4. Configure Environment Variables

```bash
# Copy example environment file
cp .env.example .env

# Edit .env with your database credentials
nano .env  # or use your preferred editor
```

Update these values in `.env`:
```
POSTGRES_USER=mgg_user
POSTGRES_PASSWORD=your_secure_password
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=mgg_simulation
```

### 5. Initialize Database

#### Option A: Create Schema Only
```bash
# Using SQL file
psql mgg_simulation < schema.sql

# Or using Python init script
python init_db.py
```

#### Option B: Create Schema + Seed Initial Data
```bash
python init_db.py
```

This will create:
- All database tables
- Igniter types (3 types)
- NC types (3 types)
- GP types (2 types)
- Test devices (3 devices)
- Retention policies
- Admin user (username: `admin`, password: `admin123`)

**⚠️ IMPORTANT: Change the admin password immediately after first login!**

#### Option C: Create Schema + Seed Sample Data
```bash
# First initialize with init_db.py
python init_db.py

# Then add sample data for testing
python seed_data.py
```

This adds:
- Sample users (engineer1, user1)
- Sample work orders
- Sample forward simulations with time series data
- Sample test results with time series data
- Sample PT comparisons
- Sample operation logs

### 6. Verify Installation

```bash
python db_config.py
```

Expected output:
```
Testing database connection...
✓ Database connection successful!
```

### 7. Create Archive Directory

```bash
# From project root
mkdir -p parquet_archive
```

## Database Management Commands

### Reset Database (Drop and Recreate)
```bash
python init_db.py --reset
```

**⚠️ WARNING: This will delete ALL data!**

### Drop All Tables
```bash
python init_db.py --drop
```

### Backup Database
```bash
# Create backup
pg_dump -Fc mgg_simulation > backup_$(date +%Y%m%d).dump

# Restore from backup
pg_restore -d mgg_simulation backup_20240115.dump
```

### View Database Size
```sql
SELECT
    pg_size_pretty(pg_database_size('mgg_simulation')) AS database_size;
```

### View Table Sizes
```sql
SELECT
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
```

## Archive Management

### Run Retention Policy (Archive Old Data)
```bash
cd database/
python -c "from archive_manager import ArchiveManager; mgr = ArchiveManager(); mgr.run_retention_policy()"
```

### List Archives
```python
from archive_manager import ArchiveManager

mgr = ArchiveManager()
archives = mgr.list_archives()
for archive in archives:
    print(archive)
```

### Restore from Archive
```python
from archive_manager import ArchiveManager

mgr = ArchiveManager()
mgr.restore_from_archive('simulation_time_series_20240101_20240331')
```

## Connection Pooling

The database uses SQLAlchemy connection pooling:
- **Pool Size**: 10 connections (configurable via `DB_POOL_SIZE`)
- **Max Overflow**: 20 additional connections (configurable via `DB_MAX_OVERFLOW`)
- **Pool Timeout**: 30 seconds (configurable via `DB_POOL_TIMEOUT`)
- **Pool Recycle**: 3600 seconds / 1 hour (configurable via `DB_POOL_RECYCLE`)

## Security Best Practices

### 1. Change Default Passwords
```sql
ALTER USER mgg_user WITH PASSWORD 'new_secure_password';
```

Update admin password after first login via the web interface.

### 2. Enable SSL/TLS (Production)
In `.env`:
```
POSTGRES_HOST=your-server.com
DATABASE_URL=postgresql://user:pass@host:5432/db?sslmode=require
```

### 3. Restrict Database Access
```sql
-- Revoke public access
REVOKE ALL ON DATABASE mgg_simulation FROM PUBLIC;

-- Grant only to specific users
GRANT CONNECT ON DATABASE mgg_simulation TO mgg_user;
```

### 4. Enable Row-Level Security (if needed)
```sql
ALTER TABLE users ENABLE ROW LEVEL SECURITY;

CREATE POLICY user_isolation_policy ON users
    USING (id = current_user_id());
```

## Monitoring

### Check Active Connections
```sql
SELECT count(*)
FROM pg_stat_activity
WHERE datname = 'mgg_simulation';
```

### View Slow Queries
```sql
SELECT
    query,
    calls,
    total_time,
    mean_time,
    max_time
FROM pg_stat_statements
ORDER BY mean_time DESC
LIMIT 10;
```

### Check Table Bloat
```sql
SELECT
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS total_size,
    n_live_tup AS live_tuples,
    n_dead_tup AS dead_tuples
FROM pg_stat_user_tables
WHERE n_dead_tup > 1000
ORDER BY n_dead_tup DESC;
```

## Troubleshooting

### Connection Refused
```bash
# Check if PostgreSQL is running
sudo systemctl status postgresql  # Linux
brew services list  # macOS

# Start PostgreSQL if not running
sudo systemctl start postgresql  # Linux
brew services start postgresql@15  # macOS
```

### Authentication Failed
- Check username and password in `.env`
- Verify user exists: `psql postgres -c "\du"`
- Check `pg_hba.conf` for authentication method

### Permission Denied
```sql
-- Grant necessary permissions
GRANT ALL PRIVILEGES ON DATABASE mgg_simulation TO mgg_user;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO mgg_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO mgg_user;
```

### Out of Memory
Increase PostgreSQL memory settings in `postgresql.conf`:
```
shared_buffers = 2GB  # 25% of RAM
work_mem = 64MB
maintenance_work_mem = 512MB
effective_cache_size = 6GB  # 50-75% of RAM
```

## Next Steps

1. Configure automatic backups with cron/Task Scheduler
2. Set up monitoring with pg_stat_statements
3. Configure archive retention policies
4. Integrate with main Flask application
5. Set up replication for high availability (production)

## Additional Resources

- [PostgreSQL Documentation](https://www.postgresql.org/docs/)
- [SQLAlchemy Documentation](https://docs.sqlalchemy.org/)
- [Parquet Format](https://parquet.apache.org/docs/)
