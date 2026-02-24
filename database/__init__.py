"""
MGG Database Package

Optimized hybrid database design combining:
- Simplicity of embedded parameters
- Performance of separated time series
- Best practices from both normalized and denormalized approaches

For documentation, see database/README.md
"""

from database.extensions import db, login_manager, bcrypt
from database.manager import init_database, reset_database, backup_database

__all__ = [
    'db',
    'login_manager',
    'bcrypt',
    'init_database',
    'reset_database',
    'backup_database',
]
