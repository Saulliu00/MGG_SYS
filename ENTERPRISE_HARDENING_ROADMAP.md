# MGG_SYS Enterprise Hardening Roadmap
## Single-Server Internal Deployment (100 Daily Users)

**Document Version:** 1.0  
**Date:** 2026-02-22  
**Target Environment:** Single server, local network only (air-gapped)  
**Target Users:** 100 concurrent daily users (internal)  
**Current Framework:** Flask 3.0.0 + PostgreSQL + Gunicorn

---

## 📋 **Executive Summary**

**Deployment Context:**
- ✅ Internal use only (company LAN)
- ✅ Single physical server
- ✅ No internet connectivity (air-gapped)
- ✅ 100 daily users (engineers + lab staff)
- ✅ Critical business data (simulation results)

**Goal:** Transform MGG_SYS from development-ready to **production-hardened** for daily mission-critical use.

**Key Priorities:**
1. **Data protection** - Prevent catastrophic data loss
2. **High availability** - Minimize downtime for 100 users
3. **Performance** - Handle concurrent load smoothly
4. **Reliability** - Stable operation 24/7
5. **Maintainability** - Easy to troubleshoot and upgrade

**Total Effort:** 6-8 weeks  
**Budget:** ~$15,000 (hardware + labor)

---

## 🎯 **Why This Matters**

### **Current Risks (Single Server, 100 Users):**

| Risk | Impact | Probability | Current State |
|------|--------|-------------|---------------|
| **Hardware failure → data loss** | CRITICAL | Medium | ❌ No backups |
| **System overload (100 users)** | HIGH | High | ❌ No load management |
| **Silent failures** | HIGH | High | ❌ No monitoring |
| **Deployment errors** | MEDIUM | High | ❌ Manual deployment |
| **Regression bugs** | MEDIUM | Medium | ❌ No automated tests |
| **Long recovery time** | HIGH | Medium | ❌ No disaster plan |

### **After Hardening:**

| Area | Current | Target | Improvement |
|------|---------|--------|-------------|
| **Uptime** | ~95% | **99.5%** | 10x less downtime |
| **Data safety** | At risk | **Protected** | Daily backups |
| **Recovery time** | Hours | **< 15 min** | 20x faster |
| **User capacity** | 20-30 | **100+** | 5x more |
| **Failure detection** | Manual | **< 5 min** | Automated |

---

## 🗂️ **Implementation Phases**

### **Phase 1: Critical Foundation (Weeks 1-2)**
**Priority:** P0 - Must have  
**Focus:** Data protection + stability

### **Phase 2: Performance & Reliability (Weeks 3-4)**
**Priority:** P1 - Should have  
**Focus:** Handle 100 users smoothly

### **Phase 3: Quality & Maintenance (Weeks 5-8)**
**Priority:** P2 - Nice to have  
**Focus:** Long-term maintainability

---

## 🚨 **PHASE 1: Critical Foundation (Weeks 1-2)**

### **1.1 Automated Database Backups**

**Why:** Prevent catastrophic data loss (simulation results are irreplaceable)

**Current Risk:** Hardware failure = complete data loss

#### **Implementation:**

**A. Daily PostgreSQL Backups**

```bash
#!/bin/bash
# /opt/mgg_backup/scripts/daily_backup.sh

# Configuration
BACKUP_DIR="/mnt/nas/mgg_backups/postgres"
DATE=$(date +%Y%m%d_%H%M%S)
DB_NAME="mgg_simulation"
DB_USER="mgg_user"
RETENTION_DAYS=90

# Create backup directory
mkdir -p $BACKUP_DIR

# Perform backup
pg_dump -U $DB_USER -h localhost $DB_NAME | gzip > $BACKUP_DIR/backup_$DATE.sql.gz

# Verify backup integrity
gunzip -t $BACKUP_DIR/backup_$DATE.sql.gz
if [ $? -eq 0 ]; then
    echo "[$(date)] Backup successful: backup_$DATE.sql.gz" >> /var/log/mgg_backup.log
else
    echo "[$(date)] ERROR: Backup verification failed!" >> /var/log/mgg_backup.log
    # Send email alert (internal mail server)
    mail -s "MGG Backup Failed" admin@company.internal < /dev/null
fi

# Remove backups older than retention period
find $BACKUP_DIR -name "backup_*.sql.gz" -mtime +$RETENTION_DAYS -delete

# Backup to secondary location (USB drive or secondary NAS)
rsync -av $BACKUP_DIR/ /mnt/backup_drive/mgg_postgres/
```

**Cron Schedule:**
```bash
# Run daily at 2 AM (low usage time)
0 2 * * * /opt/mgg_backup/scripts/daily_backup.sh
```

**B. Application Data Backup**

```bash
#!/bin/bash
# /opt/mgg_backup/scripts/backup_app_data.sh

BACKUP_ROOT="/mnt/nas/mgg_backups"
DATE=$(date +%Y%m%d)

# Backup uploaded files
rsync -av --delete /opt/mgg_sys/app/static/uploads/ $BACKUP_ROOT/uploads_$DATE/

# Backup system logs
rsync -av --delete /opt/mgg_sys/app/log/ $BACKUP_ROOT/logs_$DATE/

# Backup Parquet archives
rsync -av --delete /opt/mgg_sys/parquet_archive/ $BACKUP_ROOT/parquet_$DATE/

# Backup configuration
tar -czf $BACKUP_ROOT/config_$DATE.tar.gz /opt/mgg_sys/config.py /opt/mgg_sys/.env

echo "[$(date)] Application backup completed" >> /var/log/mgg_backup.log
```

**Cron Schedule:**
```bash
# Run daily at 3 AM (after database backup)
0 3 * * * /opt/mgg_backup/scripts/backup_app_data.sh
```

**C. Point-in-Time Recovery (WAL Archiving)**

Enable PostgreSQL WAL archiving for disaster recovery:

