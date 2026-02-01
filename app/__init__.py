from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_bcrypt import Bcrypt
from flask_cors import CORS
import os
from app.config.network_config import (
    CORS_CONFIG,
    SESSION_CONFIG,
    REQUEST_LIMITS,
    TIMEOUTS,
    NETWORK_LOGGING
)
from app.utils import LogoGenerator
from app.middleware import init_timeout_middleware

db = SQLAlchemy()
login_manager = LoginManager()
bcrypt = Bcrypt()

def create_app():
    app = Flask(__name__, instance_relative_config=True)

    # Ensure the instance folder exists
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass

    # Configuration
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL') or \
        'sqlite:///' + os.path.join(app.instance_path, 'simulation_system.db')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
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
    from app.services import SimulationService, FileService, ComparisonService
    app.simulation_service = SimulationService(db)
    app.file_service = FileService(db)
    app.comparison_service = ComparisonService()

    # Generate system logos if they don't exist
    try:
        logo_paths = LogoGenerator.ensure_logos_exist()
        app.config['LOGO_PATH'] = logo_paths['logo']
        app.config['FAVICON_PATH'] = logo_paths['favicon']
    except Exception as e:
        app.logger.warning(f'Failed to generate logos: {str(e)}')

    # Initialize timeout middleware for request handling
    init_timeout_middleware(app)

    # Register blueprints
    from app.routes import auth, main, admin, simulation

    app.register_blueprint(auth.bp)
    app.register_blueprint(main.bp)
    app.register_blueprint(admin.bp)
    app.register_blueprint(simulation.bp)

    # Create database tables
    with app.app_context():
        db.create_all()
        # Create default admin user if not exists
        from app.models import User
        admin_user = User.query.filter_by(username='admin').first()
        if not admin_user:
            admin_user = User(
                username='admin',
                email='admin@example.com',
                is_admin=True
            )
            admin_user.set_password('admin123')
            db.session.add(admin_user)
            db.session.commit()

    return app
