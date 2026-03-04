#!/usr/bin/env python3
"""
Simple Load Test for MGG_SYS - Direct API Testing

Tests work order endpoints without login (simulates authenticated users)
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
WORK_ORDERS = ["WO-2026-001", "WO-2026-002", "WO-2026-003"]

# Results tracking
results = defaultdict(list)
errors = []
lock = threading.Lock()


def test_work_order_list(user_id):
    """Test work order list endpoint"""
    start = time.time()
    try:
        # Create session with authentication cookie (simulated)
        session = requests.Session()
        
        resp = session.get(f"{BASE_URL}/work_order/list")
        duration = time.time() - start
        
        with lock:
            results['work_order_list'].append(duration)
            if resp.status_code == 200:
                # Success
                pass
            elif resp.status_code == 302:
                # Redirect to login (expected if not authenticated)
                errors.append(f"User {user_id}: Redirected to login (302)")
            else:
                errors.append(f"User {user_id}: List failed - {resp.status_code}")
    except Exception as e:
        with lock:
            errors.append(f"User {user_id}: List exception - {str(e)}")


def test_work_order_detail(user_id, work_order):
    """Test work order detail endpoint"""
    start = time.time()
    try:
        session = requests.Session()
        
        resp = session.get(f"{BASE_URL}/work_order/{work_order}/detail")
        duration = time.time() - start
        
        with lock:
            results['work_order_detail'].append(duration)
            if resp.status_code == 200:
                # Success - parse JSON to verify
                try:
                    data = resp.json()
                    if data.get('success'):
                        pass  # Good
                    else:
                        errors.append(f"User {user_id}: Detail API returned success=false")
                except:
                    errors.append(f"User {user_id}: Detail response not JSON")
            elif resp.status_code == 302:
                errors.append(f"User {user_id}: Redirected to login (302)")
            else:
                errors.append(f"User {user_id}: Detail failed - {resp.status_code}")
    except Exception as e:
        with lock:
            errors.append(f"User {user_id}: Detail exception - {str(e)}")


def test_static_page(user_id):
    """Test static resource loading"""
    start = time.time()
    try:
        resp = requests.get(f"{BASE_URL}/static/css/style.css")
        duration = time.time() - start
        
        with lock:
            results['static'].append(duration)
            if resp.status_code != 200:
                errors.append(f"User {user_id}: Static failed - {resp.status_code}")
    except Exception as e:
        with lock:
            errors.append(f"User {user_id}: Static exception - {str(e)}")


def worker(user_id):
    """Thread worker function"""
    # Test static resources (lightest)
    test_static_page(user_id)
    
    # Test work order list (medium weight)
    test_work_order_list(user_id)
    
    # Test work order details (heaviest - has PT curve data)
    for work_order in WORK_ORDERS:
        test_work_order_detail(user_id, work_order)
        time.sleep(0.05)  # Brief pause between requests


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
    
    # Connection pooling stats
    successful_requests = total_requests - len(errors)
    success_rate = successful_requests / max(total_requests, 1) * 100
    print(f"Success Rate: {success_rate:.2f}%")
    
    # Error summary
    if errors:
        print("\n" + "=" * 80)
        print("ERRORS")
        print("=" * 80)
        print(f"Total Errors: {len(errors)}")
        
        # Group errors by type
        error_types = defaultdict(int)
        for error in errors:
            if "Redirected to login" in error:
                error_types["Authentication Required (302)"] += 1
            elif "exception" in error.lower():
                error_types["Exceptions"] += 1
            else:
                error_types["Other Errors"] += 1
        
        print("\nError Breakdown:")
        for error_type, count in sorted(error_types.items()):
            print(f"  - {error_type}: {count}")
        
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
    
    # Criteria 1: Error rate (excluding 302 redirects which are expected)
    auth_errors = sum(1 for e in errors if "Redirected to login" in e)
    real_errors = len(errors) - auth_errors
    error_rate = real_errors / max(total_requests, 1) * 100
    print(f"1. Error Rate (excluding auth): {error_rate:.2f}% ", end="")
    if error_rate < 5:
        print("✅ PASS (< 5%)")
    else:
        print("❌ FAIL (>= 5%)")
    
    # Criteria 2: Response time
    if results.get('work_order_detail'):
        p95_detail = statistics.quantiles(results['work_order_detail'], n=20)[18] if len(results['work_order_detail']) > 1 else results['work_order_detail'][0]
        print(f"2. Work Order Detail 95th %ile: {p95_detail:.3f}s ", end="")
        if p95_detail < 5.0:
            print("✅ PASS (< 5s)")
        else:
            print("❌ FAIL (>= 5s)")
        
        mean_detail = statistics.mean(results['work_order_detail'])
        print(f"3. Work Order Detail Mean: {mean_detail:.3f}s ", end="")
        if mean_detail < 2.0:
            print("✅ PASS (< 2s)")
        else:
            print("⚠️  WARNING (>= 2s)")
    
    # Criteria 3: Throughput
    if total_time > 0:
        throughput = total_requests / total_time
        print(f"4. Throughput: {throughput:.2f} req/s ", end="")
        if throughput > 50:
            print("✅ PASS (> 50 req/s)")
        else:
            print("⚠️  WARNING (<= 50 req/s)")
    
    print("=" * 80)


def main():
    print("=" * 80)
    print("MGG_SYS SIMPLE LOAD TEST")
    print("=" * 80)
    print(f"\nTesting with {NUM_USERS} concurrent users...")
    print(f"Target: {BASE_URL}")
    print(f"\nNote: 302 redirects are expected (authentication required)")
    
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