```bash
# /etc/postgresql/*/main/postgresql.conf

wal_level = replica
archive_mode = on
archive_command = 'test ! -f /mnt/nas/mgg_backups/wal_archive/%f && cp %p /mnt/nas/mgg_backups/wal_archive/%f'
archive_timeout = 300  # Archive every 5 minutes
```

**Restart PostgreSQL:**
```bash
sudo systemctl restart postgresql
```

#### **Testing Backup Restoration:**

```bash
#!/bin/bash
# /opt/mgg_backup/scripts/test_restore.sh

# Restore to test database
TEST_DB="mgg_test_restore"

# Drop test database if exists
psql -U postgres -c "DROP DATABASE IF EXISTS $TEST_DB;"

# Create test database
psql -U postgres -c "CREATE DATABASE $TEST_DB;"

# Restore latest backup
LATEST_BACKUP=$(ls -t /mnt/nas/mgg_backups/postgres/backup_*.sql.gz | head -1)
gunzip -c $LATEST_BACKUP | psql -U postgres -d $TEST_DB

# Verify data integrity
RECORD_COUNT=$(psql -U postgres -d $TEST_DB -t -c "SELECT COUNT(*) FROM forward_simulations;")

if [ $RECORD_COUNT -gt 0 ]; then
    echo "[$(date)] Restore test PASSED: $RECORD_COUNT records found" >> /var/log/mgg_backup.log
else
    echo "[$(date)] Restore test FAILED: No records found!" >> /var/log/mgg_backup.log
fi

# Cleanup
psql -U postgres -c "DROP DATABASE $TEST_DB;"
```

**Run monthly:**
```bash
# Test restore on 1st of every month at 4 AM
0 4 1 * * /opt/mgg_backup/scripts/test_restore.sh
```

#### **Hardware Requirements:**

- **NAS/Network Storage:** 2TB minimum (for backups)
- **Secondary Backup:** External USB drive or secondary NAS (offsite if possible)

#### **Deliverables:**
- ✅ Automated daily PostgreSQL backups
- ✅ Application data backups (uploads, logs, config)
- ✅ WAL archiving for point-in-time recovery
- ✅ Monthly restore testing
- ✅ Backup monitoring and alerting

**Time:** 3 days  
**Cost:** NAS storage (~$500) + 3 days labor  
**Impact:** Eliminates data loss risk

---

### **1.2 System Monitoring & Health Checks**

**Why:** Detect failures before users notice

**Current Risk:** System failures go unnoticed for hours

#### **Implementation:**

**A. Enhanced Health Check Endpoint**

```python
# app/routes/main.py

import psutil
import shutil
from datetime import datetime
from flask import Blueprint, jsonify
from sqlalchemy import text

bp = Blueprint('main', __name__)

@bp.route('/health')
def health_check():
    """Comprehensive health check for monitoring"""
    health = {
        'status': 'healthy',
        'timestamp': datetime.utcnow().isoformat(),
        'version': '1.0.0',
        'checks': {}
    }
    
    # 1. Database connectivity
    try:
        from app import db
        db.session.execute(text('SELECT 1'))
        health['checks']['database'] = {
            'status': 'ok',
            'message': 'PostgreSQL connected'
        }
    except Exception as e:
        health['checks']['database'] = {
            'status': 'error',
            'message': str(e)
        }
        health['status'] = 'unhealthy'
    
    # 2. Database connection pool
    try:
        pool = db.engine.pool
        pool_status = {
            'size': pool.size(),
            'checked_in': pool.checkedin(),
            'checked_out': pool.checkedout(),
            'overflow': pool.overflow(),
        }
        utilization = (pool.checkedout() / pool.size()) * 100
        
        if utilization > 80:
            health['checks']['connection_pool'] = {
                'status': 'warning',
                'message': f'High utilization: {utilization:.1f}%',
                'details': pool_status
            }
            health['status'] = 'degraded'
        else:
            health['checks']['connection_pool'] = {
                'status': 'ok',
                'message': f'Utilization: {utilization:.1f}%',
                'details': pool_status
            }
    except Exception as e:
        health['checks']['connection_pool'] = {
            'status': 'error',
            'message': str(e)
        }
    
    # 3. Disk space
    try:
        disk_usage = shutil.disk_usage('/')
        free_gb = disk_usage.free / (1024**3)
        total_gb = disk_usage.total / (1024**3)
        percent_used = (disk_usage.used / disk_usage.total) * 100
        
        if free_gb < 10:
            health['checks']['disk_space'] = {
                'status': 'critical',
                'message': f'Low disk space: {free_gb:.1f}GB free',
                'free_gb': round(free_gb, 1),
                'total_gb': round(total_gb, 1),
                'percent_used': round(percent_used, 1)
            }
            health['status'] = 'unhealthy'
        elif free_gb < 50:
            health['checks']['disk_space'] = {
                'status': 'warning',
                'message': f'Disk space low: {free_gb:.1f}GB free',
                'free_gb': round(free_gb, 1),
                'total_gb': round(total_gb, 1),
                'percent_used': round(percent_used, 1)
            }
            if health['status'] == 'healthy':
                health['status'] = 'degraded'
        else:
            health['checks']['disk_space'] = {
                'status': 'ok',
                'message': f'{free_gb:.1f}GB free',
                'free_gb': round(free_gb, 1),
                'total_gb': round(total_gb, 1),
                'percent_used': round(percent_used, 1)
            }
    except Exception as e:
        health['checks']['disk_space'] = {
            'status': 'error',
            'message': str(e)
        }
    
    # 4. Memory usage
    try:
        mem = psutil.virtual_memory()
        if mem.percent > 95:
            health['checks']['memory'] = {
                'status': 'critical',
                'message': f'Memory critical: {mem.percent:.1f}% used',
                'percent': mem.percent,
                'available_gb': round(mem.available / (1024**3), 1)
            }
            health['status'] = 'unhealthy'
        elif mem.percent > 85:
            health['checks']['memory'] = {
                'status': 'warning',
                'message': f'Memory high: {mem.percent:.1f}% used',
                'percent': mem.percent,
                'available_gb': round(mem.available / (1024**3), 1)
            }
            if health['status'] == 'healthy':
                health['status'] = 'degraded'
        else:
            health['checks']['memory'] = {
                'status': 'ok',
                'message': f'{mem.percent:.1f}% used',
                'percent': mem.percent,
                'available_gb': round(mem.available / (1024**3), 1)
            }
    except Exception as e:
        health['checks']['memory'] = {
            'status': 'error',
            'message': str(e)
        }
    
    # 5. CPU usage
    try:
        cpu_percent = psutil.cpu_percent(interval=1)
        if cpu_percent > 90:
            health['checks']['cpu'] = {
                'status': 'warning',
                'message': f'CPU high: {cpu_percent:.1f}%',
                'percent': cpu_percent
            }
            if health['status'] == 'healthy':
                health['status'] = 'degraded'
        else:
            health['checks']['cpu'] = {
                'status': 'ok',
                'message': f'{cpu_percent:.1f}% used',
                'percent': cpu_percent
            }
    except Exception as e:
        health['checks']['cpu'] = {
            'status': 'error',
            'message': str(e)
        }
    
    # 6. Application services
    try:
        # Check if simulation service is responsive
        from app import app as flask_app
        sim_service = flask_app.simulation_service
        # Quick sanity check
        health['checks']['simulation_service'] = {
            'status': 'ok',
            'message': 'Service initialized'
        }
    except Exception as e:
        health['checks']['simulation_service'] = {
            'status': 'error',
            'message': str(e)
        }
        health['status'] = 'unhealthy'
    
    # Return appropriate HTTP status code
    status_code = 200
    if health['status'] == 'unhealthy':
        status_code = 503
    elif health['status'] == 'degraded':
        status_code = 200  # Still operational
    
    return jsonify(health), status_code
```

