# Network Deployment Guide

Complete guide for deploying MGG_SYS on a local network — development through production.

---

## Quick Start

### Development (Flask dev server)

```bash
source venv/bin/activate
export SECRET_KEY=$(python -c "import secrets; print(secrets.token_hex(32))")
python run.py
```

Server starts on `http://0.0.0.0:5001` — accessible from any device on the local network.

### Production (Gunicorn)

```bash
export SECRET_KEY=<your-secret-key>
export ADMIN_PASSWORD=<your-admin-password>
gunicorn -c gunicorn.conf.py "app:create_app()"
```

---

## Configuration Reference

All network settings live in [app/config/network_config.py](app/config/network_config.py).

### Worker Configuration

| Setting | Value | Notes |
|---------|-------|-------|
| Workers | `min(cpu_count + 1, 5)` | Capped at 5 to stay within DB pool |
| Threads per worker | 5 | 25 total concurrent handlers |
| Worker class | sync | |
| Timeout | 120 s | Covers simulation subprocess calls |
| Max requests | 1000 + jitter 50 | Auto-restart for memory management |

### Request Timeouts

| Endpoint type | Timeout |
|---------------|---------|
| Default | 30 s |
| Simulation / prediction | 120 s |
| File upload | 60 s |
| Database query | 10 s |
| Static files | 5 s |

### Session Management

| Setting | Value |
|---------|-------|
| Session inactivity timeout | 1 hour (3600 s) |
| Daily re-login | Sessions expire at midnight |
| Cookie HTTPOnly | Yes (XSS protection) |
| Cookie SameSite | Lax (CSRF protection) |
| Cookie Secure | False — set `True` when using HTTPS |

### Database Connection Pool

Configured in `app/config/network_config.py` (SQLAlchemy settings in `app/__init__.py`):

| Setting | Value | Description |
|---------|-------|-------------|
| pool_size | 25 | Persistent connections |
| max_overflow | 25 | Burst capacity (50 total max) |
| pool_timeout | 10 s | Fail fast on exhaustion |
| pool_recycle | 3600 s | Recycle idle connections hourly |
| pool_pre_ping | True | Discard stale connections |

5 workers × 5 threads = 25 handlers, matching pool_size exactly — no contention.

### CORS

Configured for local network access. Default allows all origins (`*`).
Override via environment variable:

```bash
export CORS_ORIGINS=http://192.168.1.0/24
```

### Request Limits

| Setting | Value |
|---------|-------|
| Max upload size | 16 MB |
| Max form memory | 2 MB |

---

## Production Deployment Options

### Option 1: Gunicorn with config file (recommended)

```bash
gunicorn -c gunicorn.conf.py "app:create_app()"
```

### Option 2: Manual Gunicorn

```bash
gunicorn \
  --bind 0.0.0.0:5001 \
  --workers 5 \
  --threads 5 \
  --timeout 120 \
  --graceful-timeout 30 \
  --max-requests 1000 \
  --preload \
  --access-logfile - \
  --error-logfile - \
  "app:create_app()"
```

### Option 3: systemd service

Create `/etc/systemd/system/mgg-system.service`:

```ini
[Unit]
Description=MGG Simulation System
After=network.target

[Service]
Type=notify
User=www-data
Group=www-data
WorkingDirectory=/home/saul_liu/Desktop/MGG_SYS
Environment="PATH=/home/saul_liu/Desktop/MGG_SYS/venv/bin"
Environment="SECRET_KEY=<your-secret-key>"
Environment="ADMIN_PASSWORD=<your-admin-password>"
ExecStart=/home/saul_liu/Desktop/MGG_SYS/venv/bin/gunicorn -c gunicorn.conf.py "app:create_app()"
ExecReload=/bin/kill -s HUP $MAINPID
KillMode=mixed
TimeoutStopSec=5
PrivateTmp=true
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl start mgg-system
sudo systemctl enable mgg-system
sudo systemctl status mgg-system
```

---

## Accessing from the Local Network

1. **Find server IP:**
   ```bash
   ip addr show   # Linux
   ```

2. **Open from any device on the network:**
   ```
   http://<server-ip>:5001
   ```

3. **Open firewall port (Ubuntu/Debian):**
   ```bash
   sudo ufw allow 5001/tcp
   ```

---

## API Endpoints

