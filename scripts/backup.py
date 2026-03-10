#!/usr/bin/env python3
"""
MGG_SYS daily backup script.

Backs up (in order):
  1. Database  — SQLite file copy, or pg_dump for PostgreSQL
  2. Uploads   — instance/uploads/ → tar.gz archive
  3. Logs      — app/log/         → tar.gz archive

Does NOT back up:
  - ML models  (tracked in git)
  - Source code (tracked in git)

Usage:
    python scripts/backup.py [--retention-days N] [--date YYYYMMDD]

    --retention-days N   Keep backups for N days (default: 30)
    --date YYYYMMDD      Label the backup with a specific date instead of today
                         (e.g. --date 20260301 creates mgg_backup_20260301_000000.db)

Recommended cron (daily at 02:00):
    0 2 * * * cd /opt/mgg/MGG_SYS && \
              /opt/mgg/MGG_SYS/venv/bin/python scripts/backup.py \
              >> /var/log/mgg_backup.log 2>&1

Environment variables read:
    DATABASE_URL   — if set and starts with postgresql://, uses pg_dump
                     otherwise defaults to SQLite at instance/simulation_system.db
"""

import argparse
import os
import shutil
import subprocess
import sys
import tarfile
from datetime import datetime, timedelta
from pathlib import Path

# ── Paths ──────────────────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).parent.parent.resolve()
BACKUP_DIR   = PROJECT_ROOT / 'instance' / 'backups'
UPLOADS_DIR  = PROJECT_ROOT / 'instance' / 'uploads'
LOGS_DIR     = PROJECT_ROOT / 'app' / 'log'

# Set at startup; overridden by --date flag in main()
TIMESTAMP = datetime.now().strftime('%Y%m%d_%H%M%S')


# ── Helpers ────────────────────────────────────────────────────────────────────

def _fmt_size(path: Path) -> str:
    """Return human-readable file size string."""
    size = path.stat().st_size
    if size < 1024:
        return f'{size} B'
    elif size < 1024 ** 2:
        return f'{size / 1024:.1f} KB'
    else:
        return f'{size / 1024 ** 2:.1f} MB'


def ensure_backup_dir():
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)


# ── Backup functions ───────────────────────────────────────────────────────────

def backup_database() -> Path:
    """Back up the database. SQLite → file copy; PostgreSQL → pg_dump."""
    db_url = os.environ.get('DATABASE_URL', '')

    if db_url.startswith('postgresql'):
        return _pg_dump(db_url)
    else:
        return _sqlite_copy(db_url)


def _sqlite_copy(db_url: str) -> Path:
    if db_url.startswith('sqlite:///'):
        db_path = Path(db_url[len('sqlite:///'):])
    else:
        db_path = PROJECT_ROOT / 'instance' / 'simulation_system.db'

    if not db_path.is_file():
        raise FileNotFoundError(f'SQLite database not found: {db_path}')

    dest = BACKUP_DIR / f'mgg_backup_{TIMESTAMP}.db'
    shutil.copy2(db_path, dest)
    print(f'  [DB]      {dest.name}  ({_fmt_size(dest)})')
    return dest


def _pg_dump(db_url: str) -> Path:
    dest = BACKUP_DIR / f'mgg_backup_{TIMESTAMP}.dump'
    result = subprocess.run(
        ['pg_dump', '--format=custom', '--file', str(dest), db_url],
        capture_output=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f'pg_dump failed:\n{result.stderr.decode().strip()}')
    print(f'  [DB]      {dest.name}  ({_fmt_size(dest)})')
    return dest


def backup_uploads() -> Path:
    """Archive instance/uploads/ → uploads_<timestamp>.tar.gz"""
    dest = BACKUP_DIR / f'uploads_{TIMESTAMP}.tar.gz'
    with tarfile.open(dest, 'w:gz') as tar:
        if UPLOADS_DIR.is_dir():
            tar.add(UPLOADS_DIR, arcname='uploads')
    print(f'  [UPLOADS] {dest.name}  ({_fmt_size(dest)})')
    return dest


def backup_logs() -> Path:
    """Archive app/log/ → logs_<timestamp>.tar.gz"""
    dest = BACKUP_DIR / f'logs_{TIMESTAMP}.tar.gz'
    with tarfile.open(dest, 'w:gz') as tar:
        if LOGS_DIR.is_dir():
            tar.add(LOGS_DIR, arcname='log')
    print(f'  [LOGS]    {dest.name}  ({_fmt_size(dest)})')
    return dest


def prune_old_backups(retention_days: int):
    """Delete backup files older than retention_days."""
    cutoff = datetime.now() - timedelta(days=retention_days)
    pruned = 0
    for f in BACKUP_DIR.iterdir():
        if not f.is_file():
            continue
        if f.suffix not in ('.db', '.dump', '.gz'):
            continue
        if datetime.fromtimestamp(f.stat().st_mtime) < cutoff:
            f.unlink()
            pruned += 1
    if pruned:
        print(f'  [PRUNE]   Removed {pruned} file(s) older than {retention_days} days')


# ── Entry point ────────────────────────────────────────────────────────────────

def main():
    global TIMESTAMP

    parser = argparse.ArgumentParser(description='MGG_SYS daily backup')
    parser.add_argument(
        '--retention-days', type=int, default=30,
        help='Delete backups older than N days (default: 30)',
    )
    parser.add_argument(
        '--date', type=str, default=None,
        metavar='YYYYMMDD',
        help='Label the backup with this date instead of today '
             '(e.g. --date 20260301 → mgg_backup_20260301_000000)',
    )
    args = parser.parse_args()

    if args.date:
        try:
            datetime.strptime(args.date, '%Y%m%d')
        except ValueError:
            print(f'ERROR: --date must be in YYYYMMDD format, got: {args.date}')
            sys.exit(1)
        TIMESTAMP = f'{args.date}_000000'

    print(f'\nMGG_SYS Backup  {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
    if args.date:
        print(f'Label:       {TIMESTAMP}  (custom --date)')
    print(f'Destination: {BACKUP_DIR}')
    print()

    ensure_backup_dir()

    jobs = [
        ('Database', backup_database),
        ('Uploads',  backup_uploads),
        ('Logs',     backup_logs),
    ]

    errors = []
    for label, fn in jobs:
        try:
            fn()
        except Exception as exc:
            print(f'  [ERROR]   {label}: {exc}')
            errors.append(f'{label}: {exc}')

    prune_old_backups(args.retention_days)
    print()

    if errors:
        print(f'Backup completed with {len(errors)} error(s):')
        for err in errors:
            print(f'  - {err}')
        sys.exit(1)
    else:
        print('Backup completed successfully.')
        sys.exit(0)


if __name__ == '__main__':
    main()
