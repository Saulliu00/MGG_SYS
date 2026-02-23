"""Database initialization, migrations, and seeding."""
import sqlite3
from sqlalchemy import text
from database.extensions import db


def init_database(app):
    """
    Initialize the database within an app context.

    Creates all tables, enables WAL mode, runs migrations,
    and seeds the default admin user.
    """
    with app.app_context():
        db.create_all()
        _enable_wal_mode(app)
        _run_migrations(app)
        _seed_admin(app)


def _enable_wal_mode(app):
    """Enable SQLite WAL mode for concurrent read/write performance."""
    try:
        db.session.execute(text('PRAGMA journal_mode=WAL'))
        db.session.commit()
    except Exception as e:
        app.logger.warning(f'Failed to enable WAL mode: {str(e)}')


def _run_migrations(app):
    """Run manual SQLite migrations for columns that create_all() won't add."""
    db_uri = app.config['SQLALCHEMY_DATABASE_URI']
    if not db_uri.startswith('sqlite:///'):
        return
    db_path = db_uri.replace('sqlite:///', '')
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(simulation)")
        columns = [col[1] for col in cursor.fetchall()]
        if 'work_order_id' not in columns:
            cursor.execute(
                "ALTER TABLE simulation ADD COLUMN work_order_id INTEGER REFERENCES work_order(id)"
            )
            conn.commit()
            app.logger.info('Migration: Added work_order_id to simulation table')

        cursor.execute('PRAGMA table_info("user")')
        user_cols = [col[1] for col in cursor.fetchall()]
        if 'last_seen_at' not in user_cols:
            cursor.execute('ALTER TABLE "user" ADD COLUMN last_seen_at DATETIME')
            conn.commit()
            app.logger.info('Migration: Added last_seen_at to user table')
        if 'session_token' not in user_cols:
            cursor.execute('ALTER TABLE "user" ADD COLUMN session_token VARCHAR(36)')
            conn.commit()
            app.logger.info('Migration: Added session_token to user table')

        conn.close()
    except Exception as e:
        app.logger.warning(f'Migration check failed: {str(e)}')


def _seed_admin(app):
    """Create default admin user if not exists."""
    from database.models import User
    admin_user = User.query.filter_by(employee_id='admin').first()
    if not admin_user:
        admin_user = User(
            username='admin',
            employee_id='admin',
            role='admin'
        )
        admin_user.set_password('admin123')
        db.session.add(admin_user)
        db.session.commit()
