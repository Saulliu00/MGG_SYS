"""System monitoring utilities — CPU, memory, disk, DB stats, log analysis.

No Flask imports. Pure Python. Call get_system_metrics() from a route handler
and pass the result dict directly to the template.
"""
import os
import sqlite3
from collections import defaultdict
from datetime import datetime
from pathlib import Path

import psutil

from app.config.network_config import NETWORK_LOGGING

# Slow-request threshold in milliseconds (config stores it in seconds)
_SLOW_MS = NETWORK_LOGGING['slow_request_threshold'] * 1000

# Tables expected in the database (for row-count display)
_DB_TABLES = ['user', 'simulation', 'test_result', 'recipe', 'work_order', 'experiment_file']

# Brute-force detection threshold: flag IPs with more than this many failures today
_BRUTE_FORCE_THRESHOLD = 5

# Active-user window: users seen within this many minutes are shown as online
_ACTIVE_MINUTES = 30


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _resolve_db_path() -> str:
    """Return absolute path to the SQLite database file."""
    db_url = os.environ.get('DATABASE_URL', '')
    if db_url.startswith('sqlite:///'):
        return db_url[len('sqlite:///'):]
    # Walk up: app/utils/ → app/ → project_root → instance/
    project_root = Path(__file__).parent.parent.parent
    return str(project_root / 'instance' / 'simulation_system.db')


def _dir_size_and_count(path: str):
    """Return (total_bytes, file_count) for a directory, or (0, 0) if missing."""
    total, count = 0, 0
    if not os.path.isdir(path):
        return 0, 0
    for entry in os.scandir(path):
        if entry.is_file(follow_symlinks=False):
            try:
                total += entry.stat().st_size
                count += 1
            except OSError:
                pass
    return total, count


def _mb(byte_count: int) -> float:
    return round(byte_count / (1024 ** 2), 2)


# ---------------------------------------------------------------------------
# Public metric functions
# ---------------------------------------------------------------------------

def get_system_resources() -> dict:
    """CPU and RAM snapshot using psutil."""
    cpu = psutil.cpu_percent(interval=0.5)
    mem = psutil.virtual_memory()
    return {
        'cpu_percent':         round(cpu, 1),
        'memory_percent':      round(mem.percent, 1),
        'memory_used_mb':      _mb(mem.used),
        'memory_total_mb':     _mb(mem.total),
        'memory_available_mb': _mb(mem.available),
    }


def get_disk_usage(db_path: str, uploads_path: str, backups_path: str) -> dict:
    """File-system sizes for the three key locations."""
    db_bytes = os.path.getsize(db_path) if os.path.isfile(db_path) else 0
    uploads_bytes, uploads_count = _dir_size_and_count(uploads_path)
    backups_bytes, backups_count = _dir_size_and_count(backups_path)
    return {
        'db_size_mb':        _mb(db_bytes),
        'uploads_size_mb':   _mb(uploads_bytes),
        'uploads_file_count': uploads_count,
        'backups_size_mb':   _mb(backups_bytes),
        'backups_file_count': backups_count,
    }


def get_db_stats(db_path: str) -> dict:
    """Row counts per table, file size, and backup info."""
    file_size_mb = _mb(os.path.getsize(db_path)) if os.path.isfile(db_path) else 0

    table_counts = {t: 0 for t in _DB_TABLES}
    if os.path.isfile(db_path):
        conn = sqlite3.connect(f'file:{db_path}?mode=ro', uri=True)
        try:
            for table in _DB_TABLES:
                try:
                    row = conn.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()
                    table_counts[table] = row[0] if row else 0
                except sqlite3.OperationalError:
                    pass  # Table may not exist yet on a fresh DB
        finally:
            conn.close()

    # Backup inventory
    backups_dir = os.path.join(os.path.dirname(db_path), 'backups')
    backup_files = sorted([
        f for f in os.listdir(backups_dir)
        if f.startswith('simulation_system_') and f.endswith('.db')
    ]) if os.path.isdir(backups_dir) else []
    latest_backup = backup_files[-1].replace('simulation_system_', '').replace('.db', '') \
        if backup_files else None

    return {
        'file_size_mb':      file_size_mb,
        'table_counts':      table_counts,
        'backup_count':      len(backup_files),
        'latest_backup_date': latest_backup,
    }


