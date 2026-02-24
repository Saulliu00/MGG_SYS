"""MGG System Stress Test — concurrent user capacity and crash analysis.

Escalates through user-count tiers. Each virtual user logs in and executes
a realistic mixed workload (reads + writes). Metrics are collected per-tier
and a final summary identifies the break point and primary failure cause.

SQLite failure modes this test deliberately exercises
-----------------------------------------------------
  • database is locked       — concurrent writers exceed WAL write-lock timeout
  • connection pool timeout  — SQLAlchemy pool exhausted under high load
  • HTTP 500 (middleware)    — exception re-raised by logging middleware
  • Thread join timeout      — worker threads hang (deadlock / infinite wait)

Usage
-----
    python stress_test.py                            # default tiers: 2,5,10,20,50
    python stress_test.py --tiers 5,10,25,50,100    # custom tiers
    python stress_test.py --requests 20              # more requests per user
    python stress_test.py --write-heavy              # emphasise write operations
    python stress_test.py --tiers 5,10 --requests 5 # quick smoke run
"""

import argparse
import io
import json
import os
import shutil
import statistics
import sys
import tempfile
import threading
import time
import traceback
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# ── Colour helpers (graceful fallback if terminal has no colour) ──────────────

_COLOUR = sys.stdout.isatty()

def _c(code, text):
    return f'\033[{code}m{text}\033[0m' if _COLOUR else text

RED    = lambda t: _c('91', t)
YELLOW = lambda t: _c('93', t)
GREEN  = lambda t: _c('92', t)
CYAN   = lambda t: _c('96', t)
BOLD   = lambda t: _c('1',  t)
DIM    = lambda t: _c('2',  t)


# ── App factory ───────────────────────────────────────────────────────────────

def _make_app(db_path: str, upload_dir: str):
    """Full Flask app with all blueprints, backed by a temp SQLite file."""
    os.environ['DATABASE_URL'] = f'sqlite:///{db_path}'
    from app import create_app
    app = create_app()
    app.config.update(
        TESTING=False,
        WTF_CSRF_ENABLED=False,
        SESSION_COOKIE_SECURE=False,
        UPLOAD_FOLDER=upload_dir,
        PROPAGATE_EXCEPTIONS=False,
    )
    return app


# ── Result data structures ────────────────────────────────────────────────────

@dataclass
class RequestResult:
    success: bool
    status_code: int
    duration_ms: float
    endpoint: str = ''
    error_type: Optional[str] = None    # short label, e.g. "SQLite_locked"
    error_detail: Optional[str] = None  # full message / first line of traceback


@dataclass
class TierResult:
    tier: int
    num_users: int
    requests_per_user: int
    write_heavy: bool
    results: List[RequestResult] = field(default_factory=list)
    wall_time_s: float = 0.0
    crashed_workers: int = 0   # threads that timed out
    first_crash: Optional[str] = None  # first full crash traceback

    # ── aggregates ──────────────────────────────────────────────────────────

    @property
    def total(self) -> int:
        return len(self.results)

    @property
    def successes(self) -> int:
        return sum(1 for r in self.results if r.success)

    @property
    def failures(self) -> int:
        return self.total - self.successes

    @property
    def error_rate(self) -> float:
        return (self.failures / self.total * 100) if self.total else 0.0

    @property
    def throughput(self) -> float:
        return (self.total / self.wall_time_s) if self.wall_time_s else 0.0

    # Requests slower than this are counted as degraded even if they returned 200
    SLOW_THRESHOLD_MS: float = 5_000

    def latencies(self) -> List[float]:
        return sorted(r.duration_ms for r in self.results if r.success)

    @property
    def slow_requests(self) -> int:
        """Successful responses that took longer than SLOW_THRESHOLD_MS."""
        return sum(1 for r in self.results
                   if r.success and r.duration_ms >= self.SLOW_THRESHOLD_MS)

    @property
    def hung_pct(self) -> float:
        """Percentage of worker threads that timed out."""
        return (self.crashed_workers / self.num_users * 100
                if self.num_users else 0.0)

    @property
    def effective_error_rate(self) -> float:
        """Combined signal: HTTP errors + hung workers (they never responded)."""
        http_fail_pct = self.error_rate
        hung_pct = self.hung_pct
        return min(100.0, http_fail_pct + hung_pct * 0.5)

    def error_breakdown(self) -> Dict[str, int]:
        counts: Dict[str, int] = defaultdict(int)
        for r in self.results:
            if not r.success and r.error_type:
                counts[r.error_type] += 1
        return dict(sorted(counts.items(), key=lambda x: -x[1]))

    def endpoint_stats(self) -> Dict[str, Tuple[int, int]]:
        """Returns {endpoint: (total, failures)}."""
        stats: Dict[str, List] = defaultdict(lambda: [0, 0])
        for r in self.results:
            stats[r.endpoint][0] += 1
            if not r.success:
                stats[r.endpoint][1] += 1
        return {k: tuple(v) for k, v in stats.items()}


