"""
Database initialization, migrations, and seeding.
Handles both SQLite (development) and PostgreSQL (production).
"""
import sqlite3
import os
from sqlalchemy import text
from database.extensions import db


def init_database(app):
    """
    Initialize the database within an app context.
    
    Steps:
    1. Create all tables (from models.py)
    2. Enable WAL mode (SQLite only, for concurrency)
    3. Run any manual migrations
    4. Seed default admin user
    
    Args:
        app: Flask application instance
    """
    with app.app_context():
        # Create all tables
        db.create_all()
        app.logger.info('✓ Database tables created')
        
        # SQLite-specific optimizations
        if app.config['SQLALCHEMY_DATABASE_URI'].startswith('sqlite:///'):
            _enable_wal_mode(app)
            _run_sqlite_migrations(app)
        
        # Seed default data
        _seed_admin(app)
        _seed_example_recipes(app)


def _enable_wal_mode(app):
    """
    Enable SQLite WAL (Write-Ahead Logging) mode for better concurrency.
    
    WAL mode allows multiple readers while one writer is active.
    This is critical for web applications with concurrent requests.
    
    Fallback: If WAL fails (e.g., network filesystem), keep default journal mode.
    """
    try:
        db.session.execute(text('PRAGMA journal_mode=WAL'))
        db.session.commit()
        app.logger.info('✓ SQLite WAL mode enabled')
    except Exception as e:
        app.logger.warning(f'⚠ Failed to enable WAL mode: {str(e)}')
        app.logger.warning('  Continuing with default journal mode')


