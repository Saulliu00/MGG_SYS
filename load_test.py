#!/usr/bin/env python3
"""
Load Test for MGG_SYS

Simulates concurrent users exercising critical endpoints:
  - Authentication (login)
  - Work Order list & detail
  - Simulation history
  - Admin system monitor (admin users only)

Usage:
    python load_test.py [--url URL] [--users N] [--employee-id ID] [--password PW]

Examples:
    python load_test.py
    python load_test.py --url http://127.0.0.1:5001 --users 50
    python load_test.py --employee-id myuser --password mypass
"""

import argparse
import re
import statistics
import sys
import threading
import time
from collections import defaultdict
from datetime import datetime

import requests

# ---------------------------------------------------------------------------
# Defaults (overridden by CLI args)
# ---------------------------------------------------------------------------
DEFAULT_URL = "http://127.0.0.1:5001"
DEFAULT_USERS = 100
DEFAULT_EMPLOYEE_ID = "admin"
DEFAULT_PASSWORD = "admin123"

# Work orders to probe in the detail endpoint; non-existent ones still exercise
# the route and return 404 — which is a valid, non-error response for load tests.
SAMPLE_WORK_ORDERS = ["WO-2026-001", "WO-2026-002", "WO-2026-003"]

# ---------------------------------------------------------------------------
# Shared state (protected by lock)
# ---------------------------------------------------------------------------
results: dict[str, list[float]] = defaultdict(list)
success_counts: dict[str, int] = defaultdict(int)
failure_counts: dict[str, int] = defaultdict(int)
errors: list[str] = []
lock = threading.Lock()


# ---------------------------------------------------------------------------
# User simulation
# ---------------------------------------------------------------------------

class LoadTestUser:
    """Simulates a single authenticated user making a sequence of requests."""

    def __init__(self, user_id: int, base_url: str, employee_id: str, password: str):
        self.user_id = user_id
        self.base_url = base_url
        self.employee_id = employee_id
        self.password = password
        self.session = requests.Session()
        self.session.headers.update({'User-Agent': f'LoadTest-User-{user_id}'})

    def _record(self, endpoint: str, duration: float, ok: bool, msg: str = ''):
        with lock:
            results[endpoint].append(duration)
            if ok:
                success_counts[endpoint] += 1
            else:
                failure_counts[endpoint] += 1
                if msg:
                    errors.append(msg)

    def login(self) -> bool:
        start = time.time()
        try:
            # Fetch login page to obtain CSRF token
            resp = self.session.get(f"{self.base_url}/auth/login", timeout=10)
            csrf_token = None
            match = re.search(r'<meta name="csrf-token" content="([^"]+)"', resp.text)
            if match:
                csrf_token = match.group(1)

            login_data = {
                'employee_id': self.employee_id,
                'password': self.password,
                'remember': False,
            }
            headers = {'X-CSRFToken': csrf_token} if csrf_token else {}
            if csrf_token:
                login_data['csrf_token'] = csrf_token

            resp = self.session.post(
                f"{self.base_url}/auth/login",
                data=login_data,
                allow_redirects=True,
                headers=headers,
                timeout=10,
            )
            duration = time.time() - start
            ok = resp.status_code == 200 and '/simulation' in resp.url
            self._record(
                'login', duration, ok,
                f'User {self.user_id}: Login failed — status={resp.status_code} url={resp.url}' if not ok else '',
            )
            return ok
        except Exception as exc:
            duration = time.time() - start
            self._record('login', duration, False, f'User {self.user_id}: Login exception — {exc}')
            return False

    def get_work_order_list(self) -> bool:
        start = time.time()
        try:
            resp = self.session.get(f"{self.base_url}/work_order/list", timeout=10)
            duration = time.time() - start
            ok = resp.status_code == 200
            self._record(
                'work_order_list', duration, ok,
                f'User {self.user_id}: work_order/list — status={resp.status_code}' if not ok else '',
            )
            return ok
        except Exception as exc:
            duration = time.time() - start
            self._record('work_order_list', duration, False, f'User {self.user_id}: work_order/list exception — {exc}')
            return False

    def get_work_order_detail(self, work_order: str) -> bool:
        start = time.time()
        try:
            resp = self.session.get(f"{self.base_url}/work_order/{work_order}/detail", timeout=15)
            duration = time.time() - start
            # 200 (found) and 404 (not found) are both valid non-error responses
            ok = resp.status_code in (200, 404)
            self._record(
                'work_order_detail', duration, ok,
                f'User {self.user_id}: work_order/detail — status={resp.status_code}' if not ok else '',
            )
            return ok
        except Exception as exc:
            duration = time.time() - start
            self._record('work_order_detail', duration, False,
                         f'User {self.user_id}: work_order/detail exception — {exc}')
            return False

    def get_simulation_history(self) -> bool:
        start = time.time()
        try:
            resp = self.session.get(f"{self.base_url}/simulation/history", timeout=10)
            duration = time.time() - start
            ok = resp.status_code == 200
            self._record(
                'simulation_history', duration, ok,
                f'User {self.user_id}: simulation/history — status={resp.status_code}' if not ok else '',
            )
            return ok
        except Exception as exc:
            duration = time.time() - start
            self._record('simulation_history', duration, False,
                         f'User {self.user_id}: simulation/history exception — {exc}')
            return False

    def get_admin_monitor(self) -> bool:
        """Admin system monitor — only meaningful for admin accounts; others get 403."""
        start = time.time()
        try:
            resp = self.session.get(f"{self.base_url}/admin/monitor", timeout=10)
            duration = time.time() - start
            ok = resp.status_code in (200, 403)
            self._record(
                'admin_monitor', duration, ok,
                f'User {self.user_id}: admin/monitor — status={resp.status_code}' if not ok else '',
            )
            return ok
        except Exception as exc:
            duration = time.time() - start
            self._record('admin_monitor', duration, False,
                         f'User {self.user_id}: admin/monitor exception — {exc}')
            return False

    def run_scenario(self):
        """Realistic user journey: login → browse work orders → simulation history → admin monitor."""
        if not self.login():
            return

        # Browse work order list several times (lightweight, common operation)
        for _ in range(3):
            self.get_work_order_list()
            time.sleep(0.1)

        # Drill into individual work order details (heavier chart + stats generation)
        for wo in SAMPLE_WORK_ORDERS:
            self.get_work_order_detail(wo)
            time.sleep(0.2)

        # Check simulation history
        self.get_simulation_history()

        # Admin system monitor (will 403 for non-admin — that's fine)
        self.get_admin_monitor()


