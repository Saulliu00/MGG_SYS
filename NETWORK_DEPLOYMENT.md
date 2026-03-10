# Deployment Guide — MGG Simulation System

Step-by-step instructions for deploying MGG_SYS from GitHub onto a local Ubuntu/Debian server.

---

## Prerequisites

**Hardware (minimum):**
- 16-core CPU, 64 GB RAM, 500 GB disk
- Network interface reachable by all client devices with 10 GbE network card

**Software — install before starting:**
```bash
sudo apt-get update
sudo apt-get install -y git python3 python3-pip python3-venv \
    postgresql-15 postgresql-contrib ufw
```

Confirm versions:
```bash
python3 --version   # must be 3.9+
psql --version      # must be 15+
git --version
```

---

## Step 1 — Clone the Repository

```bash
# Choose a home for the app (adjust path to your preference)
sudo mkdir -p /opt/mgg
sudo chown $USER:$USER /opt/mgg

git clone https://github.com/<your-org>/MGG_SYS.git /opt/mgg/MGG_SYS
cd /opt/mgg/MGG_SYS
```

> Replace `<your-org>` with your actual GitHub organisation or username.

---

## Step 2 — Create Python Virtual Environment

```bash
cd /opt/mgg/MGG_SYS

python3 -m venv venv
source venv/bin/activate

pip install --upgrade pip
pip install -r requirements.txt
```

Verify the key packages installed correctly:
```bash
python -c "import flask, gunicorn, psycopg2, numpy, pandas, plotly; print('OK')"
```

---

## Step 3 — Set Up PostgreSQL Database

**3a. Start and enable PostgreSQL:**
```bash
sudo systemctl start postgresql
sudo systemctl enable postgresql
```

**3b. Create the database and application user:**
```bash
sudo -u postgres psql
```
Inside the `psql` prompt, run:
```sql
CREATE DATABASE mgg_simulation;
CREATE USER mgg_user WITH PASSWORD 'your_secure_password';
GRANT ALL PRIVILEGES ON DATABASE mgg_simulation TO mgg_user;

-- Required on PostgreSQL 15+ (grants schema access)
\c mgg_simulation
GRANT ALL ON SCHEMA public TO mgg_user;

\q
```

**3c. Restrict public access (security hardening):**
```sql
-- Run as postgres user
REVOKE ALL ON DATABASE mgg_simulation FROM PUBLIC;
GRANT CONNECT ON DATABASE mgg_simulation TO mgg_user;
```

**3d. Tune PostgreSQL for your server RAM** (edit `/etc/postgresql/15/main/postgresql.conf`):
```
max_connections = 100
shared_buffers = 16GB         # ~25% of total RAM
work_mem = 256MB
effective_cache_size = 48GB   # ~75% of total RAM
```
Adjust the values above to match your hardware. After editing:
```bash
sudo systemctl restart postgresql
```

---

## Step 4 — Configure Environment Variables

Create a `.env` file in the project root. This file is read automatically by `python-dotenv` on startup.

```bash
cd /opt/mgg/MGG_SYS

# Generate a strong secret key
SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))")

cat > .env << EOF
SECRET_KEY=${SECRET_KEY}
ADMIN_PASSWORD=change_this_to_a_strong_password
DATABASE_URL=postgresql://mgg_user:your_secure_password@localhost:5432/mgg_simulation
EOF

chmod 600 .env
```

> **Important:** `.env` contains credentials — never commit it to git. The repo's `.gitignore` already excludes it.

---

## Step 5 — First Run and Database Initialisation

Start the app once with the Flask dev server to confirm configuration is correct and let it create the database tables automatically:

```bash
cd /opt/mgg/MGG_SYS
source venv/bin/activate
python run.py
```

Expected output:
```
 * Running on http://0.0.0.0:5001
```

In another terminal, verify the database tables were created:
```bash
psql postgresql://mgg_user:your_secure_password@localhost:5432/mgg_simulation \
     -c "\dt"
```
You should see three tables: `user`, `simulation`, `test_result`.

Also confirm the health endpoint responds:
```bash
curl http://localhost:5001/health
# Expected: {"status": "healthy", "checks": {"database": "ok", "file_system": "ok"}}
```

Stop the dev server with `Ctrl+C` once confirmed.

---

## Step 6 — Create a Dedicated System User

Run the application as a non-root, no-login user:

```bash
sudo useradd --system --no-create-home --shell /bin/false mgg
sudo chown -R mgg:mgg /opt/mgg/MGG_SYS
```

---

## Step 7 — Configure the systemd Service

Create the service file:
```bash
sudo nano /etc/systemd/system/mgg-system.service
```

Paste the following (adjust `WorkingDirectory` if you used a different path):
```ini
[Unit]
Description=MGG Simulation System
After=network.target postgresql.service
Requires=postgresql.service

[Service]
Type=notify
User=mgg
Group=mgg
WorkingDirectory=/opt/mgg/MGG_SYS
EnvironmentFile=/opt/mgg/MGG_SYS/.env
Environment="PATH=/opt/mgg/MGG_SYS/venv/bin"
ExecStart=/opt/mgg/MGG_SYS/venv/bin/gunicorn -c gunicorn.conf.py "app:create_app()"
ExecReload=/bin/kill -s HUP $MAINPID
KillMode=mixed
TimeoutStopSec=10
PrivateTmp=true
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Enable and start the service:
```bash
sudo systemctl daemon-reload
sudo systemctl start mgg-system
sudo systemctl enable mgg-system
```

Check it is running:
```bash
sudo systemctl status mgg-system
# Should show: Active: active (running)

