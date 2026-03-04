#!/usr/bin/env python3
"""
Load Test for MGG_SYS - Test with 100 Concurrent Users

Tests critical endpoints:
- Login
- Work Order List
- Work Order Detail
- Simulation
"""

import time
import requests
import threading
import statistics
from collections import defaultdict
from datetime import datetime

# Configuration
BASE_URL = "http://127.0.0.1:5001"
NUM_USERS = 100
NUM_REQUESTS_PER_USER = 10

# Test data
WORK_ORDERS = ["WO-2026-001", "WO-2026-002", "WO-2026-003"]

# Results tracking
results = defaultdict(list)
errors = []
lock = threading.Lock()


class LoadTestUser:
    """Simulates a single user making requests"""
    
    def __init__(self, user_id):
        self.user_id = user_id
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': f'LoadTest-User-{user_id}'
        })
    
    def login(self):
        """Login as admin"""
        start = time.time()
        try:
            # Get login page to get CSRF token
            resp = self.session.get(f"{BASE_URL}/auth/login")
            
            # Extract CSRF token from meta tag
            csrf_token = None
            if 'csrf-token' in resp.text:
                # Simple extraction (not perfect but works for testing)
                import re
                match = re.search(r'<meta name="csrf-token" content="([^"]+)"', resp.text)
                if match:
                    csrf_token = match.group(1)
            
            # Login data
            login_data = {
                'employee_id': 'admin',
                'password': 'admin123',
                'remember': False
            }
            
            # Add CSRF token if found
            if csrf_token:
                login_data['csrf_token'] = csrf_token
            
            # Post login
            resp = self.session.post(
                f"{BASE_URL}/auth/login", 
                data=login_data, 
                allow_redirects=True,
                headers={'X-CSRFToken': csrf_token} if csrf_token else {}
            )
            duration = time.time() - start
            
            with lock:
                results['login'].append(duration)
                # Check if we were redirected to the main page (successful login)
                if resp.status_code == 200 and '/simulation' in resp.url:
                    return True
                else:
                    errors.append(f"User {self.user_id}: Login failed - {resp.status_code}, URL: {resp.url}")
                    return False
        except Exception as e:
            with lock:
                errors.append(f"User {self.user_id}: Login exception - {str(e)}")
            return False
    
    def get_work_order_list(self):
        """Get work order list"""
        start = time.time()
        try:
            resp = self.session.get(f"{BASE_URL}/work_order/list")
            duration = time.time() - start
            
            with lock:
                results['work_order_list'].append(duration)
                if resp.status_code != 200:
                    errors.append(f"User {self.user_id}: Work order list failed - {resp.status_code}")
                    return False
            return True
        except Exception as e:
            with lock:
                errors.append(f"User {self.user_id}: Work order list exception - {str(e)}")
            return False
    
    def get_work_order_detail(self, work_order):
        """Get work order detail with PT curves"""
        start = time.time()
        try:
            resp = self.session.get(f"{BASE_URL}/work_order/{work_order}/detail")
            duration = time.time() - start
            
            with lock:
                results['work_order_detail'].append(duration)
                if resp.status_code != 200:
                    errors.append(f"User {self.user_id}: Work order detail failed - {resp.status_code}")
                    return False
            return True
        except Exception as e:
            with lock:
                errors.append(f"User {self.user_id}: Work order detail exception - {str(e)}")
            return False
    
    def run_test_scenario(self):
        """Run a realistic user scenario"""
        # Login
        if not self.login():
            return
        
        # Get work order list (common operation)
        for _ in range(3):
            if not self.get_work_order_list():
                break
            time.sleep(0.1)  # Brief pause between requests
        
        # Get work order details (heaviest operation)
        for work_order in WORK_ORDERS:
            if not self.get_work_order_detail(work_order):
                break
            time.sleep(0.2)  # Simulate user viewing chart


def worker(user_id):
    """Thread worker function"""
    user = LoadTestUser(user_id)
    user.run_test_scenario()


