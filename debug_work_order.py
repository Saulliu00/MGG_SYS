"""Debug script to check work order data"""
import sys
sys.path.insert(0, '.')

from app import create_app
from app.models import Simulation, TestResult
import json

app = create_app()

with app.app_context():
    print("=" * 70)
    print("WORK ORDER DEBUG")
    print("=" * 70)
    
    # Check simulations with work orders
    sims_with_wo = Simulation.query.filter(
        Simulation.work_order.isnot(None),
        Simulation.work_order != ''
    ).all()
    
    print(f"\n✓ Found {len(sims_with_wo)} simulations with work orders")
    
    if not sims_with_wo:
        print("\n❌ NO SIMULATIONS WITH WORK ORDERS FOUND")
        print("   This is the problem! Upload some simulations with work orders first.")
        sys.exit(0)
    
    # Check first work order in detail
    first_wo = sims_with_wo[0].work_order
    print(f"\n📋 Checking work order: {first_wo}")
    
    # Get all sims for this work order
    all_sims = Simulation.query.filter_by(work_order=first_wo).all()
    print(f"   Simulations with this work order: {len(all_sims)}")
    
    sim_ids = [s.id for s in all_sims]
    print(f"   Simulation IDs: {sim_ids}")
    
    # Check test results
    test_results = TestResult.query.filter(
        TestResult.simulation_id.in_(sim_ids)
    ).all()
    
    print(f"\n📊 Test results linked to this work order: {len(test_results)}")
    
    if not test_results:
        print("\n❌ NO TEST RESULTS FOUND FOR THIS WORK ORDER")
        print("   Possible causes:")
        print("   1. Test results exist but simulation_id is NULL")
        print("   2. Test results exist but linked to wrong simulation_id")
        print("   3. No test results uploaded yet")
        
        # Check if there are ANY test results in the database
        all_test_results = TestResult.query.all()
        print(f"\n   Total test results in database: {len(all_test_results)}")
        
        if all_test_results:
            print("\n   Sample test result:")
            tr = all_test_results[0]
            print(f"   - ID: {tr.id}")
            print(f"   - simulation_id: {tr.simulation_id}")
            print(f"   - filename: {tr.filename}")
            print(f"   - user_id: {tr.user_id}")
            print(f"   - has data: {bool(tr.data)}")
            
            # Check if any test results have NULL simulation_id
            orphaned = TestResult.query.filter_by(simulation_id=None).count()
            print(f"\n   ⚠️  Orphaned test results (simulation_id=NULL): {orphaned}")
            if orphaned > 0:
                print("      THIS IS THE BUG! Test results exist but aren't linked to simulations")
    else:
        print("\n✓ Test results found:")
        for i, tr in enumerate(test_results, 1):
            print(f"   {i}. {tr.filename}")
            print(f"      - ID: {tr.id}")
            print(f"      - simulation_id: {tr.simulation_id}")
            print(f"      - user_id: {tr.user_id}")
            
            # Check data validity
            if tr.data:
                try:
                    d = json.loads(tr.data)
                    has_time = bool(d.get('time'))
                    has_pressure = bool(d.get('pressure'))
                    print(f"      - data: ✓ (time: {has_time}, pressure: {has_pressure})")
                    
                    if not (has_time and has_pressure):
                        print(f"      ❌ INVALID DATA STRUCTURE!")
                except Exception as e:
                    print(f"      ❌ JSON PARSE ERROR: {e}")
            else:
                print(f"      ❌ NO DATA!")
    
    print("\n" + "=" * 70)
