from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_bcrypt import Bcrypt
from flask_cors import CORS
from flask_wtf.csrf import CSRFProtect
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import os
import secrets
import sqlite3
from datetime import datetime
from flask_login import current_user
from app.config.network_config import (
    CORS_CONFIG,
    SESSION_CONFIG,
    REQUEST_LIMITS,
    TIMEOUTS,
    NETWORK_LOGGING
)
from app.utils import LogoGenerator
from app.middleware import init_timeout_middleware, init_logging_middleware

db = SQLAlchemy()
login_manager = LoginManager()
bcrypt = Bcrypt()
csrf = CSRFProtect()
limiter = Limiter(key_func=get_remote_address)

def create_app():
    app = Flask(__name__, instance_relative_config=True)

    # Ensure the instance folder exists
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass

    # Configuration
    secret_key = os.environ.get('SECRET_KEY')
    if not secret_key:
        raise RuntimeError(
            'SECRET_KEY environment variable is not set. '
            'Set it before starting the application: export SECRET_KEY=$(python -c "import secrets; print(secrets.token_hex(32))")'
        )
    app.config['SECRET_KEY'] = secret_key
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL') or \
        'sqlite:///' + os.path.join(app.instance_path, 'simulation_system.db')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
        'pool_size': 25,       # Permanent connections — sized above gunicorn worker threads (~36 on 4-core)
        'max_overflow': 25,    # Burst headroom → 50 total max, handles 100 concurrent users
        'pool_timeout': 10,    # Fail fast (10s) instead of the 30s default that caused stalls
        'pool_recycle': 3600,  # Recycle idle connections every hour
        'pool_pre_ping': True, # Discard stale connections before use
    }
    app.config['UPLOAD_FOLDER'] = os.path.join(app.root_path, 'static', 'uploads')

    # Network configuration from network_config.py
    app.config['MAX_CONTENT_LENGTH'] = REQUEST_LIMITS['max_content_length']
    app.config['MAX_FORM_MEMORY_SIZE'] = REQUEST_LIMITS['max_form_memory_size']

    # Session configuration for multi-user access
    app.config['SESSION_COOKIE_SECURE'] = SESSION_CONFIG['session_cookie_secure']
    app.config['SESSION_COOKIE_HTTPONLY'] = SESSION_CONFIG['session_cookie_httponly']
    app.config['SESSION_COOKIE_SAMESITE'] = SESSION_CONFIG['session_cookie_samesite']
    app.config['PERMANENT_SESSION_LIFETIME'] = SESSION_CONFIG['permanent_session_lifetime']

    # Request timeouts and network logging
    app.config['TIMEOUTS'] = TIMEOUTS
    app.config['NETWORK_LOGGING'] = NETWORK_LOGGING

    # Initialize extensions
    db.init_app(app)
    login_manager.init_app(app)
    bcrypt.init_app(app)
    csrf.init_app(app)
    limiter.init_app(app)

    # Configure CORS for local network access
    CORS(app,
         origins=CORS_CONFIG['origins'],
         methods=CORS_CONFIG['methods'],
         allow_headers=CORS_CONFIG['allow_headers'],
         expose_headers=CORS_CONFIG['expose_headers'],
         supports_credentials=CORS_CONFIG['supports_credentials'],
         max_age=CORS_CONFIG['max_age'])

    # Login settings
    login_manager.login_view = 'auth.login'
    login_manager.login_message = '请先登录以访问此页面'

    # Initialize services and attach to app
    from app.services import SimulationService, FileService, ComparisonService, WorkOrderService
    app.simulation_service = SimulationService(db)
    app.file_service = FileService(db)
    app.comparison_service = ComparisonService()
    app.work_order_service = WorkOrderService(db)

    # Generate system logos if they don't exist
    try:
        logo_paths = LogoGenerator.ensure_logos_exist()
        app.config['LOGO_PATH'] = logo_paths['logo']
        app.config['FAVICON_PATH'] = logo_paths['favicon']
    except Exception as e:
        app.logger.warning(f'Failed to generate logos: {str(e)}')

    # Initialize timeout middleware for request handling
    init_timeout_middleware(app)

    # Initialize logging middleware for system logging
    init_logging_middleware(app)

    # Update last_seen_at for authenticated users (throttled to once per minute)
    @app.before_request
    def update_last_seen():
        if current_user.is_authenticated:
            now = datetime.utcnow()
            if (current_user.last_seen_at is None or
                    (now - current_user.last_seen_at).total_seconds() > 60):
                current_user.last_seen_at = now
                db.session.commit()

    # Register blueprints
    from app.routes import auth, main, admin, simulation
    from app.routes import work_order

    app.register_blueprint(auth.bp)
    app.register_blueprint(main.bp)
    app.register_blueprint(admin.bp)
    app.register_blueprint(simulation.bp)
    app.register_blueprint(work_order.wp)

    # Create database tables
    with app.app_context():
        db.create_all()

        # Migration: add last_seen_at / session_token to existing SQLite databases
        db_uri = app.config['SQLALCHEMY_DATABASE_URI']
        if db_uri.startswith('sqlite:///'):
            db_path = db_uri[len('sqlite:///'):]
            if os.path.isfile(db_path):
                try:
                    conn = sqlite3.connect(db_path)
                    cursor = conn.cursor()
                    cursor.execute('PRAGMA table_info(user)')
                    cols = [c[1] for c in cursor.fetchall()]
                    if 'last_seen_at' not in cols:
                        cursor.execute('ALTER TABLE "user" ADD COLUMN last_seen_at DATETIME')
                        conn.commit()
                    if 'session_token' not in cols:
                        cursor.execute('ALTER TABLE "user" ADD COLUMN session_token VARCHAR(64)')
                        conn.commit()
                    conn.close()
                except Exception as mig_err:
                    app.logger.error(
                        'Database migration failed — columns last_seen_at / session_token '
                        'may be missing, which will cause runtime errors: %s',
                        mig_err, exc_info=True
                    )
        # Create default admin user if not exists
        from app.models import User
        admin_user = User.query.filter_by(employee_id='admin').first()
        if not admin_user:
            # Default password is 'admin123', can be overridden with ADMIN_PASSWORD env var
            admin_password = os.environ.get('ADMIN_PASSWORD', 'admin123')
            
            if os.environ.get('ADMIN_PASSWORD'):
                print(
                    f'\n[MGG_SYS] Admin account created with custom password from ADMIN_PASSWORD env var.\n'
                )
            else:
                print(
                    f'\n[MGG_SYS] Default admin account created.\n'
                    f'  Employee ID : admin\n'
                    f'  Password    : admin123\n'
                    f'  ⚠️  IMPORTANT: Change this password in production!\n'
                    f'  (Set ADMIN_PASSWORD env var to use a custom password)\n'
                )
            
            admin_user = User(
                username='admin',
                employee_id='admin',
                role='admin'
            )
            admin_user.set_password(admin_password)
            db.session.add(admin_user)
            db.session.commit()

    return app