**Add to requirements.txt:**
```
psutil==5.9.6
```

**B. Simple Monitoring Script (No Internet Required)**

```bash
#!/bin/bash
# /opt/mgg_monitor/check_health.sh

HEALTH_URL="http://localhost:5001/health"
LOG_FILE="/var/log/mgg_monitor.log"
ALERT_FILE="/var/log/mgg_alerts.log"

# Query health endpoint
RESPONSE=$(curl -s -w "\n%{http_code}" $HEALTH_URL)
HTTP_CODE=$(echo "$RESPONSE" | tail -1)
BODY=$(echo "$RESPONSE" | head -n -1)

# Check HTTP status
if [ "$HTTP_CODE" -eq 200 ]; then
    echo "[$(date)] HEALTHY" >> $LOG_FILE
elif [ "$HTTP_CODE" -eq 503 ]; then
    echo "[$(date)] UNHEALTHY: $BODY" >> $ALERT_FILE
    # Send email alert
    echo "$BODY" | mail -s "MGG System UNHEALTHY" admin@company.internal
else
    echo "[$(date)] ERROR: HTTP $HTTP_CODE" >> $ALERT_FILE
fi

# Parse response for specific issues
echo "$BODY" | jq -r '.checks | to_entries[] | select(.value.status != "ok") | "[$(date)] \(.key): \(.value.message)"' >> $ALERT_FILE 2>/dev/null
```

**Cron Schedule:**
```bash
# Check every 5 minutes
*/5 * * * * /opt/mgg_monitor/check_health.sh
```

**C. Log Rotation Configuration**

```bash
# /etc/logrotate.d/mgg_sys

/var/log/mgg_*.log {
    daily
    rotate 90
    compress
    delaycompress
    notifempty
    create 0640 mgg_user mgg_group
    sharedscripts
    postrotate
        systemctl reload mgg_sys
    endscript
}

/opt/mgg_sys/app/log/*.csv {
    daily
    rotate 365
    compress
    delaycompress
    notifempty
    maxsize 100M
}
```

#### **Deliverables:**
- ✅ Comprehensive /health endpoint
- ✅ Automated health monitoring (every 5 minutes)
- ✅ Alert system for failures
- ✅ Log rotation configured

**Time:** 2 days  
**Cost:** 2 days labor  
**Impact:** Detect failures within 5 minutes

---

### **1.3 Production-Grade Gunicorn Configuration**

**Why:** Handle 100 concurrent users reliably

**Current Risk:** Default config will crash under load

#### **Implementation:**

```python
# gunicorn.conf.py (PRODUCTION)

import multiprocessing
import os

# Server Socket
bind = '0.0.0.0:5001'
backlog = 2048  # Pending connections queue

# Worker Processes
workers = min(multiprocessing.cpu_count() * 2 + 1, 8)  # Typically 5-9 workers
worker_class = 'sync'  # Use 'gevent' for I/O bound, 'sync' for CPU bound
worker_connections = 1000
max_requests = 1000  # Restart workers after 1000 requests (prevent memory leaks)
max_requests_jitter = 50  # Add randomness to avoid all workers restarting at once
timeout = 120  # Request timeout (120s for simulations)
keepalive = 5

# Logging
accesslog = '/var/log/mgg/gunicorn_access.log'
errorlog = '/var/log/mgg/gunicorn_error.log'
loglevel = 'info'
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# Process Naming
proc_name = 'mgg_simulation'

# Server Mechanics
daemon = False  # Systemd will handle daemonization
pidfile = '/var/run/mgg_sys.pid'
user = 'mgg_user'
group = 'mgg_group'
umask = 0o007

# Preload Application
preload_app = True  # Load application before forking (saves memory)

# Worker Lifecycle Hooks
def on_starting(server):
    """Called just before the master process is initialized"""
    server.log.info("Gunicorn master starting")

def on_reload(server):
    """Called to recycle workers during a reload via SIGHUP"""
    server.log.info("Gunicorn reloading")

def worker_int(worker):
    """Called when a worker receives the SIGINT or SIGQUIT signal"""
    worker.log.info("Worker received INT or QUIT signal")

def worker_abort(worker):
    """Called when a worker receives the SIGABRT signal"""
    worker.log.info("Worker received ABORT signal")
```