def print_results():
    """Print test results"""
    print("\n" + "=" * 80)
    print("LOAD TEST RESULTS")
    print("=" * 80)
    print(f"\nTest Configuration:")
    print(f"  Target URL: {BASE_URL}")
    print(f"  Concurrent Users: {NUM_USERS}")
    print(f"  Total Requests: {sum(len(v) for v in results.values())}")
    print(f"  Errors: {len(errors)}")
    
    print("\n" + "-" * 80)
    print("Performance Metrics (seconds)")
    print("-" * 80)
    print(f"{'Endpoint':<25} {'Requests':<10} {'Mean':<10} {'Median':<10} {'95th %':<10} {'Max':<10}")
    print("-" * 80)
    
    for endpoint, times in sorted(results.items()):
        if not times:
            continue
        
        mean = statistics.mean(times)
        median = statistics.median(times)
        p95 = statistics.quantiles(times, n=20)[18] if len(times) > 1 else times[0]
        max_time = max(times)
        
        print(f"{endpoint:<25} {len(times):<10} {mean:<10.3f} {median:<10.3f} {p95:<10.3f} {max_time:<10.3f}")
    
    print("-" * 80)
    
    # Calculate throughput
    total_time = sum(sum(v) for v in results.values())
    total_requests = sum(len(v) for v in results.values())
    if total_time > 0:
        throughput = total_requests / total_time
        print(f"\nThroughput: {throughput:.2f} requests/second")
    
    # Error summary
    if errors:
        print("\n" + "=" * 80)
        print("ERRORS")
        print("=" * 80)
        print(f"Total Errors: {len(errors)}")
        print("\nFirst 10 errors:")
        for error in errors[:10]:
            print(f"  - {error}")
        if len(errors) > 10:
            print(f"  ... and {len(errors) - 10} more errors")
    else:
        print("\n✅ No errors!")
    
    # Pass/Fail criteria
    print("\n" + "=" * 80)
    print("PASS/FAIL CRITERIA")
    print("=" * 80)
    
    # Criteria 1: Error rate < 5%
    error_rate = len(errors) / max(total_requests, 1) * 100
    print(f"1. Error Rate: {error_rate:.2f}% ", end="")
    if error_rate < 5:
        print("✅ PASS (< 5%)")
    else:
        print("❌ FAIL (>= 5%)")
    
    # Criteria 2: 95th percentile response time
    if results['work_order_detail']:
        p95_detail = statistics.quantiles(results['work_order_detail'], n=20)[18]
        print(f"2. Work Order Detail 95th %ile: {p95_detail:.3f}s ", end="")
        if p95_detail < 5.0:
            print("✅ PASS (< 5s)")
        else:
            print("❌ FAIL (>= 5s)")
    
    # Criteria 3: Mean response time
    if results['work_order_detail']:
        mean_detail = statistics.mean(results['work_order_detail'])
        print(f"3. Work Order Detail Mean: {mean_detail:.3f}s ", end="")
        if mean_detail < 2.0:
            print("✅ PASS (< 2s)")
        else:
            print("⚠️  WARNING (>= 2s)")
    
    print("=" * 80)


def main():
    print("=" * 80)
    print("MGG_SYS LOAD TEST")
    print("=" * 80)
    print(f"\nStarting load test with {NUM_USERS} concurrent users...")
    print(f"Target: {BASE_URL}")
    print(f"\nMake sure the Flask server is running!")
    print("  cd /home/saul/.openclaw/workspace/MGG_SYS")
    print("  source venv/bin/activate")
    print("  python run.py")
    
    # Check if server is accessible
    try:
        resp = requests.get(BASE_URL, timeout=5)
        print(f"\n✅ Server is accessible (status {resp.status_code})")
    except Exception as e:
        print(f"\n❌ Server is NOT accessible: {e}")
        print("Please start the Flask server before running the load test.")
        return
    
    print(f"\nStarting test at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}...")
    start_time = time.time()
    
    # Create threads
    threads = []
    for i in range(NUM_USERS):
        thread = threading.Thread(target=worker, args=(i,))
        threads.append(thread)
    
    # Start all threads
    for thread in threads:
        thread.start()
        time.sleep(0.01)  # Stagger start slightly
    
    # Wait for all threads to complete
    for thread in threads:
        thread.join()
    
    elapsed_time = time.time() - start_time
    
    print(f"\nTest completed in {elapsed_time:.2f} seconds")
    
    # Print results
    print_results()


if __name__ == "__main__":
    main()
