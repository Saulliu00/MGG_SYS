"""
Seed Additional Data
Script to add more sample/test data beyond initial setup
"""

from datetime import datetime, timedelta
from db_config import get_db_session
from models import (
    User, WorkOrder, ForwardSimulation, SimulationTimeSeries,
    TestResult, TestResultFile, TestTimeSeries, PTComparison,
    OperationLog
)
from werkzeug.security import generate_password_hash
import numpy as np
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_sample_users():
    """Create sample users for testing"""
    users = [
        {
            'username': 'engineer1',
            'email': 'engineer1@mgg.com',
            'password_hash': generate_password_hash('password123'),
            'full_name': 'John Engineer',
            'role': 'engineer',
            'department': 'R&D',
            'is_active': True
        },
        {
            'username': 'user1',
            'email': 'user1@mgg.com',
            'password_hash': generate_password_hash('password123'),
            'full_name': 'Jane User',
            'role': 'user',
            'department': 'Testing',
            'is_active': True
        },
    ]

    try:
        with get_db_session() as session:
            for user_data in users:
                # Check if user exists
                existing = session.query(User).filter_by(username=user_data['username']).first()
                if not existing:
                    user = User(**user_data)
                    session.add(user)
        logger.info(f"✓ Created {len(users)} sample users")
        return True
    except Exception as e:
        logger.error(f"✗ Failed to create sample users: {str(e)}")
        return False


def create_sample_work_orders():
    """Create sample work orders"""
    with get_db_session() as session:
        # Get admin user
        admin = session.query(User).filter_by(username='admin').first()
        if not admin:
            logger.error("✗ Admin user not found")
            return False

        work_orders = [
            {
                'work_order_number': f'WO-{datetime.now().strftime("%Y%m%d")}-001',
                'created_by': admin.id,
                'status': 'completed',
                'priority': 'normal',
                'description': 'Sample forward simulation work order',
                'created_at': datetime.now() - timedelta(days=5),
                'completed_at': datetime.now() - timedelta(days=2)
            },
            {
                'work_order_number': f'WO-{datetime.now().strftime("%Y%m%d")}-002',
                'created_by': admin.id,
                'status': 'in_progress',
                'priority': 'high',
                'description': 'Test comparison work order',
                'created_at': datetime.now() - timedelta(days=3)
            },
        ]

        try:
            for wo_data in work_orders:
                # Check if exists
                existing = session.query(WorkOrder).filter_by(
                    work_order_number=wo_data['work_order_number']
                ).first()
                if not existing:
                    wo = WorkOrder(**wo_data)
                    session.add(wo)
            logger.info(f"✓ Created {len(work_orders)} sample work orders")
            return True
        except Exception as e:
            logger.error(f"✗ Failed to create work orders: {str(e)}")
            return False


def create_sample_forward_simulation():
    """Create a sample forward simulation with time series data"""
    with get_db_session() as session:
        admin = session.query(User).filter_by(username='admin').first()
        work_order = session.query(WorkOrder).first()

        if not admin or not work_order:
            logger.error("✗ Admin or work order not found")
            return False

        # Create simulation
        simulation = ForwardSimulation(
            work_order_id=work_order.id,
            user_id=admin.id,
            shell_height=100.0,
            current_condition=25.0,
            igniter_type_id=1,
            nc_type_id=1,
            nc_amount=50.0,
            gp_type_id=1,
            gp_amount=20.0,
            model_version='v1.0',
            num_models=67,
            r_squared=0.9856,
            peak_pressure=8.45,
            peak_time=12.34,
            num_data_points=100,
            status='completed',
            execution_time=2.5,
            created_at=datetime.now() - timedelta(days=3)
        )
        session.add(simulation)
        session.flush()

        # Generate sample PT curve data
        time_points = np.linspace(0, 50, 100)
        pressures = 8.45 * np.exp(-((time_points - 12.34)**2) / (2 * 5**2))

        for i, (t, p) in enumerate(zip(time_points, pressures)):
            ts = SimulationTimeSeries(
                simulation_id=simulation.id,
                time_point=float(t),
                pressure=float(p),
                sequence_number=i
            )
            session.add(ts)

        session.commit()
        logger.info("✓ Created sample forward simulation with time series data")
        return True