**Systemd Service Configuration:**

```ini
# /etc/systemd/system/mgg_sys.service

[Unit]
Description=MGG Simulation System (Gunicorn)
After=network.target postgresql.service
Wants=postgresql.service

[Service]
Type=notify
User=mgg_user
Group=mgg_group
WorkingDirectory=/opt/mgg_sys
Environment="PATH=/opt/mgg_sys/venv/bin"
ExecStart=/opt/mgg_sys/venv/bin/gunicorn -c /opt/mgg_sys/gunicorn.conf.py run:app
ExecReload=/bin/kill -s HUP $MAINPID
KillMode=mixed
KillSignal=SIGTERM
TimeoutStopSec=30
Restart=always
RestartSec=5

# Hardening
PrivateTmp=true
NoNewPrivileges=true

# Logging
StandardOutput=journal
StandardError=journal
SyslogIdentifier=mgg_sys

[Install]
WantedBy=multi-user.target
```

**Enable and Start:**
```bash
sudo systemctl daemon-reload
sudo systemctl enable mgg_sys
sudo systemctl start mgg_sys
sudo systemctl status mgg_sys
```

#### **Log Directory Setup:**

```bash
sudo mkdir -p /var/log/mgg
sudo chown mgg_user:mgg_group /var/log/mgg
sudo chmod 755 /var/log/mgg
```

#### **Deliverables:**
- ✅ Production Gunicorn configuration
- ✅ Systemd service for auto-restart
- ✅ Graceful reloads (zero downtime)
- ✅ Proper logging

**Time:** 1 day  
**Cost:** 1 day labor  
**Impact:** Handle 100 concurrent users, auto-recovery from crashes

---

### **1.4 Database Connection Pooling (Enhanced)**

**Why:** Prevent connection exhaustion with 100 users

**Current Risk:** 10 connection pool too small for 100 users

#### **Implementation:**

```python
# database/db_config.py (UPDATED)

class DatabaseConfig:
    """Database configuration for 100 concurrent users"""
    
    # PostgreSQL Connection
    POSTGRES_USER = os.getenv('POSTGRES_USER', 'mgg_user')
    POSTGRES_PASSWORD = os.getenv('POSTGRES_PASSWORD', 'mgg_password')
    POSTGRES_HOST = os.getenv('POSTGRES_HOST', 'localhost')
    POSTGRES_PORT = os.getenv('POSTGRES_PORT', '5432')
    POSTGRES_DB = os.getenv('POSTGRES_DB', 'mgg_simulation')
    
    # Connection Pool Settings (TUNED FOR 100 USERS)
    POOL_SIZE = int(os.getenv('DB_POOL_SIZE', '50'))  # Base pool
    MAX_OVERFLOW = int(os.getenv('DB_MAX_OVERFLOW', '50'))  # Additional connections
    POOL_TIMEOUT = int(os.getenv('DB_POOL_TIMEOUT', '30'))  # Wait 30s for connection
    POOL_RECYCLE = int(os.getenv('DB_POOL_RECYCLE', '3600'))  # Recycle after 1 hour
    POOL_PRE_PING = True  # Test connections before use (prevents stale connections)
    
    # ... rest of config
```

**PostgreSQL Server Configuration:**

```bash
# /etc/postgresql/*/main/postgresql.conf

# Memory Settings (for 16GB RAM server)
shared_buffers = 4GB                # 25% of RAM
effective_cache_size = 12GB         # 75% of RAM
work_mem = 64MB                     # Per operation
maintenance_work_mem = 1GB

# Connection Settings
max_connections = 150               # Allow up to 150 connections (100 users + overhead)

# Performance
random_page_cost = 1.1              # For SSD
effective_io_concurrency = 200      # For SSD

# Logging
log_line_prefix = '%t [%p]: [%l-1] user=%u,db=%d,app=%a,client=%h '
log_min_duration_statement = 1000   # Log queries > 1s
```

**Restart PostgreSQL:**
```bash
sudo systemctl restart postgresql
```

#### **Connection Pool Monitoring:**

```python
# app/routes/admin.py

@bp.route('/admin/db_stats')
@login_required
@admin_required
def database_stats():
    """Show database connection pool statistics"""
    from app import db
    
    pool = db.engine.pool
    stats = {
        'pool_size': pool.size(),
        'checked_in': pool.checkedin(),
        'checked_out': pool.checkedout(),
        'overflow': pool.overflow(),
        'max_overflow': pool._max_overflow,
        'utilization': (pool.checkedout() / pool.size()) * 100
    }
    
    return render_template('admin/db_stats.html', stats=stats)
```

#### **Deliverables:**
- ✅ 50 base connections + 50 overflow (100 total)
- ✅ Connection pre-ping (prevents stale connections)
- ✅ PostgreSQL tuned for 100 users
- ✅ Connection pool monitoring

**Time:** 1 day  
**Cost:** 1 day labor  
**Impact:** Handle 100 concurrent database queries

---

## **Phase 1 Summary:**

**Total Time:** 7 days (1.4 weeks)  
**Total Cost:** ~$1,000 hardware + 7 days labor  

**Deliverables:**
- ✅ Automated daily backups (PostgreSQL + app data)
- ✅ Point-in-time recovery (WAL archiving)
- ✅ Health monitoring (5-minute checks)
- ✅ Production Gunicorn + Systemd service
- ✅ Database connection pooling (100 users)

