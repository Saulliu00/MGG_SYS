# Network Configuration and Deployment Guide

## Overview

MGG_SYS has been configured for multi-user access over local networks with comprehensive timeout handling, session management, and health monitoring.

## Features

### 1. Logo Generation
- **Automatic Generation**: System logo and favicon are automatically generated at startup
- **Location**: `app/static/assets/logos/`
- **Files**:
  - `mgg_logo.png` - Main logo (200x200 px)
  - `favicon.ico` - Browser favicon (32x32 px)
- **Customization**: Edit `app/utils/logo_generator.py` to customize colors, text, or style

### 2. Request Timeout Configuration

Different endpoints have different timeout values based on their expected execution time:

| Endpoint Type | Timeout | Description |
|--------------|---------|-------------|
| Default | 30s | Standard requests |
| Simulation | 120s | Long-running simulations |
| File Upload | 60s | File upload operations |
| Database Query | 10s | Database operations |
| Static Files | 5s | Static file serving |

**Configuration**: `app/config/network_config.py` - `TIMEOUTS` dictionary

### 3. Multi-User Access Configuration

#### Session Management
- **Daily Login**: Sessions expire at midnight (local time), requiring daily re-login
- **Session Timeout**: 1 hour (3600 seconds) for inactivity
- **Permanent Session**: 24 hours (86400 seconds)
- **Cookie Security**:
  - HTTPOnly: Enabled (prevents XSS attacks)
  - SameSite: Lax (CSRF protection)
  - Secure: False (set to True when using HTTPS)

#### Connection Pool
- **Max Connections**: 100 simultaneous connections
- **Keepalive Connections**: 50
- **Keepalive Timeout**: 5 seconds

#### Worker Configuration (Production)
- **Workers**: `CPU cores * 2 + 1` (auto-calculated)
- **Threads per Worker**: 4
- **Worker Class**: sync (can change to gevent/eventlet for async)
- **Max Requests per Worker**: 1000 (auto-restart for memory management)

**Configuration**: `app/config/network_config.py` - `SESSION_CONFIG`, `CONNECTION_POOL`, `WORKER_CONFIG`

### 4. CORS (Cross-Origin Resource Sharing)

Configured for local network access:
- **Origins**: `*` (allow all origins - customize via CORS_ORIGINS env variable)
- **Methods**: GET, POST, PUT, DELETE, OPTIONS
- **Credentials Support**: Enabled
- **Max Age**: 3600 seconds

**Configuration**: `app/config/network_config.py` - `CORS_CONFIG`

### 5. Request Limits

- **Max Content Length**: 16 MB
- **Max Form Memory**: 2 MB

**Configuration**: `app/config/network_config.py` - `REQUEST_LIMITS`

### 6. Network Logging

Automatic logging of:
- Slow requests (threshold: 5 seconds)
- Failed requests
- Network errors

**Configuration**: `app/config/network_config.py` - `NETWORK_LOGGING`

### 7. Health Check Endpoint

**URL**: `GET /health`

**Response**:
```json
{
  "status": "healthy",
  "checks": {
    "database": "ok",
    "file_system": "ok"
  }
}
```

**Status Codes**:
- `200` - Healthy
- `503` - Unhealthy or degraded

**Use Cases**:
- Load balancer health checks
- Monitoring systems
- Container orchestration (Docker, Kubernetes)

## Deployment

### Development (Flask Development Server)

```bash
python run.py
```

Server will start on `http://0.0.0.0:5001` (accessible from local network)

### Production (Gunicorn)

#### Option 1: Using configuration file

```bash
gunicorn -c gunicorn.conf.py run:app
```

#### Option 2: Manual configuration

```bash
gunicorn \
  --bind 0.0.0.0:5001 \
  --workers 9 \
  --threads 4 \
  --timeout 30 \
  --graceful-timeout 30 \
  --access-logfile - \
  --error-logfile - \
  --log-level info \
  run:app
```

#### Option 3: Using systemd service

Create `/etc/systemd/system/mgg-system.service`:

```ini
[Unit]
Description=MGG Simulation System
After=network.target

[Service]
Type=notify
User=www-data
Group=www-data
WorkingDirectory=/path/to/MGG_SYS
Environment="PATH=/path/to/venv/bin"
ExecStart=/path/to/venv/bin/gunicorn -c gunicorn.conf.py run:app
ExecReload=/bin/kill -s HUP $MAINPID
KillMode=mixed
TimeoutStopSec=5
PrivateTmp=true

[Install]
WantedBy=multi-user.target
```

Start the service:

```bash
sudo systemctl daemon-reload
sudo systemctl start mgg-system
sudo systemctl enable mgg-system
sudo systemctl status mgg-system
```

### Docker Deployment

Create `Dockerfile`:

```dockerfile
FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 5001

CMD ["gunicorn", "-c", "gunicorn.conf.py", "run:app"]
```

Build and run:

```bash
docker build -t mgg-system .
docker run -p 5001:5001 --name mgg-system mgg-system
```

## Accessing from Local Network

