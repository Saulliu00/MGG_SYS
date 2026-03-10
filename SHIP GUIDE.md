# Server Shipment Checklist — MGG Simulation System

Complete every item below before shipping the server to the customer. Sign off each section when done.

---

## Server Specifications

| Item | Spec |
|------|------|
| CPU | 16-core (Intel Xeon / AMD EPYC) |
| RAM | 64 GB |
| Disk | 500 GB SSD |
| Network Card | 10 GbE |
| OS | Ubuntu Server 22.04 LTS |
| Database | PostgreSQL 15 |
| Application Port | 5001 |

---

## Section 1 — Hardware

- [ ] Server powers on without errors
- [ ] All 64 GB RAM detected (`free -h`)
- [ ] All 500 GB disk capacity detected (`lsblk`)
- [ ] 10 GbE network card detected and linked (`ip link show`)
- [ ] Server boots from SSD (not USB/installer media)
- [ ] System clock is set to correct timezone (`timedatectl`)

---

## Section 2 — Operating System

- [ ] Ubuntu Server 22.04 LTS installed (no desktop environment)
- [ ] All OS updates applied (`sudo apt-get update && sudo apt-get upgrade`)
- [ ] Dedicated `mgg` system user created (non-root, no login shell)
- [ ] SSH server enabled and running (`systemctl status ssh`)
- [ ] SSH key-based login configured (password login disabled)

---

## Section 3 — Application Installation

- [ ] MGG_SYS cloned from GitHub to `/opt/mgg/MGG_SYS`
- [ ] Python virtual environment created at `/opt/mgg/MGG_SYS/venv`
- [ ] All dependencies installed (`pip install -r requirements.txt`) with no errors
- [ ] Dependency smoke test passes:
  ```
  python -c "import flask, gunicorn, psycopg2, numpy, pandas, plotly; print('OK')"
  ```
- [ ] Application directory owned by `mgg` user (`ls -la /opt/mgg/`)

---

## Section 4 — Database

- [ ] PostgreSQL 15 installed and running (`systemctl status postgresql`)
- [ ] Database `mgg_simulation` created
- [ ] User `mgg_user` created with a strong password
- [ ] `mgg_user` granted all privileges on `mgg_simulation`
- [ ] Schema-level grant applied (`GRANT ALL ON SCHEMA public TO mgg_user`)
- [ ] Public access revoked (`REVOKE ALL ON DATABASE mgg_simulation FROM PUBLIC`)
- [ ] PostgreSQL tuned for 64 GB RAM (`/etc/postgresql/15/main/postgresql.conf`):
  - [ ] `shared_buffers = 16GB`
  - [ ] `work_mem = 256MB`
  - [ ] `effective_cache_size = 48GB`
  - [ ] `max_connections = 100`
- [ ] PostgreSQL set to auto-start on boot (`systemctl enable postgresql`)
- [ ] All three application tables created: `user`, `simulation`, `test_result`
  ```
  psql postgresql://mgg_user:<password>@localhost:5432/mgg_simulation -c "\dt"
  ```

---

## Section 5 — Configuration

- [ ] `.env` file created at `/opt/mgg/MGG_SYS/.env`
- [ ] `SECRET_KEY` is a random 64-character hex string (not the auto-generated dev key)
- [ ] `ADMIN_PASSWORD` is set to a strong password (not the default `admin123`)
- [ ] `DATABASE_URL` points to `postgresql://mgg_user:<password>@localhost:5432/mgg_simulation`
- [ ] `.env` file permissions are `600` (`ls -la .env`)
- [ ] `.env` is excluded from git (`git status` shows no `.env` tracked)

---

## Section 6 — System Service

- [ ] systemd service file created at `/etc/systemd/system/mgg-system.service`
- [ ] Service `After=postgresql.service` and `Requires=postgresql.service` set
- [ ] Service runs as `mgg` user (not root)
- [ ] Service enabled for auto-start (`systemctl enable mgg-system`)
- [ ] Service starts successfully (`systemctl status mgg-system` → `active (running)`)

---

## Section 7 — Firewall

- [ ] UFW enabled (`sudo ufw enable`)
- [ ] Port 22 (SSH) allowed
- [ ] Port 5001 (application) allowed
- [ ] All other ports blocked
- [ ] Firewall rules verified (`sudo ufw status`)

---

## Section 8 — Automated Backup

- [ ] Backup script verified manually:
  ```
  python scripts/backup.py
  ```
  Output files appear in `instance/backups/`
- [ ] Backup cron job scheduled (daily at 02:00):
  ```
  crontab -l | grep backup
  ```
- [ ] Backup log path configured (`/var/log/mgg_backup.log`)
- [ ] 30-day retention confirmed (old backups auto-pruned)

---

## Section 9 — Pre-Shipment Verification

Perform these tests after a **full reboot** of the server.

- [ ] Server reboots cleanly with no manual intervention
- [ ] PostgreSQL starts automatically after reboot (`systemctl status postgresql`)
- [ ] `mgg-system` service starts automatically after reboot (`systemctl status mgg-system`)
- [ ] Health endpoint returns healthy:
  ```
  curl http://localhost:5001/health
  ```
  Expected: `{"status": "healthy", "checks": {"database": "ok", "file_system": "ok"}}`
- [ ] Login works with admin credentials at `http://localhost:5001`
- [ ] Forward simulation (正向) page loads and runs a test simulation
- [ ] Work order query (工单查询) page loads and displays data
- [ ] Admin panel loads and shows user list
- [ ] Backup job runs and produces files in `instance/backups/`
- [ ] Application log files are being written to `app/log/`

---

## Section 10 — Customer Handoff

- [ ] Customer network IP confirmed and accessible from server
- [ ] Application URL confirmed: `http://<server-ip>:5001`
- [ ] Customer admin credentials documented and handed over securely
- [ ] Customer instructed to change admin password on first login
- [ ] Customer informed of backup location: `instance/backups/`
- [ ] `NETWORK_DEPLOYMENT.md` printed or provided as PDF for customer reference

---

## Sign-Off

| Role | Name | Date | Signature |
|------|------|------|-----------|
| Prepared by | | | |
| Verified by | | | |

---

## Quick Reference — Customer First Login

```
URL:         http://<server-ip>:5001
Employee ID: admin
Password:    (as set in .env ADMIN_PASSWORD)
```

**First action after handover:** log in as admin → Admin Panel → reset admin password.