**Risk Reduction:**
- ❌ → ✅ Data loss risk: **ELIMINATED**
- ❌ → ✅ Silent failures: **DETECTED in 5 minutes**
- ❌ → ✅ Crashes: **AUTO-RECOVERY**
- ❌ → ✅ Connection exhaustion: **PREVENTED**

---

## ⚡ **PHASE 2: Performance & Reliability (Weeks 3-4)**

### **2.1 NGINX Reverse Proxy**

**Why:** Serve static files faster, enable zero-downtime deployments

**Current Risk:** Gunicorn serves static files (slow), deployments require downtime

#### **Implementation:**

```nginx
# /etc/nginx/sites-available/mgg_simulation

upstream mgg_backend {
    server 127.0.0.1:5001 max_fails=3 fail_timeout=30s;
    keepalive 32;  # Persistent connections
}

server {
    listen 80;
    server_name mgg.company.internal;
    
    # Redirect to HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name mgg.company.internal;
    
    # SSL Configuration (use internal CA)
    ssl_certificate /etc/ssl/certs/mgg.crt;
    ssl_certificate_key /etc/ssl/private/mgg.key;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;
    
    # Security Headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    
    # Upload limits
    client_max_body_size 100M;
    client_body_buffer_size 10M;
    
    # Timeouts
    proxy_connect_timeout 120s;
    proxy_send_timeout 120s;
    proxy_read_timeout 120s;
    send_timeout 120s;
    
    # Static files (served directly by NGINX - 10x faster)
    location /static {
        alias /opt/mgg_sys/app/static;
        expires 30d;
        add_header Cache-Control "public, immutable";
        access_log off;  # Don't log static file requests
    }
    
    # Uploaded files
    location /static/uploads {
        alias /opt/mgg_sys/app/static/uploads;
        expires 7d;
        add_header Cache-Control "public";
    }
    
    # Health check (bypass proxy, direct to app)
    location = /health {
        access_log off;
        proxy_pass http://mgg_backend;
    }
    
    # Application requests
    location / {
        proxy_pass http://mgg_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Failover behavior
        proxy_next_upstream error timeout invalid_header http_500 http_502 http_503;
        proxy_next_upstream_tries 2;
        
        # Buffering
        proxy_buffering on;
        proxy_buffer_size 4k;
        proxy_buffers 8 4k;
    }
    
    # Logging
    access_log /var/log/nginx/mgg_access.log combined;
    error_log /var/log/nginx/mgg_error.log warn;
}
```

**Install & Enable:**
```bash
sudo apt-get install nginx
sudo ln -s /etc/nginx/sites-available/mgg_simulation /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl enable nginx
sudo systemctl start nginx
```

**Self-Signed SSL Certificate (Internal):**
```bash
sudo openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
    -keyout /etc/ssl/private/mgg.key \
    -out /etc/ssl/certs/mgg.crt \
    -subj "/C=CN/ST=State/L=City/O=Company/CN=mgg.company.internal"
```

**Time:** 2 days  
**Cost:** 2 days labor  
**Impact:** 10x faster static files, HTTPS encryption, zero-downtime deploys

---

### **2.2 Application-Level Caching**

**Why:** Reduce database load for repeated queries

**Current Risk:** Every page load queries database (slow)

#### **Implementation:**

```python
# requirements.txt
Flask-Caching==2.1.0

# app/__init__.py
from flask_caching import Cache

cache = Cache()

def create_app():
    app = Flask(__name__)
    
    # Simple cache configuration (in-memory, single server)
    app.config['CACHE_TYPE'] = 'SimpleCache'  # In-memory cache
    app.config['CACHE_DEFAULT_TIMEOUT'] = 300  # 5 minutes
    
    cache.init_app(app)
    
    # ... rest of setup
```

**Cache Usage Examples:**

```python
# app/services/simulation_service.py
from app import cache

class SimulationService:
    
    @cache.memoize(timeout=3600)  # Cache for 1 hour
    def get_simulation_by_id(self, simulation_id):
        """Cache simulation results (rarely change)"""
        return ForwardSimulation.query.get(simulation_id)
    
    @cache.memoize(timeout=86400)  # Cache for 24 hours
    def get_nc_types(self):
        """Cache dropdown options (rarely change)"""
        return db.session.query(NCType).all()
    
    @cache.memoize(timeout=86400)
    def get_gp_types(self):
        """Cache dropdown options"""
        return db.session.query(GPType).all()
    
    def invalidate_cache(self, simulation_id=None):
        """Invalidate cache when data changes"""
        if simulation_id:
            cache.delete_memoized(self.get_simulation_by_id, self, simulation_id)
        else:
            cache.clear()  # Clear all cache

# app/routes/admin.py
@bp.route('/admin/clear_cache', methods=['POST'])
@login_required
@admin_required
def clear_cache():
    """Manual cache clearing"""
    cache.clear()
    flash('Cache cleared successfully', 'success')
    return redirect(url_for('admin.index'))
```

**Cache Statistics:**

```python
# app/routes/admin.py
@bp.route('/admin/cache_stats')
@login_required
@admin_required
def cache_stats():
    """Show cache statistics"""
    stats = {
        'cache_type': app.config['CACHE_TYPE'],
        'default_timeout': app.config['CACHE_DEFAULT_TIMEOUT'],
        # SimpleCache doesn't provide detailed stats, but you can track
        'status': 'active'
    }
    return render_template('admin/cache_stats.html', stats=stats)
```

**Time:** 2 days  
**Cost:** 2 days labor  
**Impact:** 5-10x faster for repeated queries

---

### **2.3 Rate Limiting**

**Why:** Prevent accidental system overload

**Current Risk:** User can spam requests (crash system)

#### **Implementation:**

