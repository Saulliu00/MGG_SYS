#!/usr/bin/env python3
"""
Script to populate test data for Work Order Query feature testing
Creates simulations with work orders and test results with PT curve data
"""

import os
import sys
import json
from datetime import datetime, timedelta

# Add app to path
sys.path.insert(0, os.path.dirname(__file__))

from app import create_app, db
from app.models import Simulation, TestResult
import numpy as np


def generate_pt_curve(peak_pressure=3.5, peak_time=2.0, noise_level=0.05):
    """Generate a realistic PT curve with some variation"""
    # Time points from -1 to 6 ms
    time = np.linspace(-1, 6, 700)
    
    # Create a smooth curve that rises to peak and then decays
    pressure = np.zeros_like(time)
    
    for i, t in enumerate(time):
        if t < 0:
            pressure[i] = 0
        elif t < peak_time:
            # Rising phase - exponential growth
            pressure[i] = peak_pressure * (1 - np.exp(-3 * t / peak_time))
        else:
            # Decay phase - exponential decay
            pressure[i] = peak_pressure * np.exp(-0.5 * (t - peak_time))
    
    # Add some noise
    noise = np.random.normal(0, noise_level, len(pressure))
    pressure = pressure + noise
    pressure = np.maximum(pressure, 0)  # Ensure non-negative
    
    return time.tolist(), pressure.tolist()


def create_test_data():
    """Create test data for Work Order Query feature"""
    app = create_app()
    
    with app.app_context():
        print("=" * 60)
        print("Creating test data for Work Order Query")
        print("=" * 60)
        
        # Create 3 work orders with multiple test results each
        work_orders = [
            {
                'work_order': 'WO-2026-001',
                'ignition_model': '115',
                'nc_type_1': 'E',
                'nc_usage_1': 450,
                'shell_model': '18',
                'current': 1.2,
                'test_results': 3,  # 3 experimental runs
                'peak_variation': 0.1  # 10% variation in peak pressure
            },
            {
                'work_order': 'WO-2026-002',
                'ignition_model': '116',
                'nc_type_1': 'F',
                'nc_usage_1': 500,
                'shell_model': '19',
                'current': 1.5,
                'test_results': 5,  # 5 experimental runs
                'peak_variation': 0.05  # 5% variation (better consistency)
            },
            {
                'work_order': 'WO-2026-003',
                'ignition_model': '117',
                'nc_type_1': 'D',
                'nc_usage_1': 400,
                'shell_model': '20',
                'current': 2.0,
                'test_results': 2,  # 2 experimental runs
                'peak_variation': 0.15  # 15% variation (poor consistency)
            }
        ]
        
        for wo_data in work_orders:
            print(f"\nCreating work order: {wo_data['work_order']}")
            
            # Create simulation record
            sim = Simulation(
                user_id=1,  # admin user
                work_order=wo_data['work_order'],
                ignition_model=wo_data['ignition_model'],
                nc_type_1=wo_data['nc_type_1'],
                nc_usage_1=wo_data['nc_usage_1'],
                shell_model=wo_data['shell_model'],
                current=wo_data['current'],
                sensor_model='30',
                body_model='3.5',
                created_at=datetime.utcnow() - timedelta(days=np.random.randint(1, 30))
            )
            db.session.add(sim)
            db.session.flush()  # Get the ID
            
            print(f"  Created simulation ID: {sim.id}")
            
            # Create multiple test results for this work order
            base_peak = 3.0 + np.random.random() * 1.5  # Random base peak between 3-4.5 MPa
            base_time = 1.8 + np.random.random() * 0.4  # Random base time between 1.8-2.2 ms
            
            for i in range(wo_data['test_results']):
                # Add variation to peak pressure and time
                peak_pressure = base_peak * (1 + np.random.uniform(-wo_data['peak_variation'], wo_data['peak_variation']))
                peak_time = base_time * (1 + np.random.uniform(-0.05, 0.05))  # Small time variation
                
                # Generate PT curve
                time_data, pressure_data = generate_pt_curve(peak_pressure, peak_time)
                
                # Create test result
                filename = f"{wo_data['work_order']}_run_{i+1:02d}.xlsx"
                test_result = TestResult(
                    simulation_id=sim.id,
                    user_id=1,
                    filename=filename,
                    data=json.dumps({
                        'time': time_data,
                        'pressure': pressure_data
                    }),
                    file_path=f'/fake/path/{filename}',
                    uploaded_at=datetime.utcnow() - timedelta(hours=np.random.randint(1, 72))
                )
                db.session.add(test_result)
                print(f"    Added test result: {filename} (peak={peak_pressure:.3f} MPa @ {peak_time:.3f} ms)")
            
        # Commit all changes
        db.session.commit()
        
        print("\n" + "=" * 60)
        print("✓ Test data created successfully!")
        print("=" * 60)
        print("\nSummary:")
        print(f"  - Created {len(work_orders)} work orders")
        print(f"  - Total test results: {sum(wo['test_results'] for wo in work_orders)}")
        print("\nYou can now test the Work Order Query feature at:")
        print("  http://127.0.0.1:5001/work_order/")
        print("=" * 60)


if __name__ == '__main__':
    create_test_data()
