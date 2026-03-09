# Database Setup Guide

Complete guide for the MGG Simulation System database — from development (SQLite) to production (PostgreSQL).

---

## Development Setup (SQLite — Default)

No configuration is required. On the first run, Flask auto-creates the SQLite database:

```bash
# From project root
source venv/bin/activate
export SECRET_KEY=$(python -c "import secrets; print(secrets.token_hex(32))")
python run.py
```

The database is created at `instance/simulation_system.db` and seeded with a default admin account.

**Default credentials:**
```
Employee ID: admin
Password:    admin123   (or value of ADMIN_PASSWORD env var)
```

---

## Production Setup (PostgreSQL)

### Prerequisites

- PostgreSQL 15+
- Python 3.9+
- `psycopg2` driver (`pip install psycopg2-binary`)

### 1. Install PostgreSQL

**Ubuntu / Debian**
```bash
sudo apt-get update
sudo apt-get install postgresql-15 postgresql-contrib
sudo systemctl start postgresql
sudo systemctl enable postgresql
```

**macOS**
```bash
brew install postgresql@15
brew services start postgresql@15
```

**Windows**
Download from [postgresql.org/download/windows](https://www.postgresql.org/download/windows/)

### 2. Create Database and User

```bash
sudo -u postgres psql          # Linux
# or: psql postgres            # macOS / Windows
```

```sql
CREATE DATABASE mgg_simulation;
CREATE USER mgg_user WITH PASSWORD 'your_secure_password';
GRANT ALL PRIVILEGES ON DATABASE mgg_simulation TO mgg_user;
\q
```

### 3. Configure Environment Variables

```bash
export SECRET_KEY=<your-secret-key>
export ADMIN_PASSWORD=<your-admin-password>
export DATABASE_URL=postgresql://mgg_user:your_secure_password@localhost:5432/mgg_simulation
```

Or store them in a `.env` file (loaded by `python-dotenv`):
```env
SECRET_KEY=your_secret_key_here
ADMIN_PASSWORD=your_admin_password
DATABASE_URL=postgresql://mgg_user:your_secure_password@localhost:5432/mgg_simulation
```

### 4. Start the Application

```bash
# Development
python run.py

# Production (Gunicorn)
gunicorn -c gunicorn.conf.py "app:create_app()"
```

Flask-SQLAlchemy creates all tables automatically on first start (`db.create_all()`).

---

## Connection Pool Settings

Configured in `app/config/network_config.py` (tune for your hardware):

| Setting | Default | Description |
|---------|---------|-------------|
| `pool_size` | 25 | Persistent connections kept open |
| `max_overflow` | 25 | Extra connections allowed on burst |
| `pool_timeout` | 10s | Time to wait for a free connection |
| `pool_recycle` | 3600s | Recycle idle connections hourly |
| `pool_pre_ping` | True | Discard stale connections automatically |

For **100 concurrent users**, the defaults (25+25=50 max connections, 5 workers × 5 threads) are sufficient.

For **PostgreSQL**, also tune `postgresql.conf`:
```
max_connections = 100
shared_buffers = 16GB         # ~25% of RAM
work_mem = 256MB
effective_cache_size = 48GB   # ~75% of RAM
```

---

## SSL/TLS (Production)

```env
DATABASE_URL=postgresql://mgg_user:pass@your-server.com:5432/mgg_simulation?sslmode=require
```

---

## Backup and Restore

### Automated daily backup (recommended)

`scripts/backup.py` backs up database + uploaded Excel files + application logs in one shot:

```bash
# Run once to verify
python scripts/backup.py

# Schedule via cron — daily at 02:00
0 2 * * * cd /home/saul_liu/Desktop/MGG_SYS && \
          /home/saul_liu/Desktop/MGG_SYS/venv/bin/python scripts/backup.py \
          >> /var/log/mgg_backup.log 2>&1
```

Output in `instance/backups/`:
- `mgg_backup_YYYYMMDD_HHMMSS.db` — SQLite copy **or** `mgg_backup_*.dump` — pg_dump archive
- `uploads_YYYYMMDD_HHMMSS.tar.gz` — all uploaded Excel files
- `logs_YYYYMMDD_HHMMSS.tar.gz` — application CSV logs

Backups older than 30 days are pruned automatically (override: `--retention-days N`).

### Via application code (SQLite or PostgreSQL)
```python
from database.manager import backup_database
path = backup_database(app)   # writes to instance/backups/
```

### Manual PostgreSQL backup / restore
```bash
# Backup
pg_dump -Fc mgg_simulation > backup_$(date +%Y%m%d_%H%M%S).dump

# Restore
pg_restore -d mgg_simulation backup_20260306_120000.dump
```

---

## Database Management

### Reset (destructive — deletes all data)
```bash
# Via Python
python -c "
from app import create_app
from database.manager import reset_database
app = create_app()
reset_database(app)
"
```

### View schema (SQLite)
```bash
sqlite3 instance/simulation_system.db ".schema"
```

### View table sizes (PostgreSQL)
```sql
SELECT
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname || '.' || tablename)) AS size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname || '.' || tablename) DESC;
```

---

## Security

### 1. Change Default Passwords
```bash
# Application admin — via web interface (Admin Panel) or env var at startup
export ADMIN_PASSWORD=new_secure_password

# PostgreSQL user
psql -c "ALTER USER mgg_user WITH PASSWORD 'new_secure_password';"
```

### 2. Restrict Database Access (PostgreSQL)
```sql
REVOKE ALL ON DATABASE mgg_simulation FROM PUBLIC;
GRANT CONNECT ON DATABASE mgg_simulation TO mgg_user;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO mgg_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO mgg_user;
```

---

## Monitoring (PostgreSQL)

### Active connections
```sql
SELECT count(*)
FROM pg_stat_activity
WHERE datname = 'mgg_simulation';
```

### Slow queries (requires `pg_stat_statements`)
```sql
SELECT query, calls, mean_exec_time, max_exec_time
FROM pg_stat_statements
ORDER BY mean_exec_time DESC
LIMIT 10;
```

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| `connection refused` | Check `systemctl status postgresql` (Linux) or `brew services list` (macOS) |
| `authentication failed` | Verify `DATABASE_URL` credentials; check `pg_hba.conf` |
| `permission denied` | Re-run the `GRANT` statements above |
| `database is locked` (SQLite) | Enable WAL mode (automatic on init), reduce concurrent connections, or migrate to PostgreSQL |
| `no such table` | Run `python run.py` once — `db.create_all()` creates tables on startup |

---

## Additional Resources

- [PostgreSQL Documentation](https://www.postgresql.org/docs/)
- [SQLAlchemy Documentation](https://docs.sqlalchemy.org/)
- [Flask-SQLAlchemy Documentation](https://flask-sqlalchemy.palletsprojects.com/)
- Current schema: `database/README.md`
- Future normalized schema: `database/DATABASE_SCHEMA_VISUALIZATION.md`