def create_sample_test_result():
    """Create a sample test result with time series data"""
    with get_db_session() as session:
        admin = session.query(User).filter_by(username='admin').first()
        work_order = session.query(WorkOrder).first()

        if not admin or not work_order:
            logger.error("✗ Admin or work order not found")
            return False

        # Create test result
        test_result = TestResult(
            work_order_id=work_order.id,
            user_id=admin.id,
            tester_id='TEST001',
            test_device_id=1,
            test_date=datetime.now().date() - timedelta(days=2),
            notes='Sample test result for demonstration',
            status='validated',
            created_at=datetime.now() - timedelta(days=2)
        )
        session.add(test_result)
        session.flush()

        # Add test file reference
        test_file = TestResultFile(
            test_result_id=test_result.id,
            file_name='sample_test_data.xlsx',
            file_path='/uploads/sample_test_data.xlsx',
            file_size=45678,
            file_type='xlsx'
        )
        session.add(test_file)
        session.flush()

        # Generate sample PT curve data (similar to simulation but with noise)
        time_points = np.linspace(0, 50, 100)
        pressures = 8.45 * np.exp(-((time_points - 12.34)**2) / (2 * 5**2))
        pressures += np.random.normal(0, 0.1, len(pressures))  # Add noise

        for i, (t, p) in enumerate(zip(time_points, pressures)):
            ts = TestTimeSeries(
                test_result_id=test_result.id,
                file_id=test_file.id,
                time_point=float(t),
                pressure=float(max(0, p)),  # No negative pressure
                sequence_number=i
            )
            session.add(ts)

        session.commit()
        logger.info("✓ Created sample test result with time series data")
        return True


def create_sample_comparison():
    """Create a sample PT comparison"""
    with get_db_session() as session:
        admin = session.query(User).filter_by(username='admin').first()
        simulation = session.query(ForwardSimulation).first()
        test_result = session.query(TestResult).first()

        if not all([admin, simulation, test_result]):
            logger.error("✗ Required data not found for comparison")
            return False

        comparison = PTComparison(
            user_id=admin.id,
            simulation_id=simulation.id,
            test_result_id=test_result.id,
            peak_pressure_diff=0.15,
            peak_time_diff=0.25,
            rmse=0.234,
            correlation=0.9823,
            notes='Sample PT curve comparison',
            created_at=datetime.now() - timedelta(days=1)
        )
        session.add(comparison)
        logger.info("✓ Created sample PT comparison")
        return True


def create_sample_operation_logs():
    """Create sample operation logs"""
    with get_db_session() as session:
        admin = session.query(User).filter_by(username='admin').first()

        if not admin:
            logger.error("✗ Admin user not found")
            return False

        logs = [
            {
                'user_id': admin.id,
                'log_type': 'login',
                'action': 'User login',
                'details': 'Successful login from web interface',
                'ip_address': '127.0.0.1',
                'created_at': datetime.now() - timedelta(days=5)
            },
            {
                'user_id': admin.id,
                'log_type': 'simulation',
                'action': 'Forward simulation',
                'details': 'NC50 50mg simulation completed',
                'ip_address': '127.0.0.1',
                'created_at': datetime.now() - timedelta(days=3)
            },
            {
                'user_id': admin.id,
                'log_type': 'upload',
                'action': 'Test data upload',
                'details': 'Uploaded test_data.xlsx',
                'ip_address': '127.0.0.1',
                'created_at': datetime.now() - timedelta(days=2)
            },
            {
                'user_id': admin.id,
                'log_type': 'comparison',
                'action': 'PT curve comparison',
                'details': 'Compared simulation vs test data',
                'ip_address': '127.0.0.1',
                'created_at': datetime.now() - timedelta(days=1)
            },
        ]

        try:
            for log_data in logs:
                log = OperationLog(**log_data)
                session.add(log)
            logger.info(f"✓ Created {len(logs)} sample operation logs")
            return True
        except Exception as e:
            logger.error(f"✗ Failed to create operation logs: {str(e)}")
            return False


def seed_all_sample_data():
    """Seed all sample data"""
    logger.info("=" * 60)
    logger.info("Seeding Sample Data")
    logger.info("=" * 60)

    success = True
    success &= create_sample_users()
    success &= create_sample_work_orders()
    success &= create_sample_forward_simulation()
    success &= create_sample_test_result()
    success &= create_sample_comparison()
    success &= create_sample_operation_logs()

    if success:
        logger.info("\n" + "=" * 60)
        logger.info("✓ Sample data seeding completed successfully!")
        logger.info("=" * 60)
    else:
        logger.error("\n" + "=" * 60)
        logger.error("✗ Sample data seeding completed with errors")
        logger.error("=" * 60)

    return success


if __name__ == "__main__":
    seed_all_sample_data()