# ── Fake xlsx helper ──────────────────────────────────────────────────────────

_XLSX_CACHE: Optional[bytes] = None

def _fake_xlsx_bytes() -> bytes:
    """Build a real xlsx once and cache it (thread-safe — GIL protects bytes)."""
    global _XLSX_CACHE
    if _XLSX_CACHE is None:
        try:
            import openpyxl
            wb = openpyxl.Workbook()
            ws = wb.active
            ws.append(['time', 'pressure'])
            for i in range(50):
                ws.append([i * 0.01, i * 0.5 + 0.1])
            buf = io.BytesIO()
            wb.save(buf)
            _XLSX_CACHE = buf.getvalue()
        except Exception:
            _XLSX_CACHE = b'PK\x03\x04\x14\x00' + b'\x00' * 100
    return _XLSX_CACHE


# ── Virtual user ─────────────────────────────────────────────────────────────

class VirtualUser:
    """Simulates one logged-in user making a realistic mix of requests."""

    WORKER_TIMEOUT = 60  # seconds before we consider a thread hung

    def __init__(self, app, user_index: int, role: str, result: TierResult):
        self.app = app
        self.employee_id = f'stress_{user_index:05d}'
        self.role = role
        self.result = result
        self.client = app.test_client()
        self._logged_in = False

    # ── Low-level request wrapper ────────────────────────────────────────────

    def _req(self, method: str, url: str, endpoint_label: str = '',
             **kwargs) -> RequestResult:
        label = endpoint_label or url
        t0 = time.perf_counter()
        try:
            resp = getattr(self.client, method)(url, **kwargs)
            dur = (time.perf_counter() - t0) * 1000
            ok = resp.status_code < 400
            err_type = err_detail = None
            if not ok:
                err_type = f'HTTP_{resp.status_code}'
                try:
                    body = json.loads(resp.data)
                    err_detail = body.get('message') or body.get('error') or str(resp.status_code)
                except Exception:
                    err_detail = f'status {resp.status_code}'
            return RequestResult(ok, resp.status_code, dur, label, err_type, err_detail)
        except Exception as exc:
            dur = (time.perf_counter() - t0) * 1000
            msg = str(exc)
            tb_lines = traceback.format_exc().splitlines()
            # Classify common SQLite / SQLAlchemy failure modes
            if 'database is locked' in msg.lower():
                et = 'SQLite_locked'
            elif 'pool' in msg.lower() and ('timeout' in msg.lower() or 'overflow' in msg.lower()):
                et = 'ConnectionPool_exhausted'
            elif 'operationalerror' in type(exc).__name__.lower():
                et = 'SQLite_OperationalError'
            elif 'timeout' in msg.lower():
                et = 'RequestTimeout'
            elif 'statementError' in type(exc).__name__:
                et = 'SQLAlchemy_StatementError'
            else:
                et = type(exc).__name__
            # Keep only first line of traceback as detail
            detail = tb_lines[-1] if tb_lines else msg[:120]
            # Record full traceback on first crash
            if self.result.first_crash is None:
                self.result.first_crash = traceback.format_exc()
            return RequestResult(False, 0, dur, label, et, detail[:200])

    # ── Individual request actions ───────────────────────────────────────────

    def login(self) -> bool:
        r = self._req('post', '/auth/login', 'POST /auth/login',
                      data={'employee_id': self.employee_id, 'password': 'pass123'})
        self.result.results.append(r)
        self._logged_in = r.success
        return r.success

    def health_check(self):
        self.result.results.append(
            self._req('get', '/health', 'GET /health'))

    def view_simulation(self):
        if self.role in ('admin', 'research_engineer'):
            self.result.results.append(
                self._req('get', '/simulation/', 'GET /simulation/'))
        else:
            self.result.results.append(
                self._req('get', '/simulation/history', 'GET /simulation/history'))

    def view_admin_monitor(self):
        if self.role == 'admin':
            self.result.results.append(
                self._req('get', '/admin/monitor/data', 'GET /admin/monitor/data'))

    def submit_experiment(self, seq: int):
        wo = f'WO_S{self.employee_id[-5:]}_{seq:04d}'
        data = {
            'ticket_number': wo,
            'employee_id': self.employee_id,
            'test_date': '2026-02-18',
            'files': (io.BytesIO(_fake_xlsx_bytes()), f'run_{seq}.xlsx'),
        }
        self.result.results.append(
            self._req('post', '/simulation/experiment',
                      'POST /simulation/experiment',
                      data=data, content_type='multipart/form-data'))

    def add_and_delete_user(self, seq: int):
        """Admin-only: create then delete a temporary user."""
        eid = f'tmp_{self.employee_id[-5:]}_{seq:04d}'
        r_add = self._req('post', '/admin/user/add', 'POST /admin/user/add',
                          data={'employee_id': eid, 'password': 'pass123',
                                'role': 'lab_engineer'})
        self.result.results.append(r_add)

    # ── Full workflow ────────────────────────────────────────────────────────

    def run(self, cycles: int, write_heavy: bool):
        """Login then execute `cycles` mixed-workload cycles."""
        if not self.login():
            return  # Cannot proceed without authentication

        for i in range(cycles):
            # Every user reads on every cycle
            self.health_check()
            self.view_simulation()
            self.view_admin_monitor()   # no-op for non-admins

            # Write operations — frequency depends on role and write_heavy flag
            if self.role == 'lab_engineer' or write_heavy:
                self.submit_experiment(i)

            if self.role == 'admin' and write_heavy:
                self.add_and_delete_user(i)