# ---------------------------------------------------------------------------
# Thread worker
# ---------------------------------------------------------------------------

def worker(user_id: int, base_url: str, employee_id: str, password: str):
    LoadTestUser(user_id, base_url, employee_id, password).run_scenario()


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------

def _p95(times: list[float]) -> float:
    """Return 95th-percentile response time; safe for single-element lists."""
    if len(times) < 2:
        return times[0] if times else 0.0
    return statistics.quantiles(times, n=20)[18]


def print_results(num_users: int, base_url: str, elapsed: float):
    total_requests = sum(len(v) for v in results.values())
    total_errors = sum(failure_counts.values())

    print()
    print('=' * 80)
    print('LOAD TEST RESULTS')
    print('=' * 80)
    print(f'  Target URL      : {base_url}')
    print(f'  Concurrent users: {num_users}')
    print(f'  Wall-clock time : {elapsed:.2f}s')
    print(f'  Total requests  : {total_requests}')
    print(f'  Total failures  : {total_errors}')

    print()
    print('-' * 92)
    print(f"{'Endpoint':<25} {'Req':>5} {'OK':>5} {'Fail':>5} {'Mean':>8} {'Median':>8} {'95th%':>8} {'Max':>8}")
    print('-' * 92)

    for endpoint in sorted(results):
        times = results[endpoint]
        if not times:
            continue
        mean   = statistics.mean(times)
        median = statistics.median(times)
        p95    = _p95(times)
        mx     = max(times)
        ok     = success_counts[endpoint]
        fail   = failure_counts[endpoint]
        print(f'{endpoint:<25} {len(times):>5} {ok:>5} {fail:>5} {mean:>8.3f} {median:>8.3f} {p95:>8.3f} {mx:>8.3f}')

    print('-' * 92)

    if total_requests > 0:
        throughput = total_requests / elapsed
        print(f'\n  Throughput: {throughput:.2f} requests/second')

    # Error details
    if errors:
        print()
        print('=' * 80)
        print('ERRORS (first 15)')
        print('=' * 80)
        for err in errors[:15]:
            print(f'  - {err}')
        if len(errors) > 15:
            print(f'  ... and {len(errors) - 15} more')

    # Pass/Fail summary
    print()
    print('=' * 80)
    print('PASS / FAIL CRITERIA')
    print('=' * 80)

    passed = True

    # 1. Overall error rate
    error_rate = total_errors / max(total_requests, 1) * 100
    ok1 = error_rate < 5
    passed = passed and ok1
    status = 'PASS' if ok1 else 'FAIL'
    print(f'  1. Error rate        : {error_rate:5.2f}%  — {status} (threshold < 5%)')

    # 2. Work order detail 95th percentile
    if results['work_order_detail']:
        p95_detail = _p95(results['work_order_detail'])
        ok2 = p95_detail < 5.0
        passed = passed and ok2
        status = 'PASS' if ok2 else 'FAIL'
        print(f'  2. Detail 95th %ile  : {p95_detail:5.3f}s  — {status} (threshold < 5s)')

    # 3. Work order detail mean
    if results['work_order_detail']:
        mean_detail = statistics.mean(results['work_order_detail'])
        ok3 = mean_detail < 2.0
        status = 'PASS' if ok3 else 'WARN'
        print(f'  3. Detail mean       : {mean_detail:5.3f}s  — {status} (threshold < 2s)')

    # 4. Login success rate
    if results['login']:
        login_ok = success_counts['login']
        login_rate = login_ok / len(results['login']) * 100
        ok4 = login_rate >= 95
        passed = passed and ok4
        status = 'PASS' if ok4 else 'FAIL'
        print(f'  4. Login success     : {login_rate:5.1f}%  — {status} (threshold >= 95%)')

    print()
    print('  OVERALL:', 'PASS' if passed else 'FAIL')
    print('=' * 80)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description='MGG_SYS load test — simulates concurrent users against a live server.',
    )
    parser.add_argument('--url', default=DEFAULT_URL,
                        help=f'Base URL of the running Flask app (default: {DEFAULT_URL})')
    parser.add_argument('--users', type=int, default=DEFAULT_USERS,
                        help=f'Number of concurrent users (default: {DEFAULT_USERS})')
    parser.add_argument('--employee-id', default=DEFAULT_EMPLOYEE_ID,
                        help=f'Login employee ID (default: {DEFAULT_EMPLOYEE_ID})')
    parser.add_argument('--password', default=DEFAULT_PASSWORD,
                        help='Login password (default: admin123)')
    return parser.parse_args()


