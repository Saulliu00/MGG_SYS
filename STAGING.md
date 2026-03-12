# Staging Environment Plan

A staging box is a permanent second server that mirrors production exactly. Code is deployed and tested on staging before it reaches the customer's production machine. This document describes how to set one up for MGG_SYS.

---

## Why Staging

| Risk | Mitigated by staging |
|---|---|
| Environment-specific bugs (wrong Python version, missing package) | Staging uses the same OS and setup as production |
| Database migration failures | Run migrations on staging first; verify data integrity |
| Performance regressions under real load | Load-test on staging without affecting production |
| Configuration errors in `.env` or `gunicorn.conf.py` | Catch before the customer sees them |

---

## Staging Hardware Requirements

Staging does not need to match production exactly, but must be close enough to catch real issues.

| Resource | Minimum | Recommended |
|---|---|---|
| CPU | 4-core | 8-core |
| RAM | 16 GB | 32 GB |
| Disk | 100 GB SSD | 200 GB SSD |
| Network | 1 GbE | 1 GbE |
| OS | Ubuntu 22.04 LTS | Ubuntu 22.04 LTS (same as production) |

A spare physical machine, a VM (VirtualBox/VMware), or a cloud VM (AWS t3.xlarge, etc.) all work.

---

## Step 1 — Set Up the Staging Machine

Follow [NETWORK_DEPLOYMENT.md](NETWORK_DEPLOYMENT.md) **Steps 1–5** exactly, substituting the staging machine's hostname/IP.

Key differences from production:
- Use a separate PostgreSQL database name: `mgg_simulation_staging`
- Use a separate database user: `mgg_user_staging`
- Run on port `5002` (not `5001`) to avoid port conflict if staging and production ever share a host

```bash
# On staging server — create DB and user
sudo -u postgres psql <<'SQL'
CREATE DATABASE mgg_simulation_staging;
CREATE USER mgg_user_staging WITH PASSWORD 'staging_password_change_me';
GRANT ALL PRIVILEGES ON DATABASE mgg_simulation_staging TO mgg_user_staging;
SQL
```

---

## Step 2 — Staging `.env`

Create `/opt/mgg/MGG_SYS/.env` on the staging machine:

```bash
SECRET_KEY=<64-char hex — different from production>
ADMIN_PASSWORD=StagingAdmin1!
DATABASE_URL=postgresql://mgg_user_staging:staging_password_change_me@localhost:5432/mgg_simulation_staging
```

> Never reuse the production `SECRET_KEY` or `DATABASE_URL` on staging.

---

## Step 3 — Staging systemd Service

Copy the production service file and change the port:

```bash
sudo cp /etc/systemd/system/mgg.service /etc/systemd/system/mgg-staging.service
sudo sed -i 's/0.0.0.0:5001/0.0.0.0:5002/' /etc/systemd/system/mgg-staging.service
sudo sed -i 's/mgg.service/mgg-staging.service/' /etc/systemd/system/mgg-staging.service
sudo systemctl daemon-reload
sudo systemctl enable mgg-staging
sudo systemctl start mgg-staging
```

Verify: `curl -s http://localhost:5002/health | python3 -m json.tool`

---

## Step 4 — Firewall

Allow staging port from your development machine only (not the whole network):

```bash
sudo ufw allow from <dev_machine_ip> to any port 5002
```

---

## Step 5 — Deploy Workflow

Every change goes through this pipeline before touching production:

```
GitHub (db-optimized branch)
        │
        ▼
   Staging server          ← deploy here first
        │
   Run regression tests    ← python app_regression_test.py
        │
   Manual smoke test       ← log in, run a simulation, upload a file
        │
        ▼
  Production server        ← deploy only after staging passes
```

### Deploy to staging

```bash
# On staging server
cd /opt/mgg/MGG_SYS
git fetch origin
git checkout db-optimized
git pull origin db-optimized

source venv/bin/activate
pip install -r requirements.txt --quiet

# Run any new migrations
python migrations/sqlite_to_postgresql.py   # idempotent — safe to re-run

# Run regression tests against staging DB
python app_regression_test.py

# Restart the service
sudo systemctl restart mgg-staging
```

