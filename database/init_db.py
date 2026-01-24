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
    User, IgniterType, NCType, GPType, TestDevice,
    RetentionPolicy, ModelVersion
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
        {'type_code': 'IG-001', 'description': 'Standard Igniter Type 1'},
        {'type_code': 'IG-002', 'description': 'Standard Igniter Type 2'},
        {'type_code': 'IG-003', 'description': 'High Performance Igniter'},
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


def seed_nc_types():
    """Seed NC types"""
    nc_types = [
        {
            'type_code': 'NC-50',
            'description': 'NC50 Standard Grade',
            'density': 1.50,
            'specific_heat': 1.20
        },
        {
            'type_code': 'NC-60',
            'description': 'NC60 High Performance',
            'density': 1.52,
            'specific_heat': 1.22
        },
        {
            'type_code': 'NC-70',
            'description': 'NC70 Premium Grade',
            'density': 1.54,
            'specific_heat': 1.24
        },
    ]

    try:
        with get_db_session() as session:
            for nc_data in nc_types:
                nc = NCType(**nc_data)
                session.add(nc)
        logger.info(f"✓ Seeded {len(nc_types)} NC types")
        return True
    except Exception as e:
        logger.error(f"✗ Failed to seed NC types: {str(e)}")
        return False


def seed_gp_types():
    """Seed GP types"""
    gp_types = [
        {
            'type_code': 'GP-A',
            'description': 'GP Type A Standard',
            'density': 1.30,
            'specific_heat': 1.10
        },
        {
            'type_code': 'GP-B',
            'description': 'GP Type B Enhanced',
            'density': 1.32,
            'specific_heat': 1.12
        },
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


def seed_test_devices():
    """Seed test devices"""
    test_devices = [
        {
            'device_code': 'TD-001',
            'device_name': 'Pressure Test Chamber 1',
            'location': 'Lab Building A, Room 101',
            'calibration_date': datetime(2024, 1, 15).date()
        },
        {
            'device_code': 'TD-002',
            'device_name': 'Pressure Test Chamber 2',
            'location': 'Lab Building A, Room 102',
            'calibration_date': datetime(2024, 1, 20).date()
        },
        {
            'device_code': 'TD-003',
            'device_name': 'High Precision Chamber',
            'location': 'Lab Building B, Room 201',
            'calibration_date': datetime(2024, 2, 1).date()
        },
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
    success &= seed_nc_types()
    success &= seed_gp_types()
    success &= seed_test_devices()
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