# ── Tier orchestrator ─────────────────────────────────────────────────────────

def _seed_users(app, db, num_users: int):
    """Ensure all virtual users exist in the database."""
    from database import User
    roles = ('research_engineer', 'lab_engineer', 'admin')
    with app.app_context():
        for i in range(num_users):
            eid = f'stress_{i:05d}'
            role = roles[i % len(roles)]
            existing = User.query.filter_by(employee_id=eid).first()
            if existing:
                if not existing.is_active:
                    existing.is_active = True
            else:
                u = User(employee_id=eid, role=role, is_active=True)
                u.set_password('pass123')
                db.session.add(u)
        db.session.commit()


def run_tier(app, db, tier_num: int, num_users: int,
             requests_per_user: int, write_heavy: bool) -> TierResult:
    """Run one concurrency tier and return its aggregated results."""
    result = TierResult(
        tier=tier_num,
        num_users=num_users,
        requests_per_user=requests_per_user,
        write_heavy=write_heavy,
    )

    _seed_users(app, db, num_users)

    roles = ('research_engineer', 'lab_engineer', 'admin')
    workers = [
        VirtualUser(app, i, roles[i % len(roles)], result)
        for i in range(num_users)
    ]

    threads = [
        threading.Thread(
            target=w.run,
            args=(requests_per_user, write_heavy),
            daemon=True,
            name=f'user-{i}',
        )
        for i, w in enumerate(workers)
    ]

    t0 = time.perf_counter()
    for t in threads:
        t.start()

    deadline = t0 + VirtualUser.WORKER_TIMEOUT
    for t in threads:
        remaining = deadline - time.perf_counter()
        if remaining > 0:
            t.join(timeout=remaining)
        if t.is_alive():
            result.crashed_workers += 1

    result.wall_time_s = time.perf_counter() - t0
    return result


# ── Reporting ─────────────────────────────────────────────────────────────────

def _bar(value: float, max_val: float, width: int = 28,
         fill: str = '█', empty: str = '░') -> str:
    pct = min(value / max_val, 1.0) if max_val else 0
    filled = round(width * pct)
    return fill * filled + empty * (width - filled)


def _percentile(data: list, pct: float) -> float:
    if not data:
        return 0.0
    idx = max(0, int(len(data) * pct) - 1)
    return data[idx]