```python
# requirements.txt
Flask-Limiter==3.5.0

# app/__init__.py
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["500 per day", "100 per hour"],
    storage_uri="memory://"  # In-memory (single server)
)

def create_app():
    app = Flask(__name__)
    
    limiter.init_app(app)
    
    # ... rest of setup

# app/routes/simulation.py
from app import limiter

@bp.route('/simulation/forward', methods=['POST'])
@login_required
@limiter.limit("20 per hour")  # Max 20 simulations per hour per user
def forward_simulation():
    # ... existing code

@bp.route('/upload', methods=['POST'])
@login_required
@limiter.limit("30 per hour")  # Max 30 uploads per hour per user
def upload_file():
    # ... existing code

# app/routes/auth.py
@bp.route('/login', methods=['POST'])
@limiter.limit("10 per minute")  # Prevent brute force
def login():
    # ... existing code
```

**Custom Error Handler:**

```python
# app/__init__.py
@app.errorhandler(429)
def ratelimit_handler(e):
    return render_template('errors/429.html', description=e.description), 429

# app/templates/errors/429.html
{% extends "base.html" %}
{% block content %}
<div class="alert alert-warning">
    <h2>请求过于频繁</h2>
    <p>您的请求超过了系统限制。请稍后再试。</p>
    <p>{{ description }}</p>
</div>
{% endblock %}
```

**Time:** 1 day  
**Cost:** 1 day labor  
**Impact:** Prevent accidental system overload

---

### **2.4 Automated Testing**

**Why:** Catch bugs before production

**Current Risk:** Manual testing only (regressions possible)

#### **Implementation:**

```python
# requirements.txt (add to existing)
pytest==7.4.3
pytest-cov==4.1.0
pytest-flask==1.3.0

# tests/conftest.py (pytest configuration)
import pytest
from app import create_app, db as _db
from app.models import User

@pytest.fixture(scope='session')
def app():
    """Create application for testing"""
    app = create_app()
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['WTF_CSRF_ENABLED'] = False
    
    with app.app_context():
        _db.create_all()
        yield app
        _db.drop_all()

@pytest.fixture
def client(app):
    """Test client"""
    return app.test_client()

@pytest.fixture
def auth_client(client, app):
    """Authenticated test client"""
    with app.app_context():
        # Create test user
        user = User(username='testuser', employee_id='TEST001', role='admin')
        user.set_password('test123')
        _db.session.add(user)
        _db.session.commit()
    
    # Login
    client.post('/auth/login', data={
        'employee_id': 'TEST001',
        'password': 'test123'
    })
    
    return client

# tests/test_auth.py
def test_login_success(client):
    """Test successful login"""
    response = client.post('/auth/login', data={
        'employee_id': 'admin',
        'password': 'admin123'
    })
    assert response.status_code == 302  # Redirect

def test_login_failure(client):
    """Test failed login"""
    response = client.post('/auth/login', data={
        'employee_id': 'invalid',
        'password': 'wrong'
    })
    assert b'Invalid' in response.data

# tests/test_simulation.py
def test_forward_simulation(auth_client, app):
    """Test simulation calculation"""
    response = auth_client.post('/simulation/forward', data={
        'nc_type': 'Type A',
        'nc_amount': 100,
        'gp_type': 'GP-1',
        'gp_amount': 50,
        # ... other params
    })
    assert response.status_code == 200
    assert b'peak_pressure' in response.data

# tests/test_file_upload.py
def test_file_upload(auth_client, tmp_path):
    """Test file upload"""
    # Create temporary Excel file
    import openpyxl
    wb = openpyxl.Workbook()
    ws = wb.active
    ws['A1'] = 'Time'
    ws['B1'] = 'Pressure'
    file_path = tmp_path / "test.xlsx"
    wb.save(file_path)
    
    with open(file_path, 'rb') as f:
        response = auth_client.post('/upload', data={
            'file': (f, 'test.xlsx')
        })
    
    assert response.status_code == 200

# Run tests
# pytest tests/ --cov=app --cov-report=html
```

**Automated Test Script:**

```bash
#!/bin/bash
# /opt/mgg_sys/run_tests.sh

cd /opt/mgg_sys

# Activate virtual environment
source venv/bin/activate

# Run tests
pytest tests/ \
    --cov=app \
    --cov-report=html \
    --cov-report=term \
    --verbose

# Check coverage threshold
coverage report --fail-under=70

echo "Tests completed. HTML report: htmlcov/index.html"
```

**Time:** 5 days  
**Cost:** 5 days labor  
**Impact:** Catch 80% of bugs before production

---

## **Phase 2 Summary:**

**Total Time:** 10 days (2 weeks)  
**Total Cost:** 10 days labor  

**Deliverables:**
- ✅ NGINX reverse proxy (10x faster static files)
- ✅ HTTPS encryption
- ✅ Application caching (5-10x faster queries)
- ✅ Rate limiting (prevent overload)
- ✅ Automated test suite (70%+ coverage)

**Performance Improvements:**
- Static files: 10ms → **1ms** (10x faster)
- Repeated queries: 100ms → **10ms** (10x faster)
- Protection from overload: ✅

---

## 🔧 **PHASE 3: Quality & Maintenance (Weeks 5-8)**

### **3.1 Deployment Automation**

**Why:** Reduce human error during updates

#### **Implementation:**

```bash
#!/bin/bash
# /opt/mgg_sys/deploy.sh

set -e  # Exit on error

echo "=== MGG_SYS Deployment Script ==="
echo "Starting deployment at $(date)"

# 1. Backup current version
echo "Creating backup..."
tar -czf /opt/mgg_backup/pre_deploy_$(date +%Y%m%d_%H%M%S).tar.gz /opt/mgg_sys

# 2. Pull latest code (if using Git)
echo "Pulling latest code..."
cd /opt/mgg_sys
git pull origin master

# 3. Install dependencies
echo "Installing dependencies..."
source venv/bin/activate
pip install -r requirements.txt

# 4. Run database migrations (if any)
echo "Running database migrations..."
# Add migration script here if using Alembic/Flask-Migrate

# 5. Run tests
echo "Running tests..."
pytest tests/ --quiet || {
    echo "Tests failed! Aborting deployment."
    exit 1
}

# 6. Graceful reload Gunicorn (zero downtime)
echo "Reloading application..."
sudo systemctl reload mgg_sys

# 7. Verify health
echo "Checking application health..."
sleep 5
curl -f http://localhost:5001/health || {
    echo "Health check failed! Rolling back..."
    # Restore backup
    tar -xzf /opt/mgg_backup/pre_deploy_*.tar.gz -C /
    sudo systemctl restart mgg_sys
    exit 1
}

echo "Deployment successful at $(date)"
```