def _run_sqlite_migrations(app):
    """
    Run manual SQLite migrations for schema changes.
    
    SQLite has limited ALTER TABLE support, so we handle migrations manually.
    This function checks for missing columns and adds them if needed.
    
    Note: For PostgreSQL, use Alembic instead.
    """
    db_uri = app.config['SQLALCHEMY_DATABASE_URI']
    if not db_uri.startswith('sqlite:///'):
        return
        
    db_path = db_uri.replace('sqlite:///', '')
    if not os.path.exists(db_path):
        app.logger.info('✓ New database, no migrations needed')
        return
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Migration 1: Add email to user table (if doesn't exist)
        cursor.execute("PRAGMA table_info(user)")
        user_cols = [col[1] for col in cursor.fetchall()]
        
        if 'email' not in user_cols:
            cursor.execute('ALTER TABLE "user" ADD COLUMN email VARCHAR(120)')
            conn.commit()
            app.logger.info('✓ Migration: Added email to user table')
        
        if 'department' not in user_cols:
            cursor.execute('ALTER TABLE "user" ADD COLUMN department VARCHAR(50)')
            conn.commit()
            app.logger.info('✓ Migration: Added department to user table')
        
        # Migration 2: Add recipe_name to recipe table
        cursor.execute("PRAGMA table_info(recipe)")
        recipe_cols = [col[1] for col in cursor.fetchall()]
        
        if 'recipe_name' not in recipe_cols:
            cursor.execute('ALTER TABLE recipe ADD COLUMN recipe_name VARCHAR(200)')
            cursor.execute('ALTER TABLE recipe ADD COLUMN description TEXT')
            cursor.execute('ALTER TABLE recipe ADD COLUMN updated_at DATETIME DEFAULT CURRENT_TIMESTAMP')
            conn.commit()
            app.logger.info('✓ Migration: Added recipe metadata columns')
        
        # Migration 3: Add work_order status tracking
        cursor.execute("PRAGMA table_info(work_order)")
        wo_cols = [col[1] for col in cursor.fetchall()]
        
        if 'status' not in wo_cols:
            cursor.execute('ALTER TABLE work_order ADD COLUMN status VARCHAR(20) DEFAULT "pending"')
            cursor.execute('ALTER TABLE work_order ADD COLUMN priority VARCHAR(10) DEFAULT "normal"')
            cursor.execute('ALTER TABLE work_order ADD COLUMN completed_at DATETIME')
            conn.commit()
            app.logger.info('✓ Migration: Added work_order status tracking')
        
        # Migration 4: Add simulation results summary
        cursor.execute("PRAGMA table_info(simulation)")
        sim_cols = [col[1] for col in cursor.fetchall()]
        
        if 'peak_pressure' not in sim_cols:
            cursor.execute('ALTER TABLE simulation ADD COLUMN peak_pressure FLOAT')
            cursor.execute('ALTER TABLE simulation ADD COLUMN peak_time FLOAT')
            cursor.execute('ALTER TABLE simulation ADD COLUMN num_data_points INTEGER')
            cursor.execute('ALTER TABLE simulation ADD COLUMN r_squared FLOAT')
            conn.commit()
            app.logger.info('✓ Migration: Added simulation summary columns')
        
        conn.close()
        app.logger.info('✓ All migrations complete')
        
    except Exception as e:
        app.logger.error(f'✗ Migration failed: {str(e)}')
        # Don't crash - migrations are optional for existing DBs


def _seed_admin(app):
    """
    Create default admin user if not exists.
    
    Default credentials:
        employee_id: admin
        password: admin123
    
    ⚠️ IMPORTANT: Change this password in production!
    """
    from database.models import User
    
    admin_user = User.query.filter_by(employee_id='admin').first()
    if not admin_user:
        admin_user = User(
            username='Administrator',
            employee_id='admin',
            email='admin@example.com',
            role='admin',
            department='IT'
        )
        admin_user.set_password('admin123')
        db.session.add(admin_user)
        db.session.commit()
        app.logger.info('✓ Created default admin user (admin/admin123)')
    else:
        app.logger.info('✓ Admin user already exists')


def _seed_example_recipes(app):
    """
    Seed a few example recipes for new deployments.
    Only runs if no recipes exist yet.
    """
    from database.models import Recipe, User
    
    # Check if any recipes exist
    if Recipe.query.first():
        app.logger.info('✓ Recipes already exist, skipping seed')
        return
    
    # Get admin user for recipe creator
    admin = User.query.filter_by(employee_id='admin').first()
    if not admin:
        app.logger.warning('⚠ Admin user not found, skipping recipe seed')
        return
    
    # Example recipes (you can customize these)
    example_recipes = [
        {
            'recipe_name': 'Standard Test Configuration',
            'description': 'Default parameter set for baseline testing',
            'ignition_model': 'Type-A',
            'nc_type_1': 'NC-Standard',
            'nc_usage_1': 20.0,
            'nc_type_2': 'NC-Enhanced',
            'nc_usage_2': 10.0,
            'gp_type': 'GP-Alpha',
            'gp_usage': 15.0,
            'shell_model': 'Shell-100mm',
            'current_condition': '5A',
            'sensor_range': '0-10MPa',
            'body_model': '50cc',
            'equipment': 'Tester-01'
        },
        {
            'recipe_name': 'High Pressure Configuration',
            'description': 'For high-pressure testing scenarios',
            'ignition_model': 'Type-B',
            'nc_type_1': 'NC-Enhanced',
            'nc_usage_1': 30.0,
            'nc_type_2': None,
            'nc_usage_2': None,
            'gp_type': 'GP-Beta',
            'gp_usage': 25.0,
            'shell_model': 'Shell-150mm',
            'current_condition': '7A',
            'sensor_range': '0-20MPa',
            'body_model': '100cc',
            'equipment': 'Tester-02'
        }
    ]
    
    try:
        for recipe_data in example_recipes:
            recipe = Recipe(user_id=admin.id, **recipe_data)
            db.session.add(recipe)
        
        db.session.commit()
        app.logger.info(f'✓ Seeded {len(example_recipes)} example recipes')
    except Exception as e:
        app.logger.warning(f'⚠ Failed to seed example recipes: {str(e)}')
        db.session.rollback()


def reset_database(app):
    """
    ⚠️ DANGEROUS: Drop all tables and recreate from scratch.
    
    This will DELETE ALL DATA. Use only for:
    - Development/testing environments
    - Fresh installations
    - When explicitly requested by admin
    
    Args:
        app: Flask application instance
    """
    with app.app_context():
        app.logger.warning('⚠ DROPPING ALL TABLES')
        db.drop_all()
        app.logger.info('✓ All tables dropped')
        
        init_database(app)
        app.logger.info('✓ Database reset complete')


def backup_database(app, backup_path=None):
    """
    Create a backup of the SQLite database.
    
    For PostgreSQL, use pg_dump instead.
    
    Args:
        app: Flask application instance
        backup_path: Optional custom backup path (defaults to ./backups/)
    
    Returns:
        str: Path to backup file
    """
    import shutil
    from datetime import datetime
    
    db_uri = app.config['SQLALCHEMY_DATABASE_URI']
    if not db_uri.startswith('sqlite:///'):
        raise ValueError('Backup function only works with SQLite. Use pg_dump for PostgreSQL.')
    
    db_path = db_uri.replace('sqlite:///', '')
    if not os.path.exists(db_path):
        raise FileNotFoundError(f'Database file not found: {db_path}')
    
    # Create backups directory
    if backup_path is None:
        backup_dir = os.path.join(os.path.dirname(db_path), 'backups')
    else:
        backup_dir = backup_path
    
    os.makedirs(backup_dir, exist_ok=True)
    
    # Generate backup filename with timestamp
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_filename = f'mgg_backup_{timestamp}.db'
    backup_fullpath = os.path.join(backup_dir, backup_filename)
    
    # Copy database file
    shutil.copy2(db_path, backup_fullpath)
    app.logger.info(f'✓ Database backed up to: {backup_fullpath}')
    
    return backup_fullpath