def _status_label(r: TierResult) -> str:
    """Status based on effective error rate, latency, AND hung threads."""
    eff = r.effective_error_rate
    lats = r.latencies()
    p99 = _percentile(lats, 0.99) if lats else 0
    if r.hung_pct >= 50:
        return RED('✗ STALLED  (>50% threads hung)')
    if r.hung_pct >= 20 or eff >= 30:
        return RED('✗ FAILING')
    if r.hung_pct >= 5 or eff >= 10 or p99 >= 10_000:
        return YELLOW('⚠ WARNING  (latency/hang pressure)')
    if r.hung_pct > 0 or eff >= 2 or p99 >= 5_000:
        return YELLOW('~ DEGRADED')
    return GREEN('✓ HEALTHY')


def print_tier_report(r: TierResult):
    lats = r.latencies()
    W = 65

    print()
    print(BOLD(f"{'─'*W}"))
    mode = 'write-heavy' if r.write_heavy else 'mixed'
    print(BOLD(f"  TIER {r.tier}") +
          f"  |  {CYAN(str(r.num_users) + ' users')}  |  "
          f"{r.requests_per_user} cycles/user  |  {mode}")
    print(f"{'─'*W}")

    # Core numbers
    print(f"  {'Total requests':<20}: {r.total}")
    ok_pct = 100 - r.error_rate
    print(f"  {'Successes':<20}: {GREEN(str(r.successes))}  ({ok_pct:.1f}%)")
    fail_str = RED(str(r.failures)) if r.failures else str(r.failures)
    print(f"  {'Failures':<20}: {fail_str}  ({r.error_rate:.1f}%)")

    if r.crashed_workers:
        hung_str = (RED if r.hung_pct >= 20 else YELLOW)(
            f"{r.crashed_workers} ({r.hung_pct:.0f}% of workers)")
        print(f"  {'Hung threads':<20}: {hung_str}  "
              f"(timed out after {VirtualUser.WORKER_TIMEOUT}s)")

    if r.slow_requests:
        slow_pct = r.slow_requests / r.total * 100
        slow_str = (RED if slow_pct > 30 else YELLOW)(
            f"{r.slow_requests} ({slow_pct:.1f}%)")
        print(f"  {'Slow (>5s)':<20}: {slow_str}")

    print(f"  {'Wall time':<20}: {r.wall_time_s:.2f}s")
    print(f"  {'Throughput':<20}: {r.throughput:.1f} req/s")

    # Latency
    if lats:
        p50 = statistics.median(lats)
        p95 = _percentile(lats, 0.95)
        p99 = _percentile(lats, 0.99)
        print(f"  {'Latency (ms)':<20}: "
              f"min={lats[0]:.0f}  p50={p50:.0f}  "
              f"p95={p95:.0f}  p99={p99:.0f}  max={lats[-1]:.0f}")
    else:
        print(f"  {'Latency (ms)':<20}: N/A (all requests failed)")

    # Error breakdown
    errs = r.error_breakdown()
    if errs:
        print(f"\n  Error breakdown:")
        for etype, count in errs.items():
            pct = count / r.total * 100
            sample = next(
                (res.error_detail for res in r.results
                 if res.error_type == etype and res.error_detail),
                ''
            )
            print(f"    {RED(etype):<35} {count:>4}x  ({pct:.1f}%)")
            if sample:
                print(f"      {DIM(sample[:70])}")

    # Endpoint breakdown
    ep = r.endpoint_stats()
    if len(ep) > 1:
        print(f"\n  Endpoint breakdown:")
        for label, (tot, fail) in sorted(ep.items()):
            ep_err = fail / tot * 100 if tot else 0
            status = GREEN('ok') if fail == 0 else (
                YELLOW('warn') if ep_err < 20 else RED('fail'))
            print(f"    {label:<40} {tot:>4} reqs  {fail:>3} failed  [{status}]")

    # Visual bars
    max_tput = max(200, r.throughput)
    err_bar = RED(_bar(r.error_rate, 100)) if r.error_rate >= 10 else (
              YELLOW(_bar(r.error_rate, 100)) if r.error_rate >= 2 else
              GREEN(_bar(r.error_rate, 100)))
    print(f"\n  Error rate  [{err_bar}] {r.error_rate:.1f}%")
    print(f"  Throughput  [{_bar(r.throughput, max_tput)}] {r.throughput:.1f} req/s")
    if r.effective_error_rate != r.error_rate:
        print(f"  {'Effective err rate':<20}: {r.effective_error_rate:.1f}%  "
              f"(HTTP {r.error_rate:.1f}% + hung-thread penalty)")
    print(f"\n  Status: {_status_label(r)}")

    # First crash traceback
    if r.first_crash:
        print(f"\n  {BOLD(RED('FIRST CRASH TRACEBACK:'))}")
        for line in r.first_crash.strip().splitlines()[-12:]:
            print(f"    {DIM(line)}")


