"""Flask extensions for the database layer.

These are created here (not in app/) so that models can import them
without circular dependencies.  app/__init__.py imports these and
calls .init_app(app) during application startup.
"""
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_bcrypt import Bcrypt

db = SQLAlchemy()
login_manager = LoginManager()
bcrypt = Bcrypt()