| Method | Route | Auth | Role | Description |
|--------|-------|------|------|-------------|
| GET | `/health` | No | — | Health check |
| GET/POST | `/auth/login` | No | — | Login |
| GET | `/auth/logout` | Yes | All | Logout |
| GET | `/simulation/` | Yes | Admin, R&D | Forward simulation page |
| POST | `/simulation/run` | Yes | All | Run simulation |
| POST | `/simulation/upload` | Yes | All | Upload test file |
| POST | `/simulation/predict` | Yes | All | Reverse prediction |
| GET | `/simulation/history` | Yes | Admin, Lab | Experiment results |
| POST | `/simulation/experiment` | Yes | Admin, Lab | Batch file upload |
| POST | `/simulation/generate_comparison_chart` | Yes | All | PT comparison chart |
| GET | `/work_order/` | Yes | Admin, R&D | Work order query page |
| GET | `/work_order/list` | Yes | Admin, R&D | List all work orders |
| GET | `/work_order/<wo>/detail` | Yes | Admin, R&D | Work order detail + chart |
| DELETE | `/work_order/test_result/<id>` | Yes | Admin, R&D | Delete test result |
| DELETE | `/work_order/<wo>` | Yes | Admin, R&D | Delete work order |
| GET | `/admin/` | Yes | Admin | User management |
| GET | `/admin/logs` | Yes | Admin | System logs |

**Roles:** `admin` · `research_engineer` (R&D) · `lab_engineer` (Lab)

---

## Health Check

```bash
curl http://localhost:5001/health
```

```json
{
  "status": "healthy",
  "checks": {
    "database": "ok",
    "file_system": "ok"
  }
}
```

Returns `200` (healthy) or `503` (degraded).

Cron-based monitoring:
```bash
# Restart if unhealthy (check every 5 minutes)
*/5 * * * * curl -sf http://localhost:5001/health || systemctl restart mgg-system
```

---

## Log Monitoring

```bash
# Gunicorn via systemd
journalctl -u mgg-system -f

# Application CSV logs (includes request, action, error columns)
ls -lt /home/saul_liu/Desktop/MGG_SYS/app/log/
```

Slow requests (> 5 s) are logged automatically. The middleware logs include:
`timestamp, level, username, method, endpoint, path, status_code, duration_ms, action, error`

---

## Security Checklist (Production)

- [ ] Set `SECRET_KEY` to a random 64-char hex string
- [ ] Set `ADMIN_PASSWORD` via env var (change from `admin123`)
- [ ] Set `CORS_ORIGINS` to specific IP range instead of `*`
- [ ] Set `SESSION_COOKIE_SECURE = True` when using HTTPS
- [ ] Open only port 5001 in firewall (or 443 behind nginx)
- [ ] Run as a non-root user
- [ ] Enable database backups (see `database/SETUP.md`)
- [ ] For PostgreSQL: restrict access per `database/SETUP.md` security section

---

## Performance Tuning

### Adjust worker count

```python
# app/config/network_config.py
WORKER_CONFIG = {
    'workers': 5,   # Increase if CPU allows; keep ≤ pool_size / threads
    'threads': 5,
    ...
}
```

### Increase simulation timeout

```python
TIMEOUTS = {
    'simulation': 300,  # 5 minutes for heavy jobs
}
```

### PostgreSQL tuning (64 GB RAM server)

```
# postgresql.conf
max_connections = 100
shared_buffers = 16GB        # 25% of RAM
work_mem = 256MB
effective_cache_size = 48GB  # 75% of RAM
```

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| `Connection refused` | Check server is running: `systemctl status mgg-system` |
| Can't reach from other devices | Confirm bind is `0.0.0.0`, not `127.0.0.1`; check firewall |
| Worker timeout on simulation | Increase `TIMEOUTS['simulation']` and Gunicorn `timeout` |
| `database is locked` (SQLite) | Reduce workers or migrate to PostgreSQL |
| `pool_timeout` errors | Reduce worker×thread count or increase `pool_size` |
| Slow first request | `preload_app = True` in `gunicorn.conf.py` (already enabled) |

---

## Configuration Files

| File | Purpose |
|------|---------|
| `app/config/network_config.py` | Timeouts, CORS, sessions, workers, connection pool |
| `app/config/plot_config.py` | Plotly chart defaults |
| `gunicorn.conf.py` | Gunicorn production server |
| `app/middleware/logging_middleware.py` | Request/error logging |
| `.env` | Environment variables (SECRET_KEY, DATABASE_URL, etc.) |