1. **Find server IP address**:
   ```bash
   ip addr show  # Linux
   ipconfig      # Windows
   ifconfig      # macOS
   ```

2. **Access from other devices**:
   - URL format: `http://<server-ip>:5001`
   - Example: `http://192.168.1.100:5001`

3. **Firewall configuration**:
   ```bash
   # Ubuntu/Debian
   sudo ufw allow 5001/tcp

   # CentOS/RHEL
   sudo firewall-cmd --add-port=5001/tcp --permanent
   sudo firewall-cmd --reload
   ```

## Monitoring and Maintenance

### Health Monitoring

Set up periodic health checks:

```bash
# Cron job example (check every 5 minutes)
*/5 * * * * curl -f http://localhost:5001/health || systemctl restart mgg-system
```

### Log Monitoring

Monitor logs for slow requests:

```bash
# View Gunicorn logs
journalctl -u mgg-system -f

# Filter slow requests
journalctl -u mgg-system | grep "Slow request"
```

### Performance Tuning

1. **Adjust worker count** (in `gunicorn.conf.py`):
   - CPU-bound: workers = CPU cores * 2 + 1
   - I/O-bound: workers = CPU cores * 4 + 1

2. **Adjust timeout values** (in `app/config/network_config.py`):
   - Increase simulation timeout if calculations take longer
   - Decrease default timeout for faster failure detection

3. **Enable connection pooling** for databases:
   - Configure SQLAlchemy pool size in `app/__init__.py`

## Security Considerations

### Production Checklist

- [ ] Change SECRET_KEY from default value
- [ ] Enable HTTPS (set SESSION_COOKIE_SECURE = True)
- [ ] Restrict CORS origins (don't use '*' in production)
- [ ] Use environment variables for sensitive configuration
- [ ] Enable firewall rules
- [ ] Set up regular backups
- [ ] Configure fail2ban for brute force protection
- [ ] Use strong admin passwords (change from 'admin123')

### Environment Variables

Create `.env` file:

```bash
SECRET_KEY=your-secret-key-here
DATABASE_URL=postgresql://user:password@localhost/mgg_db
CORS_ORIGINS=http://192.168.1.0/24
```

Load in app:

```python
from dotenv import load_dotenv
load_dotenv()
```

## Troubleshooting

### Issue: Timeout errors on simulation

**Solution**: Increase simulation timeout in `app/config/network_config.py`:

```python
TIMEOUTS = {
    'simulation': 300,  # Increase to 5 minutes
}
```

### Issue: Cannot access from other devices

**Checks**:
1. Server is bound to `0.0.0.0` (not `127.0.0.1`)
2. Firewall allows port 5001
3. Devices are on same network
4. IP address is correct

### Issue: Health check fails

**Debug**:

```bash
curl -v http://localhost:5001/health
```

Check database connection and file system permissions.

### Issue: Worker timeout

**Solution**: Increase worker timeout in `gunicorn.conf.py`:

```python
timeout = 60  # Increase from 30
```

## Configuration Files Reference

| File | Purpose |
|------|---------|
| `app/config/network_config.py` | Network settings (timeouts, CORS, sessions) |
| `app/config/plot_config.py` | Plotly chart configuration |
| `app/utils/logo_generator.py` | Logo generation logic |
| `app/middleware/timeout.py` | Request timeout middleware |
| `gunicorn.conf.py` | Gunicorn production server config |

## API Endpoints Summary

| Endpoint | Method | Auth | Role | Timeout | Description |
|----------|--------|------|------|---------|-------------|
| `/health` | GET | No | - | 5s | Health check |
| `/auth/login` | GET/POST | No | - | 30s | User login (daily re-login required) |
| `/simulation/` | GET | Yes | Admin/R&D | 30s | Forward simulation page |
| `/simulation/reverse` | GET | Yes | Admin/R&D | 30s | Reverse simulation page |
| `/simulation/run` | POST | Yes | All | 120s | Run simulation |
| `/simulation/upload` | POST | Yes | All | 60s | Upload test data |
| `/simulation/history` | GET | Yes | Admin/Lab | 30s | Experiment results page |
| `/simulation/experiment` | POST | Yes | Admin/Lab | 60s | Batch file upload |
| `/simulation/predict` | POST | Yes | All | 120s | Run prediction |
| `/simulation/generate_comparison_chart` | POST | Yes | All | 30s | Generate chart |
| `/admin/` | GET | Yes | Admin | 30s | User management |
| `/admin/logs` | GET | Yes | Admin | 30s | System logs |

### Role Types
- **Admin**: Full access to all endpoints
- **Lab** (实验工程师): Access to experiment results only
- **R&D** (研发工程师): Access to forward/reverse simulation only

## Support and Updates

- **Issues**: Report at project repository
- **Updates**: Check `NETWORK_DEPLOYMENT.md` for configuration changes
- **Logs**: Check application logs for debugging

## Version History

- **v1.2** (2026-02-07): Three-role RBAC, daily login, experiment batch upload, security fixes
- **v1.1** (2026-01-31): Added network configuration, logo generation, timeout middleware
- **v1.0**: Initial release with basic functionality