curl http://localhost:5001/health
```

---

## Step 8 — Open the Firewall

Allow clients on the local network to reach port 5001:

```bash
sudo ufw allow 5001/tcp
sudo ufw enable
sudo ufw status
```

Find the server's LAN IP address:
```bash
ip addr show | grep "inet " | grep -v 127.0.0.1
# Example output: inet 192.168.1.50/24
```

Any device on the network can now open:
```
http://192.168.1.50:5001
```

---

## Step 9 — Set Up Automated Daily Backup

The `scripts/backup.py` script backs up the database, uploaded Excel files, and application logs. Schedule it via cron:

```bash
# Verify the backup script works first
cd /opt/mgg/MGG_SYS
source venv/bin/activate
python scripts/backup.py
# Output should be saved to instance/backups/

# Schedule daily at 02:00
(crontab -l 2>/dev/null; echo "0 2 * * * cd /opt/mgg/MGG_SYS && /opt/mgg/MGG_SYS/venv/bin/python scripts/backup.py >> /var/log/mgg_backup.log 2>&1") | crontab -
```

Backups land in `instance/backups/` and are pruned after 30 days automatically.

---

## Step 10 — Verify the Full Deployment

**From the server:**
```bash
curl -s http://localhost:5001/health | python3 -m json.tool
```

**From a client device on the network:**
1. Open `http://<server-ip>:5001` in a browser
2. Log in with:
   - Employee ID: `admin`
   - Password: the value you set for `ADMIN_PASSWORD` in `.env`
3. Navigate to the Admin panel and confirm user management works
4. Run a test simulation from the 正向 page

**Check service logs if anything fails:**
```bash
journalctl -u mgg-system -f
```

---

## Updating to a New Version

```bash
cd /opt/mgg/MGG_SYS

# Pull latest code
sudo -u mgg git pull origin master

# Install any new dependencies
sudo -u mgg /opt/mgg/MGG_SYS/venv/bin/pip install -r requirements.txt

# Restart the service (zero-downtime reload)
sudo systemctl reload mgg-system
# If reload fails, do a full restart:
sudo systemctl restart mgg-system

# Confirm health
curl http://localhost:5001/health
```

---

## Service Management Reference

| Task | Command |
|------|---------|
| Start | `sudo systemctl start mgg-system` |
| Stop | `sudo systemctl stop mgg-system` |
| Restart | `sudo systemctl restart mgg-system` |
| Zero-downtime reload | `sudo systemctl reload mgg-system` |
| View live logs | `journalctl -u mgg-system -f` |
| View last 100 log lines | `journalctl -u mgg-system -n 100` |
| Disable autostart | `sudo systemctl disable mgg-system` |

Application CSV logs (request/error detail):
```bash
ls -lt /opt/mgg/MGG_SYS/app/log/
```

---

## Troubleshooting

| Symptom | Check |
|---------|-------|
| `systemctl status` shows `failed` | `journalctl -u mgg-system -n 50` — look for Python import errors or missing `.env` |
| `curl localhost:5001` → connection refused | Service not running; check status above |
| Can't reach from another device | `sudo ufw status` — port 5001 must be `ALLOW`; confirm bind is `0.0.0.0` in `gunicorn.conf.py` |
| `database "ok"` missing in `/health` | PostgreSQL not running: `sudo systemctl status postgresql`; verify `DATABASE_URL` in `.env` |
| `authentication failed for user "mgg_user"` | Password in `.env` doesn't match what was set in `psql`; re-run `ALTER USER mgg_user WITH PASSWORD '...'` |
| Worker timeout on simulation run | Increase `TIMEOUTS['simulation']` in `app/config/network_config.py` and redeploy |
| `pool_timeout` errors under load | Reduce `workers × threads` in `app/config/network_config.py` or increase `pool_size` |

---

## Security Checklist

Before handing over to users, confirm every item:

- [ ] `SECRET_KEY` in `.env` is a random 64-character hex string (not the auto-generated dev key)
- [ ] `ADMIN_PASSWORD` in `.env` is changed from the default `admin123`
- [ ] `.env` file permissions are `600` (`chmod 600 .env`)
- [ ] Service runs as `mgg` user, not `root`
- [ ] Firewall allows only port 5001 (plus SSH 22)
- [ ] PostgreSQL `mgg_user` password is strong and not reused
- [ ] Automated daily backup cron job is active (`crontab -l`)
- [ ] `curl http://localhost:5001/health` returns `"status": "healthy"`

---

## Configuration Files Reference

| File | Purpose |
|------|---------|
| `.env` | Secrets and database URL — **never commit** |
| `gunicorn.conf.py` | Gunicorn worker count, timeouts, logging |
| `app/config/network_config.py` | Timeouts, CORS, session settings, DB pool |
| `app/config/plot_config.py` | Plotly chart defaults |
| `database/SETUP.md` | PostgreSQL advanced tuning and backup detail |