### Deploy to production (after staging passes)

```bash
# On production server
cd /opt/mgg/MGG_SYS
git pull origin db-optimized
source venv/bin/activate
pip install -r requirements.txt --quiet
python migrations/sqlite_to_postgresql.py
sudo systemctl restart mgg
```

---

## Step 6 — Database Snapshots for Staging

To test with production-like data, periodically restore a sanitised production backup to staging:

```bash
# On production — take a backup
python scripts/backup.py

# Copy the dump to staging
scp instance/backups/mgg_backup_<timestamp>.dump staging_user@staging_host:/tmp/

# On staging — restore
pg_restore --dbname=postgresql://mgg_user_staging:staging_password_change_me@localhost:5432/mgg_simulation_staging \
           --clean --if-exists /tmp/mgg_backup_<timestamp>.dump
```

> If the production backup contains real employee data, sanitise it first:
> ```sql
> UPDATE "user" SET phone = NULL, username = 'user_' || id;
> ```

---

## Step 7 — Load Testing (100-user scenario)

Before each major release, run a load test on staging to verify the 100-user target:

### Install locust

```bash
pip install locust
```

### Create `locustfile.py` (run from project root)

```python
from locust import HttpUser, task, between

class LabUser(HttpUser):
    wait_time = between(2, 8)
    host = "http://staging_host:5002"

    def on_start(self):
        self.client.post("/auth/login", data={
            "employee_id": "admin",
            "password": "StagingAdmin1!",
        })

    @task(3)
    def view_simulation(self):
        self.client.get("/simulation/")

    @task(2)
    def view_work_orders(self):
        self.client.get("/work_order/list")

    @task(1)
    def health_check(self):
        self.client.get("/health")
```

### Run load test

```bash
locust --headless -u 100 -r 10 --run-time 60s --host http://staging_host:5002
```

**Pass criteria:**
- 0% error rate
- p95 response time < 2 seconds
- No `pool_timeout` errors in gunicorn logs

---

## Step 8 — Backup Verification Drill

Run this on staging quarterly (or before every production shipment):

```bash
# 1. Take a backup
python scripts/backup.py

# 2. Find the dump file
DUMP=$(ls -t instance/backups/mgg_backup_*.dump | head -1)

# 3. Restore to a test database
sudo -u postgres createdb mgg_restore_test
pg_restore --dbname=postgresql://mgg_user_staging:staging_password_change_me@localhost:5432/mgg_restore_test \
           --no-owner --clean --if-exists "$DUMP"

# 4. Verify row counts match
psql postgresql://mgg_user_staging:staging_password_change_me@localhost:5432/mgg_simulation_staging \
     -c "SELECT COUNT(*) FROM \"user\"; SELECT COUNT(*) FROM simulation; SELECT COUNT(*) FROM test_result;"

psql postgresql://mgg_user_staging:staging_password_change_me@localhost:5432/mgg_restore_test \
     -c "SELECT COUNT(*) FROM \"user\"; SELECT COUNT(*) FROM simulation; SELECT COUNT(*) FROM test_result;"

# 5. Both outputs should match. Clean up.
sudo -u postgres dropdb mgg_restore_test
```

---

## Summary Checklist

- [ ] Staging hardware provisioned (≥8-core, 16 GB RAM)
- [ ] OS and dependencies installed (follow NETWORK_DEPLOYMENT.md Steps 1–5)
- [ ] PostgreSQL staging database created (`mgg_simulation_staging`)
- [ ] `.env` created with staging credentials (different from production)
- [ ] systemd `mgg-staging.service` running on port 5002
- [ ] `/health` returns `{"status": "ok"}` on staging
- [ ] Deploy workflow documented and understood by all team members
- [ ] Load test run with 100 virtual users — 0% error rate
- [ ] Backup restore drill completed successfully