**Time:** 2 days  
**Cost:** 2 days labor

---

### **3.2 Database Maintenance Scripts**

**Why:** Keep database performant

#### **Implementation:**

```bash
#!/bin/bash
# /opt/mgg_sys/maintenance/db_maintenance.sh

# 1. Vacuum database (reclaim space)
psql -U mgg_user -d mgg_simulation -c "VACUUM ANALYZE;"

# 2. Reindex tables
psql -U mgg_user -d mgg_simulation -c "REINDEX DATABASE mgg_simulation;"

# 3. Archive old data to Parquet (> 90 days)
python3 /opt/mgg_sys/database/archive_manager.py --archive --days 90

# 4. Clean up old logs
find /opt/mgg_sys/app/log -name "*.csv" -mtime +365 -delete

echo "Database maintenance completed"
```

**Cron Schedule:**
```bash
# Run monthly on 1st at 3 AM
0 3 1 * * /opt/mgg_sys/maintenance/db_maintenance.sh
```

**Time:** 3 days  
**Cost:** 3 days labor

---

### **3.3 Documentation**

**Why:** Ensure knowledge transfer

#### **Deliverables:**

1. **Deployment Runbook** (`DEPLOYMENT.md`)
   - Step-by-step deployment process
   - Rollback procedures
   - Common issues & solutions

2. **Operations Manual** (`OPERATIONS.md`)
   - Daily checks
   - Weekly maintenance tasks
   - Monthly reviews

3. **Disaster Recovery Plan** (`DISASTER_RECOVERY.md`)
   - Backup restoration steps
   - System rebuild procedures
   - Contact information

4. **Troubleshooting Guide** (`TROUBLESHOOTING.md`)
   - Common errors
   - Log locations
   - Debugging steps

**Time:** 5 days  
**Cost:** 5 days labor

---

## **Phase 3 Summary:**

**Total Time:** 10 days (2 weeks)  
**Total Cost:** 10 days labor  

**Deliverables:**
- ✅ Automated deployment script
- ✅ Database maintenance automation
- ✅ Comprehensive documentation
- ✅ Knowledge transfer materials

---

## 📊 **Total Project Summary**

### **Timeline:**

| Phase | Duration | Tasks |
|-------|----------|-------|
| **Phase 1** | Weeks 1-2 | Backups, monitoring, production config |
| **Phase 2** | Weeks 3-4 | NGINX, caching, testing |
| **Phase 3** | Weeks 5-8 | Automation, maintenance, documentation |
| **TOTAL** | **6-8 weeks** | 27 days of work |

### **Budget:**

| Category | Cost |
|----------|------|
| **Hardware** | $1,000 (NAS for backups) |
| **Labor (27 days)** | ~$14,000 (@$500/day internal rate) |
| **TOTAL** | **~$15,000** |

### **Deliverables:**

**Infrastructure:**
- ✅ Automated daily backups (PostgreSQL + app data)
- ✅ Point-in-time recovery (WAL archiving)
- ✅ NGINX reverse proxy with HTTPS
- ✅ Production Gunicorn configuration
- ✅ Systemd service management

**Monitoring & Reliability:**
- ✅ Health monitoring (5-minute checks)
- ✅ Email alerts for failures
- ✅ Database connection pooling (100 users)
- ✅ Application-level caching

**Quality Assurance:**
- ✅ Automated test suite (70%+ coverage)
- ✅ Rate limiting
- ✅ Deployment automation
- ✅ Database maintenance scripts

**Documentation:**
- ✅ Deployment runbook
- ✅ Operations manual
- ✅ Disaster recovery plan
- ✅ Troubleshooting guide

---

## 🎯 **Success Metrics**

### **Before Hardening:**

| Metric | Current |
|--------|---------|
| Uptime | ~95% |
| Data loss risk | High (no backups) |
| Recovery time | Hours (manual) |
| Max concurrent users | 20-30 |
| Failure detection | Manual (hours) |
| Deployment downtime | 15-30 minutes |
| Test coverage | 0% (manual only) |

### **After Hardening:**

| Metric | Target | Improvement |
|--------|--------|-------------|
| Uptime | **99.5%** | 10x less downtime |
| Data loss risk | **Zero** (daily backups) | Eliminated |
| Recovery time | **< 15 minutes** | 20x faster |
| Max concurrent users | **100+** | 5x more capacity |
| Failure detection | **< 5 minutes** | Automated |
| Deployment downtime | **Zero** (graceful reload) | Eliminated |
| Test coverage | **70%+** | Automated QA |

---

## 🚨 **Risk Matrix**

### **Before vs After:**

| Risk | Current | After Hardening |
|------|---------|-----------------|
| **Data loss** | CRITICAL | ✅ MITIGATED (daily backups) |
| **System overload** | HIGH | ✅ MITIGATED (rate limiting + pooling) |
| **Extended downtime** | HIGH | ✅ MITIGATED (auto-recovery + monitoring) |
| **Silent failures** | HIGH | ✅ MITIGATED (5-minute detection) |
| **Deployment errors** | MEDIUM | ✅ MITIGATED (automated tests) |
| **Knowledge loss** | MEDIUM | ✅ MITIGATED (documentation) |

---

## 📋 **Implementation Checklist**

