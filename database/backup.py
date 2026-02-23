"""Daily SQLite database backup.

Backs up instance/simulation_system.db to instance/backups/
once per day, keyed by date.  Old backups beyond BACKUP_KEEP_DAYS
are automatically deleted.

Intended to be called from check_daily_login() in app/routes/auth.py
so the backup runs at the start of each new calendar day, before
any user session is invalidated.
"""
import os
import sqlite3
from datetime import date, timedelta

BACKUP_KEEP_DAYS = 30  # how many daily backups to retain


def daily_backup(app):
    """Create a dated backup of the SQLite database if one doesn't exist for today.

    Backup location: instance/backups/simulation_system_YYYY-MM-DD.db
    Skips silently if today's backup already exists (safe for concurrent requests).
    Cleans up backups older than BACKUP_KEEP_DAYS days after a successful backup.
    """
    db_uri = app.config.get('SQLALCHEMY_DATABASE_URI', '')
    if not db_uri.startswith('sqlite:///'):
        return  # Only supports SQLite

    source_path = db_uri.replace('sqlite:///', '')
    if not os.path.exists(source_path):
        return

    backup_dir = os.path.join(os.path.dirname(source_path), 'backups')
    os.makedirs(backup_dir, exist_ok=True)

    today = date.today().isoformat()
    backup_path = os.path.join(backup_dir, f'simulation_system_{today}.db')

    # Skip if today's backup already exists (another request may have triggered it first)
    if os.path.exists(backup_path):
        return

    try:
        # SQLite's online backup API — safe to use while the DB is live
        src = sqlite3.connect(source_path)
        dst = sqlite3.connect(backup_path)
        src.backup(dst)
        dst.close()
        src.close()
        app.logger.info(f'Daily database backup created: {backup_path}')
    except Exception as e:
        app.logger.error(f'Daily database backup failed: {str(e)}')
        return

    _cleanup_old_backups(backup_dir, app)


def _cleanup_old_backups(backup_dir, app):
    """Delete backup files older than BACKUP_KEEP_DAYS days."""
    cutoff = date.today() - timedelta(days=BACKUP_KEEP_DAYS)
    try:
        for filename in os.listdir(backup_dir):
            if not (filename.startswith('simulation_system_') and filename.endswith('.db')):
                continue
            date_str = filename[len('simulation_system_'):-len('.db')]
            try:
                backup_date = date.fromisoformat(date_str)
                if backup_date < cutoff:
                    os.remove(os.path.join(backup_dir, filename))
                    app.logger.info(f'Deleted old backup: {filename}')
            except ValueError:
                pass  # Skip files with unexpected names
    except Exception as e:
        app.logger.warning(f'Backup cleanup failed: {str(e)}')
