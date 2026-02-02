"""
Database Initialization Script
Creates all tables and seeds initial data
"""

import sys
from datetime import datetime
from sqlalchemy import text
import logging

from db_config import DatabaseManager, get_db_session
from models import (
    User, IgniterType, NCType1, NCType2, GPType, ShellType,
    CurrentType, SensorType, VolumeType, TestDevice,
    Employee, Ticket, RetentionPolicy, ModelVersion
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_tables():
    """Create all database tables"""
    try:
        db_manager = DatabaseManager()
        db_manager.create_all_tables()
        logger.info("✓ All tables created successfully")
        return True
    except Exception as e:
        logger.error(f"✗ Failed to create tables: {str(e)}")
        return False


def seed_igniter_types():
    """Seed igniter types"""
    igniter_types = [
        {'type_code': '115', 'description': 'Igniter Model 115'},
        {'type_code': '116', 'description': 'Igniter Model 116'},
        {'type_code': '117', 'description': 'Igniter Model 117'},
    ]

    try:
        with get_db_session() as session:
            for ig_data in igniter_types:
                igniter = IgniterType(**ig_data)
                session.add(igniter)
        logger.info(f"✓ Seeded {len(igniter_types)} igniter types")
        return True
    except Exception as e:
        logger.error(f"✗ Failed to seed igniter types: {str(e)}")
        return False


def seed_nc_types1():
    """Seed NC Type 1"""
    nc_types = [
        {'type_code': 'D', 'description': 'NC Type D', 'density': 1.50, 'specific_heat': 1.20},
        {'type_code': 'E', 'description': 'NC Type E', 'density': 1.52, 'specific_heat': 1.22},
        {'type_code': 'F', 'description': 'NC Type F', 'density': 1.54, 'specific_heat': 1.24},
    ]

    try:
        with get_db_session() as session:
            for nc_data in nc_types:
                nc = NCType1(**nc_data)
                session.add(nc)
        logger.info(f"✓ Seeded {len(nc_types)} NC Type 1 entries")
        return True
    except Exception as e:
        logger.error(f"✗ Failed to seed NC Type 1: {str(e)}")
        return False


def seed_nc_types2():
    """Seed NC Type 2"""
    nc_types = [
        {'type_code': '无', 'description': 'None', 'density': 0, 'specific_heat': 0},
        {'type_code': 'D', 'description': 'NC Type D', 'density': 1.50, 'specific_heat': 1.20},
        {'type_code': 'E', 'description': 'NC Type E', 'density': 1.52, 'specific_heat': 1.22},
        {'type_code': 'F', 'description': 'NC Type F', 'density': 1.54, 'specific_heat': 1.24},
    ]

    try:
        with get_db_session() as session:
            for nc_data in nc_types:
                nc = NCType2(**nc_data)
                session.add(nc)
        logger.info(f"✓ Seeded {len(nc_types)} NC Type 2 entries")
        return True
    except Exception as e:
        logger.error(f"✗ Failed to seed NC Type 2: {str(e)}")
        return False


def seed_gp_types():
    """Seed GP types"""
    gp_types = [
        {'type_code': 'A', 'description': 'GP Type A', 'density': 1.30, 'specific_heat': 1.10},
        {'type_code': 'B', 'description': 'GP Type B', 'density': 1.32, 'specific_heat': 1.12},
        {'type_code': 'C', 'description': 'GP Type C', 'density': 1.34, 'specific_heat': 1.14},
    ]

    try:
        with get_db_session() as session:
            for gp_data in gp_types:
                gp = GPType(**gp_data)
                session.add(gp)
        logger.info(f"✓ Seeded {len(gp_types)} GP types")
        return True
    except Exception as e:
        logger.error(f"✗ Failed to seed GP types: {str(e)}")
        return False


def seed_shell_types():
    """Seed shell types"""
    shell_types = [
        {'type_code': '18', 'description': 'Shell Model 18'},
        {'type_code': '19', 'description': 'Shell Model 19'},
        {'type_code': '20', 'description': 'Shell Model 20'},
    ]

    try:
        with get_db_session() as session:
            for shell_data in shell_types:
                shell = ShellType(**shell_data)
                session.add(shell)
        logger.info(f"✓ Seeded {len(shell_types)} shell types")
        return True
    except Exception as e:
        logger.error(f"✗ Failed to seed shell types: {str(e)}")
        return False


def seed_current_types():
    """Seed current types"""
    current_types = [
        {'type_code': '1.2', 'current_value': 1.2, 'description': '1.2A Current'},
        {'type_code': '1.5', 'current_value': 1.5, 'description': '1.5A Current'},
        {'type_code': '2.0', 'current_value': 2.0, 'description': '2.0A Current'},
    ]

    try:
        with get_db_session() as session:
            for current_data in current_types:
                current = CurrentType(**current_data)
                session.add(current)
        logger.info(f"✓ Seeded {len(current_types)} current types")
        return True
    except Exception as e:
        logger.error(f"✗ Failed to seed current types: {str(e)}")
        return False


def seed_sensor_types():
    """Seed sensor types"""
    sensor_types = [
        {'type_code': '30', 'description': 'Sensor Model 30'},
        {'type_code': '31', 'description': 'Sensor Model 31'},
        {'type_code': '32', 'description': 'Sensor Model 32'},
    ]

    try:
        with get_db_session() as session:
            for sensor_data in sensor_types:
                sensor = SensorType(**sensor_data)
                session.add(sensor)
        logger.info(f"✓ Seeded {len(sensor_types)} sensor types")
        return True
    except Exception as e:
        logger.error(f"✗ Failed to seed sensor types: {str(e)}")
        return False


def seed_volume_types():
    """Seed volume types"""
    volume_types = [
        {'type_code': '3.5', 'volume_value': 3.5, 'description': '3.5 Volume'},
        {'type_code': '4.0', 'volume_value': 4.0, 'description': '4.0 Volume'},
        {'type_code': '4.5', 'volume_value': 4.5, 'description': '4.5 Volume'},
    ]

    try:
        with get_db_session() as session:
            for volume_data in volume_types:
                volume = VolumeType(**volume_data)
                session.add(volume)
        logger.info(f"✓ Seeded {len(volume_types)} volume types")
        return True
    except Exception as e:
        logger.error(f"✗ Failed to seed volume types: {str(e)}")
        return False


def seed_test_devices():
    """Seed test devices"""
    test_devices = [
        {'device_code': 'A', 'device_name': 'Test Device A', 'location': 'Lab A'},
        {'device_code': 'B', 'device_name': 'Test Device B', 'location': 'Lab B'},
        {'device_code': 'C', 'device_name': 'Test Device C', 'location': 'Lab C'},
    ]

    try:
        with get_db_session() as session:
            for device_data in test_devices:
                device = TestDevice(**device_data)
                session.add(device)
        logger.info(f"✓ Seeded {len(test_devices)} test devices")
        return True
    except Exception as e:
        logger.error(f"✗ Failed to seed test devices: {str(e)}")
        return False


def seed_employees():
    """Seed sample employees"""
    employees = [
        {
            'employee_id': 'EMP001',
            'full_name': 'Zhang Wei',
            'department': 'Testing',
            'position': 'Test Engineer',
            'email': 'zhang.wei@mgg.com',
            'phone': '13800138001'
        },
        {
            'employee_id': 'EMP002',
            'full_name': 'Li Ming',
            'department': 'Testing',
            'position': 'Senior Test Engineer',
            'email': 'li.ming@mgg.com',
            'phone': '13800138002'
        },
        {
            'employee_id': 'EMP003',
            'full_name': 'Wang Fang',
            'department': 'R&D',
            'position': 'Research Engineer',
            'email': 'wang.fang@mgg.com',
            'phone': '13800138003'
        },
    ]

    try:
        with get_db_session() as session:
            for emp_data in employees:
                employee = Employee(**emp_data)
                session.add(employee)
        logger.info(f"✓ Seeded {len(employees)} employees")
        return True
    except Exception as e:
        logger.error(f"✗ Failed to seed employees: {str(e)}")
        return False


def create_admin_user():
    """Create default admin user"""
    from werkzeug.security import generate_password_hash

    admin_data = {
        'username': 'admin',
        'email': 'admin@mgg.com',
        'password_hash': generate_password_hash('admin123'),  # Change in production!
        'full_name': 'System Administrator',
        'role': 'admin',
        'department': 'IT',
        'is_active': True
    }

    try:
        with get_db_session() as session:
            # Check if admin already exists
            existing = session.query(User).filter_by(username='admin').first()
            if existing:
                logger.info("✓ Admin user already exists")
                return True

            admin = User(**admin_data)
            session.add(admin)
        logger.info("✓ Created admin user (username: admin, password: admin123)")
        logger.warning("⚠️  IMPORTANT: Change the admin password in production!")
        return True
    except Exception as e:
        logger.error(f"✗ Failed to create admin user: {str(e)}")
        return False


def seed_retention_policies():
    """Seed retention policies"""
    policies = [
        {
            'table_name': 'operation_logs',
            'retention_days': 90,
            'archive_enabled': True,
            'delete_after_archive': True
        },
        {
            'table_name': 'simulation_time_series',
            'retention_days': 180,
            'archive_enabled': True,
            'delete_after_archive': True
        },
        {
            'table_name': 'test_time_series',
            'retention_days': 365,
            'archive_enabled': True,
            'delete_after_archive': True
        },
        {
            'table_name': 'forward_simulations',
            'retention_days': 365,
            'archive_enabled': False,
            'delete_after_archive': False
        },
        {
            'table_name': 'reverse_simulations',
            'retention_days': 365,
            'archive_enabled': False,
            'delete_after_archive': False
        },
        {
            'table_name': 'test_results',
            'retention_days': 730,
            'archive_enabled': False,
            'delete_after_archive': False
        },
    ]

    try:
        with get_db_session() as session:
            for policy_data in policies:
                policy = RetentionPolicy(**policy_data)
                session.add(policy)
        logger.info(f"✓ Seeded {len(policies)} retention policies")
        return True
    except Exception as e:
        logger.error(f"✗ Failed to seed retention policies: {str(e)}")
        return False


def initialize_database(drop_existing=False):
    """
    Initialize the database with tables and seed data

    Args:
        drop_existing: If True, drop all existing tables first (USE WITH CAUTION!)
    """
    logger.info("=" * 60)
    logger.info("MGG Simulation System - Database Initialization")
    logger.info("=" * 60)

    db_manager = DatabaseManager()

    # Test connection first
    logger.info("\n1. Testing database connection...")
    if not db_manager.test_connection():
        logger.error("✗ Database connection failed. Please check your configuration.")
        return False

    # Drop tables if requested
    if drop_existing:
        logger.warning("\n2. Dropping existing tables...")
        response = input("⚠️  Are you sure you want to drop all tables? (yes/no): ")
        if response.lower() == 'yes':
            db_manager.drop_all_tables()
            logger.info("✓ All tables dropped")
        else:
            logger.info("✓ Skipped dropping tables")

    # Create tables
    logger.info("\n3. Creating database tables...")
    if not create_tables():
        return False

    # Seed data
    logger.info("\n4. Seeding initial data...")

    success = True
    success &= seed_igniter_types()
    success &= seed_nc_types1()
    success &= seed_nc_types2()
    success &= seed_gp_types()
    success &= seed_shell_types()
    success &= seed_current_types()
    success &= seed_sensor_types()
    success &= seed_volume_types()
    success &= seed_test_devices()
    success &= seed_employees()
    success &= seed_retention_policies()
    success &= create_admin_user()

    if success:
        logger.info("\n" + "=" * 60)
        logger.info("✓ Database initialization completed successfully!")
        logger.info("=" * 60)
        logger.info("\nDefault Admin Credentials:")
        logger.info("  Username: admin")
        logger.info("  Password: admin123")
        logger.info("\n⚠️  IMPORTANT: Change the admin password immediately!")
        logger.info("=" * 60)
    else:
        logger.error("\n" + "=" * 60)
        logger.error("✗ Database initialization completed with errors")
        logger.error("=" * 60)

    return success


def reset_database():
    """Reset database - drop all tables and recreate"""
    return initialize_database(drop_existing=True)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Initialize MGG database')
    parser.add_argument('--reset', action='store_true',
                       help='Reset database (drop and recreate all tables)')
    parser.add_argument('--drop', action='store_true',
                       help='Drop all tables only')

    args = parser.parse_args()

    if args.drop:
        logger.warning("Dropping all tables...")
        response = input("⚠️  Are you sure? (yes/no): ")
        if response.lower() == 'yes':
            db_manager = DatabaseManager()
            db_manager.drop_all_tables()
            logger.info("✓ All tables dropped")
    elif args.reset:
        reset_database()
    else:
        initialize_database(drop_existing=False)