def get_request_stats() -> dict:
    """Analyse today's CSV log for request-level statistics."""
    from app.utils.log_manager import log_manager  # local import — avoids circular at module level
    entries = log_manager.read_log_file(filename=None, max_rows=50000)

    total = errors = slow = 0
    for row in entries:
        sc = row.get('status_code', '')
        dm = row.get('duration_ms', '')
        if not sc:
            continue  # skip non-request log entries
        total += 1
        try:
            if int(sc) >= 400:
                errors += 1
        except ValueError:
            pass
        try:
            if float(dm) >= _SLOW_MS:
                slow += 1
        except (ValueError, TypeError):
            pass

    error_rate = round(errors / total * 100, 1) if total else 0.0
    return {
        'total_requests':     total,
        'error_count':        errors,
        'slow_request_count': slow,
        'error_rate_percent': error_rate,
    }


def get_crash_events() -> list:
    """Return up to 50 ERROR/CRITICAL log entries from today (newest first)."""
    from app.utils.log_manager import log_manager
    entries = log_manager.read_log_file(filename=None, max_rows=50000)
    crashes = [
        {
            'time':     row.get('time', ''),
            'level':    row.get('level', ''),
            'message':  row.get('message', ''),
            'error':    row.get('error', ''),
            'path':     row.get('path', ''),
            'username': row.get('username', ''),
        }
        for row in entries
        if row.get('level') in ('ERROR', 'CRITICAL')
    ]
    return crashes[:50]


def get_access_failures() -> dict:
    """Return failed-login stats from today's log. Flag IPs with >5 failures."""
    from app.utils.log_manager import log_manager
    entries = log_manager.read_log_file(filename=None, max_rows=50000)

    failures = [
        row for row in entries
        if row.get('action') == 'user_login_failed'
    ]

    ip_counts: dict = defaultdict(int)
    for row in failures:
        ip_counts[row.get('ip_address', 'unknown')] += 1

    flagged = [
        {'ip': ip, 'count': count}
        for ip, count in sorted(ip_counts.items(), key=lambda x: -x[1])
        if count > _BRUTE_FORCE_THRESHOLD
    ]

    recent = [
        {
            'time':     row.get('time', ''),
            'ip':       row.get('ip_address', ''),
            'username': row.get('username', ''),
        }
        for row in failures[:10]
    ]

    return {
        'total_failures':  len(failures),
        'flagged_ips':     flagged,
        'recent_failures': recent,
    }


def get_active_users(db_path: str) -> list:
    """Users who made a request within the last _ACTIVE_MINUTES minutes."""
    if not os.path.isfile(db_path):
        return []
    conn = sqlite3.connect(f'file:{db_path}?mode=ro', uri=True)
    try:
        rows = conn.execute(
            '''SELECT id, employee_id, username, role, last_seen_at
               FROM "user"
               WHERE last_seen_at IS NOT NULL
                 AND last_seen_at >= datetime('now', ?)
               ORDER BY last_seen_at DESC''',
            (f'-{_ACTIVE_MINUTES} minutes',)
        ).fetchall()
    except sqlite3.OperationalError:
        return []  # columns not yet migrated on first boot
    finally:
        conn.close()
    return [
        {
            'id':           r[0],
            'employee_id':  r[1],
            'username':     r[2] or '',
            'role':         r[3],
            'last_seen_at': r[4],
        }
        for r in rows
    ]


# ---------------------------------------------------------------------------
# Single public entry point
# ---------------------------------------------------------------------------

def get_system_metrics() -> dict:
    """Collect all metrics. Each section is isolated — one failure won't crash the page."""
    db_path = _resolve_db_path()
    # Uploads folder is relative to app/static/uploads/
    uploads_path = str(Path(__file__).parent.parent / 'static' / 'uploads')
    backups_path = os.path.join(os.path.dirname(db_path), 'backups')

    metrics: dict = {}

    sections = [
        ('resources',       get_system_resources,  []),
        ('disk',            get_disk_usage,         [db_path, uploads_path, backups_path]),
        ('db',              get_db_stats,           [db_path]),
        ('requests',        get_request_stats,      []),
        ('crashes',         get_crash_events,       []),
        ('access_failures', get_access_failures,    []),
        ('active_users',    get_active_users,       [db_path]),
    ]

    for key, fn, args in sections:
        try:
            metrics[key] = fn(*args)
        except Exception as exc:
            metrics[key] = {'error': str(exc)}

    metrics['generated_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    return metrics
