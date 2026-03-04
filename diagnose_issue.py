#!/usr/bin/env python3
"""Diagnose why PT curves aren't showing"""

import os
import sys
import json

os.environ['SECRET_KEY'] = 'test'
sys.path.insert(0, os.path.dirname(__file__))

from app import create_app

app = create_app()

with app.app_context():
    # Test the work order service
    detail = app.work_order_service.get_work_order_detail('WO-2026-001')
    
    print("=" * 60)
    print("DIAGNOSIS: Work Order Detail API Response")
    print("=" * 60)
    
    print(f"\n1. Found: {detail.get('found')}")
    print(f"2. Simulation: {detail.get('simulation', {})}")
    print(f"3. Test Results Count: {len(detail.get('test_results', []))}")
    print(f"4. Statistics: {detail.get('statistics', {})}")
    
    # Check chart data structure
    chart = detail.get('chart', {})
    print(f"\n5. Chart Structure:")
    print(f"   - Has 'data' key: {'data' in chart}")
    print(f"   - Has 'layout' key: {'layout' in chart}")
    
    if 'data' in chart:
        print(f"   - Number of traces: {len(chart['data'])}")
        for i, trace in enumerate(chart['data']):
            print(f"   - Trace {i}: {trace.get('name', 'unnamed')}")
            print(f"     * x points: {len(trace.get('x', []))}")
            print(f"     * y points: {len(trace.get('y', []))}")
            print(f"     * mode: {trace.get('mode', 'N/A')}")
            print(f"     * line: {trace.get('line', 'N/A')}")
    
    # Print the full chart JSON (first 500 chars)
    chart_json = json.dumps(chart, indent=2)
    print(f"\n6. Chart JSON (first 500 chars):")
    print(chart_json[:500] + "...")
    
    print("\n" + "=" * 60)
    print("DIAGNOSIS COMPLETE")
    print("=" * 60)