### **Phase 1 (Critical - Weeks 1-2):**

- [ ] Set up NAS/backup storage
- [ ] Configure automated PostgreSQL backups
- [ ] Enable WAL archiving
- [ ] Set up backup monitoring & alerts
- [ ] Test backup restoration
- [ ] Implement enhanced /health endpoint
- [ ] Configure health monitoring script (5-min checks)
- [ ] Set up log rotation
- [ ] Update Gunicorn configuration
- [ ] Create Systemd service
- [ ] Tune database connection pool
- [ ] Tune PostgreSQL server settings

### **Phase 2 (Performance - Weeks 3-4):**

- [ ] Install NGINX
- [ ] Configure reverse proxy
- [ ] Generate SSL certificates
- [ ] Implement application caching
- [ ] Add rate limiting
- [ ] Write unit tests (70% coverage)
- [ ] Write integration tests
- [ ] Set up pytest automation
- [ ] Create deployment automation script

### **Phase 3 (Maintenance - Weeks 5-8):**

- [ ] Create database maintenance scripts
- [ ] Schedule cron jobs
- [ ] Write deployment runbook
- [ ] Write operations manual
- [ ] Write disaster recovery plan
- [ ] Write troubleshooting guide
- [ ] Conduct team training
- [ ] Perform dry-run disaster recovery test

---

## 🎓 **Team Training Required**

### **DevOps/Admin Training:**

1. **Backup & Recovery** (1 day)
   - How backups work
   - Restoration procedures
   - WAL archiving concepts

2. **Monitoring & Alerts** (1 day)
   - Reading health checks
   - Responding to alerts
   - Log analysis

3. **Deployment Process** (1 day)
   - Running deployment script
   - Rollback procedures
   - Testing after deployment

### **Developer Training:**

1. **Testing Best Practices** (1 day)
   - Writing unit tests
   - Running pytest
   - Coverage requirements

2. **Caching Strategies** (0.5 day)
   - When to cache
   - Cache invalidation
   - Performance monitoring

---

## 📞 **Support & Maintenance**

### **Ongoing Responsibilities:**

**Daily:**
- ✅ Review health check logs
- ✅ Monitor disk space

**Weekly:**
- ✅ Review slow query logs
- ✅ Check backup success rate
- ✅ Review error logs

**Monthly:**
- ✅ Test backup restoration
- ✅ Run database maintenance
- ✅ Review system performance
- ✅ Update dependencies

**Quarterly:**
- ✅ Security patches
- ✅ Disaster recovery drill
- ✅ Capacity planning review

---

## ✅ **Acceptance Criteria**

**The system is considered production-ready when:**

1. ✅ Automated daily backups run successfully for 7 consecutive days
2. ✅ Backup restoration tested and documented
3. ✅ Health monitoring detects failures within 5 minutes
4. ✅ System handles 100 concurrent users without slowdown
5. ✅ All automated tests pass (70%+ coverage)
6. ✅ Deployment automation tested successfully
7. ✅ Zero-downtime deployment demonstrated
8. ✅ All documentation completed
9. ✅ Team trained on operations
10. ✅ Disaster recovery plan tested

---

## 🔄 **Maintenance Schedule**

### **Automated Tasks (Cron):**

```bash
# Daily backups
0 2 * * * /opt/mgg_backup/scripts/daily_backup.sh
0 3 * * * /opt/mgg_backup/scripts/backup_app_data.sh

# Health monitoring (every 5 minutes)
*/5 * * * * /opt/mgg_monitor/check_health.sh

# Monthly maintenance
0 3 1 * * /opt/mgg_sys/maintenance/db_maintenance.sh

# Monthly backup test
0 4 1 * * /opt/mgg_backup/scripts/test_restore.sh
```

---

## 📚 **Additional Resources**

### **Hardware Recommendations:**

**Minimum Server Specs (100 users):**
- CPU: 8 cores (Intel Xeon / AMD EPYC)
- RAM: 16GB minimum, 32GB recommended
- Storage: 500GB SSD (OS + app + database)
- Backup Storage: 2TB NAS or external drive

**Network:**
- Gigabit Ethernet (minimum)
- Dedicated VLAN for MGG traffic (recommended)

### **Software Dependencies:**

- Ubuntu Server 22.04 LTS (or RHEL 8/9)
- PostgreSQL 15
- Python 3.12
- NGINX 1.18+
- Systemd (for service management)

---

## 🎯 **Next Steps**

### **Week 1 Actions:**

1. **Review this document** with stakeholders
2. **Approve budget** (~$15K)
3. **Procure hardware** (NAS for backups)
4. **Assign team members:**
   - 1 DevOps/System Admin
   - 1 Backend Developer
   - 1 QA (part-time)
5. **Set up development/staging environment** for testing
6. **Begin Phase 1 implementation**

### **Communication Plan:**

- **Weekly standup** - Progress review
- **Bi-weekly demos** - Show completed features
- **Phase completion review** - Stakeholder signoff

---

## 📧 **Contact & Support**

**Project Owner:** [Your Name]  
**Technical Lead:** [DevOps Lead]  
**Repository:** https://github.com/Saulliu00/MGG_SYS

**Questions or Issues:**
- Create GitHub issue with label: `hardening`
- Email: [admin@company.internal]

---

## 📝 **Document Version History**

| Version | Date | Changes | Author |
|---------|------|---------|--------|
| 1.0 | 2026-02-22 | Initial roadmap | OpenClaw AI |

---

**This roadmap provides a practical, achievable path to production-grade enterprise deployment for MGG_SYS on a single server with 100 daily users.**

**Key Takeaway:** Focus on Phase 1 first (backups, monitoring, production config) - that gives you 80% of the value for 25% of the effort. Phases 2 and 3 can follow as resources allow.

**Ready to start? Begin with backups (Section 1.1) - that's your highest-risk item.** 🚀
