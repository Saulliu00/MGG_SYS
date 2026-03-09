# Self-Hosted Application Deployment Guide

## Overview

This document describes how to deploy and maintain the production server that will be physically shipped to customers.

**System assumptions**

* CPU: x86 architecture
* OS: Linux (Ubuntu)
* Network: Local network access only
* Optional: Internet connection for remote support
* Database: PostgreSQL
* Web server: Application serves HTTP directly (no reverse proxy)

The goal is to ensure:

* Reliable local operation
* Optional remote support
* Safe database backup and recovery
* Hardware failure recovery

---

# 1. System Architecture

```
Customer Network
      │
      ▼
+-----------------------+
|   Application Server  |
|                       |
|  ┌─────────────────┐  |
|  │   Application   │  |
|  │   (Python/App)  │  |
|  └────────┬────────┘  |
|           │           |
|     PostgreSQL DB    |
|           │           |
|     Local File Data  |
+-----------------------+
```

Example user access:

```
http://SERVER-IP:PORT
```

Example:

```
http://0.0.0.0:5001
```

---

# 2. Server Directory Layout

All application files should be stored in a dedicated directory.

```
/opt/myapp/
    app/
    config/
    scripts/
    logs/
    uploads/

/data/
    postgres/
    backups/
```

Explanation:

| Directory            | Purpose                   |
| -------------------- | ------------------------- |
| `/opt/myapp/app`     | Application source code   |
| `/opt/myapp/logs`    | Application logs          |
| `/opt/myapp/uploads` | Uploaded user files       |
| `/data/postgres`     | PostgreSQL data directory |
| `/data/backups`      | Automated backups         |

---

# 3. Application User

Create a dedicated system user for the application.

```
sudo adduser appuser
```

Assign ownership:

```
sudo chown -R appuser:appuser /opt/myapp
sudo chown -R postgres:postgres /data/postgres
```

Never run the application as root.

---

# 4. PostgreSQL Setup

Install PostgreSQL:

```
sudo apt update
sudo apt install postgresql
```

Create database and user:

```
sudo -u postgres psql
```

Inside PostgreSQL:

```
CREATE DATABASE myapp;
CREATE USER myappuser WITH PASSWORD 'secure_password';
ALTER ROLE myappuser SET client_encoding TO 'utf8';
ALTER ROLE myappuser SET default_transaction_isolation TO 'read committed';
ALTER ROLE myappuser SET timezone TO 'UTC';
GRANT ALL PRIVILEGES ON DATABASE myapp TO myappuser;
```

Database connection example:

```
postgresql://myappuser:password@localhost/myapp
```

---

# 5. Application Service (Auto Start)

Create a system service so the application starts automatically.

File:

```
/etc/systemd/system/myapp.service
```

Content:

```
[Unit]
Description=MyApp Service
After=network.target postgresql.service

[Service]
User=appuser
WorkingDirectory=/opt/myapp/app
ExecStart=/usr/bin/python3 main.py
Restart=always

[Install]
WantedBy=multi-user.target
```

Enable the service:

```
sudo systemctl daemon-reload
sudo systemctl enable myapp
sudo systemctl start myapp
```

Verify:

```
systemctl status myapp
```

---

# 6. Firewall Configuration

Allow only required ports.

Example:

```
sudo ufw allow 22
sudo ufw allow 8000
sudo ufw enable
```

| Port | Purpose              |
| ---- | -------------------- |
| 22   | Remote support (SSH) |
| 8000 | Application access   |

---

# 7. Local Backup Strategy

Daily database backups must be automated.

Create backup script:

```
/opt/myapp/scripts/backup.sh
```

Script example:

```
#!/bin/bash

DATE=$(date +%Y%m%d_%H%M)

pg_dump myapp > /data/backups/myapp_$DATE.sql

find /data/backups -type f -mtime +14 -delete
```

Make executable:

```
chmod +x backup.sh
```

Add scheduled backup:

```
crontab -e
```

Add:

```
0 2 * * * /opt/myapp/scripts/backup.sh
```

Backup runs every day at 2 AM.

---

# 8. Remote Support Capability

If the customer connects the server to the internet, remote support can be enabled.

Requirements:

* SSH access enabled
* Secure authentication

Enable SSH:

```
sudo systemctl enable ssh
```

Recommended security:

```
Disable password login
Use SSH keys only
```

Example support workflow:

1. Customer provides server IP
2. Engineer connects via SSH
3. Diagnose system
4. Download database backup if necessary

Example database download:

```
scp user@server:/data/backups/latest.sql .
```

---

# 9. Database Export for Support

Manual database export command:

```
pg_dump myapp > myapp_export.sql
```

Restore command:

```
psql myapp < myapp_export.sql
```

---

# 10. Hardware Failure Recovery Plan

Hardware failures can occur. A recovery plan must exist.

## Scenario: Disk Failure

Steps:

1. Replace failed hardware
2. Reinstall operating system
3. Reinstall application
4. Restore database from backup

Recovery steps:

```
install OS
install PostgreSQL
create database
restore backup
start application
```

Restore example:

```
psql myapp < backup.sql
```

---

## Scenario: Complete Server Replacement

Procedure:

1. Prepare new server hardware
2. Install OS
3. Copy application files
4. Restore database backup
5. Restart services

---

# 11. Customer Backup Recommendation

Customers should copy backups regularly to external storage.

Example:

```
/data/backups/
```

Recommended methods:

* external USB drive
* network storage
* company backup server

---

# 12. System Health Checks

Verify system health periodically.

Check application:

```
systemctl status myapp
```

Check PostgreSQL:

```
systemctl status postgresql
```

Check disk usage:

```
df -h
```

Check logs:

```
/opt/myapp/logs
```

---

# 13. Pre-Shipment Checklist

Before shipping the server:

| Task                             | Status |
| -------------------------------- | ------ |
| Application starts automatically | ✓      |
| Database initialized             | ✓      |
| Backup system working            | ✓      |
| Firewall configured              | ✓      |
| SSH enabled                      | ✓      |
| Default login documented         | ✓      |
| System reboot tested             | ✓      |

Test procedure:

1. Reboot server
2. Confirm application loads
3. Confirm database works
4. Confirm backup job runs

---

# 14. Customer Quick Start

Customer setup steps:

1. Connect server to network
2. Power on server
3. Find server IP address
4. Open browser
5. Visit:

```
http://SERVER-IP:5001
```

Example:

```
http://0.0.0.0:5001
```

---

# 15. Important Notes

* Keep regular backups
* Do not modify system configuration without documentation
* Contact support if database corruption or hardware failure occurs

---

# End of Document