def main():
    args = parse_args()
    base_url    = args.url.rstrip('/')
    num_users   = args.users
    employee_id = args.employee_id
    password    = args.password

    print('=' * 80)
    print('MGG_SYS LOAD TEST')
    print('=' * 80)
    print(f'  Target  : {base_url}')
    print(f'  Users   : {num_users}')
    print(f'  Account : {employee_id}')
    print()
    print('Make sure the Flask server is running:')
    print('  source venv/bin/activate && python run.py')

    # Verify server is up before spawning threads
    try:
        resp = requests.get(base_url, timeout=5)
        print(f'\nServer accessible (HTTP {resp.status_code})')
    except Exception as exc:
        print(f'\nServer NOT accessible: {exc}')
        print('Please start the Flask server first.')
        sys.exit(1)

    print(f'\nStarting at {datetime.now().strftime("%Y-%m-%d %H:%M:%S")} ...\n')
    start_time = time.time()

    threads = [
        threading.Thread(target=worker, args=(i, base_url, employee_id, password), daemon=True)
        for i in range(num_users)
    ]
    for t in threads:
        t.start()
        time.sleep(0.01)   # small stagger to avoid thundering-herd on login
    for t in threads:
        t.join()

    elapsed = time.time() - start_time
    print(f'Test completed in {elapsed:.2f}s')
    print_results(num_users, base_url, elapsed)


if __name__ == '__main__':
    main()
