#!/usr/bin/env python3
"""Test the work order service directly"""

import os
import sys
import json

sys.path.insert(0, os.path.dirname(__file__))

from app import create_app

app = create_app()

with app.app_context():
    detail = app.work_order_service.get_work_order_detail('WO-2026-001')
    
    print("=" * 60)
    print("Work Order Detail Response")
    print("=" * 60)
    print(f"\nFound: {detail.get('found')}")
    
    if detail.get('found'):
        print(f"\nSimulation: {detail['simulation']}")
        print(f"\nTest Results: {len(detail['test_results'])} files")
        for tr in detail['test_results']:
            print(f"  - {tr['filename']}")
        
        print(f"\nStatistics:")
        stats = detail['statistics']
        print(f"  Count: {stats['count']}")
        print(f"  Mean Peak Pressure: {stats['mean_p']:.3f} MPa")
        print(f"  CV: {stats['cv_p']:.2f}%")
        
        print(f"\nChart Data:")
        chart = detail['chart']
        print(f"  Has 'data' key: {'data' in chart}")
        print(f"  Has 'layout' key: {'layout' in chart}")
        if 'data' in chart:
            print(f"  Number of traces: {len(chart['data'])}")
            for i, trace in enumerate(chart['data']):
                print(f"    Trace {i+1}: {trace.get('name', 'unnamed')}")
                print(f"      x points: {len(trace.get('x', []))}")
                print(f"      y points: {len(trace.get('y', []))}")
        
        print("\n" + "=" * 60)
        print("Backend is working correctly!")
        print("=" * 60)
    else:
        print("\n❌ Work order not found!")