def print_final_summary(all_results: List[TierResult]):
    W = 65
    print()
    print(BOLD('=' * W))
    print(BOLD('  STRESS TEST FINAL SUMMARY'))
    print(BOLD('=' * W))
    print(f"  {'Users':>6}  {'Req/s':>7}  {'Total':>6}  "
          f"{'Err%':>6}  {'p50ms':>6}  {'p99ms':>6}  Status")
    print(f"  {'─'*6}  {'─'*7}  {'─'*6}  {'─'*6}  {'─'*6}  {'─'*6}  {'─'*14}")

    for r in all_results:
        lats = r.latencies()
        p50 = statistics.median(lats) if lats else 0
        p99 = _percentile(lats, 0.99) if lats else 0
        label = _status_label(r)
        hung = (f'  {RED(str(r.crashed_workers)+" hung")}' if r.crashed_workers else '')
        print(f"  {r.num_users:>6}  {r.throughput:>7.1f}  {r.total:>6}  "
              f"{r.error_rate:>6.1f}  {p50:>6.0f}  {p99:>6.0f}  {label}{hung}")

    # ── Break point analysis ─────────────────────────────────────────────────
    print()

    # A tier is "broken" when effective error rate (HTTP errors + hung penalty) >= 10%
    # OR p99 latency > 10s, OR >20% threads hung
    def _is_broken(r: TierResult) -> bool:
        lats = r.latencies()
        p99 = _percentile(lats, 0.99) if lats else 0
        return r.effective_error_rate >= 10 or r.hung_pct >= 20 or p99 >= 10_000

    def _is_degraded(r: TierResult) -> bool:
        lats = r.latencies()
        p99 = _percentile(lats, 0.99) if lats else 0
        return r.effective_error_rate >= 2 or r.hung_pct > 0 or p99 >= 5_000

    failing  = [r for r in all_results if _is_broken(r)]
    degraded = [r for r in all_results if _is_degraded(r) and not _is_broken(r)]

    if failing:
        bp = failing[0]
        lats = bp.latencies()
        p99 = _percentile(lats, 0.99) if lats else 0
        print(BOLD(RED('  BREAK POINT DETECTED')))
        print(f"  System breaks at {CYAN(str(bp.num_users))} concurrent users")
        print(f"  HTTP error rate  : {bp.error_rate:.1f}%")
        print(f"  Hung threads     : {bp.crashed_workers} / {bp.num_users} "
              f"({bp.hung_pct:.0f}%)")
        print(f"  p99 latency      : {p99:.0f} ms")
        print(f"  Throughput       : {bp.throughput:.1f} req/s")

        errs = bp.error_breakdown()
        if errs:
            print()
            print(BOLD('  PRIMARY HTTP FAILURE CAUSE(S):'))
            for i, (etype, count) in enumerate(list(errs.items())[:3]):
                sample = next(
                    (res.error_detail for res in bp.results
                     if res.error_type == etype and res.error_detail),
                    'no detail captured'
                )
                print(f"  {i+1}. {RED(etype)} — {count} occurrences")
                print(f"     {DIM(sample[:90])}")

        if bp.hung_pct >= 20:
            print()
            print(RED(f"  STALL DIAGNOSIS: {bp.crashed_workers}/{bp.num_users} threads "
                      f"never completed within {VirtualUser.WORKER_TIMEOUT}s."))
            print(f"  This indicates SQLite write-lock queuing or connection-pool "
                  f"exhaustion under concurrent load.")
            print(f"  The system is not 'crashing' — it is blocking. Requests queue")
            print(f"  until SQLite's default 5-second lock timeout expires, causing")
            print(f"  cascading slowdowns that stall the thread pool.")

        if bp.first_crash:
            print()
            print(BOLD('  FIRST CRASH TRACEBACK:'))
            for line in bp.first_crash.strip().splitlines()[-14:]:
                print(f"    {DIM(line)}")
    elif degraded:
        dp = degraded[0]
        print(YELLOW(f"  DEGRADATION begins at {CYAN(str(dp.num_users))} concurrent users"))
        print(f"  No hard failure reached within tested tiers.")
    else:
        last = all_results[-1]
        print(GREEN(f"  System handled all {last.num_users} users with no degradation."))
        print(f"  Extend --tiers or use --write-heavy to find the limit.")

    # ── Capacity summary ─────────────────────────────────────────────────────
    print()
    print(BOLD('  CAPACITY ESTIMATES:'))
    healthy = [r for r in all_results if not _is_degraded(r) and not _is_broken(r)]
    if healthy:
        best = healthy[-1]
        print(f"  Sustained healthy load   : ≤ {CYAN(str(best.num_users))} users "
              f"@ {best.throughput:.0f} req/s  (p99 < 5s, 0% hung)")
    if degraded:
        d0, dN = degraded[0], degraded[-1]
        print(f"  Degraded-but-functional  : {CYAN(str(d0.num_users))}–"
              f"{CYAN(str(dN.num_users))} users  (slow but no errors)")
    if failing:
        print(f"  Break point (stall/error): ≥ {RED(str(failing[0].num_users))} users")

    print(BOLD('=' * W))
    print()


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description='MGG System Stress Test — finds concurrent-user capacity limits',
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        '--tiers', default='2,5,10,20,50',
        help='Comma-separated concurrent user counts (default: 2,5,10,20,50)',
    )
    parser.add_argument(
        '--requests', type=int, default=8,
        help='Workload cycles per user per tier (default: 8)',
    )
    parser.add_argument(
        '--write-heavy', action='store_true',
        help='All roles perform write ops — stresses SQLite write lock harder',
    )
    parser.add_argument(
        '--stop-on-fail', action='store_true',
        help='Abort remaining tiers once error rate exceeds 30%%',
    )
    args = parser.parse_args()

    try:
        tiers = [int(x.strip()) for x in args.tiers.split(',')]
    except ValueError:
        print('ERROR: --tiers must be comma-separated integers, e.g. 5,10,25')
        sys.exit(1)

    W = 65
    print()
    print(BOLD('=' * W))
    print(BOLD('  MGG SYSTEM STRESS TEST'))
    print(BOLD('=' * W))
    print(f"  Tiers       : {tiers}")
    print(f"  Cycles/user : {args.requests}")
    print(f"  Mode        : {'write-heavy' if args.write_heavy else 'mixed (reads + writes)'}")
    print(f"  Stop on fail: {args.stop_on_fail}")
    print()

    db_fd, db_path = tempfile.mkstemp(suffix='.db')
    upload_dir = tempfile.mkdtemp()

    try:
        print(f"  Initialising application … ", end='', flush=True)
        app = _make_app(db_path, upload_dir)
        with app.app_context():
            from database.extensions import db
        print(GREEN('done'))
        print(f"  Database    : {db_path}")
        print(f"  Upload dir  : {upload_dir}")
        print()

        all_results: List[TierResult] = []

        for tier_num, num_users in enumerate(tiers, 1):
            print(f"  Running tier {tier_num}/{len(tiers)}: "
                  f"{CYAN(str(num_users))} concurrent users … ", end='', flush=True)
            t0 = time.perf_counter()
            result = run_tier(app, db, tier_num, num_users,
                              args.requests, args.write_heavy)
            elapsed = time.perf_counter() - t0
            status_short = ('OK' if result.error_rate < 2 else
                            'DEGRADED' if result.error_rate < 10 else 'FAILING')
            colour_fn = GREEN if status_short == 'OK' else (
                YELLOW if status_short == 'DEGRADED' else RED)
            print(colour_fn(status_short) +
                  f"  ({elapsed:.1f}s, {result.total} reqs, "
                  f"{result.error_rate:.1f}% err)")
            all_results.append(result)
            print_tier_report(result)

            if args.stop_on_fail and result.effective_error_rate >= 30:
                print(f"\n  {RED('--stop-on-fail triggered')}: "
                      f"effective error rate {result.effective_error_rate:.1f}% ≥ 30%")
                break

            if tier_num < len(tiers):
                print(f"\n  {DIM('Cooling down 3s before next tier …')}")
                time.sleep(3)

        print_final_summary(all_results)

    finally:
        try:
            os.close(db_fd)
        except OSError:
            pass
        try:
            os.unlink(db_path)
        except OSError:
            pass
        shutil.rmtree(upload_dir, ignore_errors=True)


if __name__ == '__main__':
    main()
