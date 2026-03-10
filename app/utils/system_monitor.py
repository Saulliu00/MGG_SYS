"""System monitoring utilities — CPU, memory, disk, DB stats, log analysis.

No direct Flask imports at module level. Uses SQLAlchemy ORM for DB queries
(requires an active app context — always called from within a request handler).
Works with both SQLite (dev) and PostgreSQL (production).
"""
import os
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path

import psutil

from app.config.network_config import NETWORK_LOGGING

# Slow-request threshold in milliseconds (config stores it in seconds)
_SLOW_MS = NETWORK_LOGGING['slow_request_threshold'] * 1000

# Current 3-table schema
_DB_TABLES = ['user', 'simulation', 'test_result']

# Brute-force detection threshold: flag IPs with more than this many failures today
_BRUTE_FORCE_THRESHOLD = 5

# Active-user window: users seen within this many minutes are shown as online
_ACTIVE_MINUTES = 30


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _is_postgres() -> bool:
    return os.environ.get('DATABASE_URL', '').startswith('postgresql')


def _resolve_db_path() -> str:
    """Return absolute path to the SQLite DB file, or '' for PostgreSQL."""
    db_url = os.environ.get('DATABASE_URL', '')
    if db_url.startswith('sqlite:///'):
        return db_url[len('sqlite:///'):]
    if db_url.startswith('postgresql'):
        return ''
    # Default SQLite fallback
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
    uploads_bytes, uploads_count = _dir_size_and_count(uploads_path)
    backups_bytes, backups_count = _dir_size_and_count(backups_path)

    # SQLite: file size on disk. PostgreSQL: query pg_database_size().
    if db_path and os.path.isfile(db_path):
        db_bytes = os.path.getsize(db_path)
    elif _is_postgres():
        try:
            from sqlalchemy import text
            from app import db
            db_bytes = int(db.session.execute(
                text('SELECT pg_database_size(current_database())')
            ).scalar() or 0)
        except Exception:
            db_bytes = 0
    else:
        db_bytes = 0

    return {
        'db_size_mb':         _mb(db_bytes),
        'uploads_size_mb':    _mb(uploads_bytes),
        'uploads_file_count': uploads_count,
        'backups_size_mb':    _mb(backups_bytes),
        'backups_file_count': backups_count,
    }


def get_db_stats(db_path: str) -> dict:
    """Row counts per table and backup inventory. Uses SQLAlchemy ORM — works for
    both SQLite and PostgreSQL without raw SQL or file-path assumptions."""
    from sqlalchemy import inspect as sa_inspect, text
    from app import db

    # Discover all tables dynamically so the UI always reflects the real schema
    table_counts = {}
    try:
        table_names = sorted(sa_inspect(db.engine).get_table_names())
        for t in table_names:
            try:
                table_counts[t] = db.session.execute(
                    text(f'SELECT COUNT(*) FROM "{t}"')
                ).scalar() or 0
            except Exception:
                table_counts[t] = '?'
    except Exception:
        # Fallback to the 3 known ORM models
        from app.models import User, Simulation, TestResult
        table_counts = {'user': 0, 'simulation': 0, 'test_result': 0}
        try:
            table_counts['user']        = User.query.count()
            table_counts['simulation']  = Simulation.query.count()
            table_counts['test_result'] = TestResult.query.count()
        except Exception:
            pass

    # File size: meaningful for SQLite only; PostgreSQL size is in get_disk_usage
    file_size_mb = _mb(os.path.getsize(db_path)) if db_path and os.path.isfile(db_path) else 0

    # Backup inventory: .db = SQLite backups, .dump = pg_dump backups
    backups_dir = (
        os.path.join(os.path.dirname(db_path), 'backups')
        if db_path
        else str(Path(__file__).parent.parent.parent / 'instance' / 'backups')
    )
    backup_files = []
    if os.path.isdir(backups_dir):
        backup_files = sorted([
            f for f in os.listdir(backups_dir)
            if f.startswith('mgg_backup_') and (f.endswith('.db') or f.endswith('.dump'))
        ])
    latest_backup = (
        backup_files[-1].replace('mgg_backup_', '').rsplit('.', 1)[0]
        if backup_files else None
    )

    return {
        'file_size_mb':       file_size_mb,
        'table_counts':       table_counts,
        'backup_count':       len(backup_files),
        'latest_backup_date': latest_backup,
    }


def get_request_stats() -> dict:
    """Analyse today's CSV log for request-level statistics."""
    from app.utils.log_manager import log_manager
    entries = log_manager.read_log_file(filename=None, max_rows=50000)

    total = errors = slow = 0
    error_entries = []
    for row in entries:
        sc = row.get('status_code', '')
        dm = row.get('duration_ms', '')
        if not sc:
            continue
        total += 1
        try:
            if int(sc) >= 400:
                errors += 1
                error_entries.append({
                    'time':        row.get('time', ''),
                    'method':      row.get('method', ''),
                    'path':        row.get('path', ''),
                    'status_code': sc,
                    'username':    row.get('username', ''),
                    'message':     row.get('message', ''),
                })
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
        'recent_errors':      error_entries[-20:][::-1],  # newest first, up to 20
    }


def get_crash_events() -> list:
    """Return up to 50 ERROR/CRITICAL log entries since the last app startup."""
    from app.utils.log_manager import log_manager
    entries = log_manager.read_log_file(filename=None, max_rows=50000)

    last_startup_ts = None
    for row in entries:
        if row.get('action') == 'system_startup':
            ts = row.get('timestamp', '')
            if ts and (last_startup_ts is None or ts > last_startup_ts):
                last_startup_ts = ts

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
        and (last_startup_ts is None or row.get('timestamp', '') >= last_startup_ts)
    ]
    return crashes[:50]


def get_access_failures() -> dict:
    """Return failed-login stats from today's log. Flag IPs with >5 failures."""
    from app.utils.log_manager import log_manager
    entries = log_manager.read_log_file(filename=None, max_rows=50000)

    failures = [row for row in entries if row.get('action') == 'user_login_failed']

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
    """Users who made a request within the last _ACTIVE_MINUTES minutes.
    Uses SQLAlchemy ORM — works for both SQLite and PostgreSQL."""
    from app.models import User

    cutoff = datetime.utcnow() - timedelta(minutes=_ACTIVE_MINUTES)
    try:
        rows = (
            User.query
            .filter(User.last_seen_at.isnot(None))
            .filter(User.last_seen_at >= cutoff)
            .order_by(User.last_seen_at.desc())
            .all()
        )
    except Exception:
        return []

    return [
        {
            'id':           u.id,
            'employee_id':  u.employee_id,
            'username':     u.username or '',
            'role':         u.role,
            'last_seen_at': u.last_seen_at.isoformat() if u.last_seen_at else None,
        }
        for u in rows
    ]


# ---------------------------------------------------------------------------
# Single public entry point
# ---------------------------------------------------------------------------

def get_system_metrics() -> dict:
    """Collect all metrics. Each section is isolated — one failure won't crash the page."""
    db_path = _resolve_db_path()
    uploads_path = str(Path(__file__).parent.parent / 'static' / 'uploads')
    backups_path = (
        os.path.join(os.path.dirname(db_path), 'backups')
        if db_path
        else str(Path(__file__).parent.parent.parent / 'instance' / 'backups')
    )

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
