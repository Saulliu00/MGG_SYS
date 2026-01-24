"""
Database Configuration and Connection Management
PostgreSQL connection settings and SQLAlchemy engine setup
"""

import os
from sqlalchemy import create_engine, pool
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, scoped_session
from contextlib import contextmanager
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Base class for SQLAlchemy models
Base = declarative_base()

# Database Configuration
class DatabaseConfig:
    """Database configuration from environment variables"""

    # PostgreSQL Connection
    POSTGRES_USER = os.getenv('POSTGRES_USER', 'mgg_user')
    POSTGRES_PASSWORD = os.getenv('POSTGRES_PASSWORD', 'mgg_password')
    POSTGRES_HOST = os.getenv('POSTGRES_HOST', 'localhost')
    POSTGRES_PORT = os.getenv('POSTGRES_PORT', '5432')
    POSTGRES_DB = os.getenv('POSTGRES_DB', 'mgg_simulation')

    # Connection Pool Settings
    POOL_SIZE = int(os.getenv('DB_POOL_SIZE', '10'))
    MAX_OVERFLOW = int(os.getenv('DB_MAX_OVERFLOW', '20'))
    POOL_TIMEOUT = int(os.getenv('DB_POOL_TIMEOUT', '30'))
    POOL_RECYCLE = int(os.getenv('DB_POOL_RECYCLE', '3600'))  # 1 hour

    # Archive Settings
    ARCHIVE_PATH = os.getenv('ARCHIVE_PATH', 'parquet_archive')
    COMPRESSION = os.getenv('PARQUET_COMPRESSION', 'snappy')  # snappy, gzip, brotli

    @classmethod
    def get_database_url(cls):
        """Construct PostgreSQL connection URL"""
        return (
            f"postgresql://{cls.POSTGRES_USER}:{cls.POSTGRES_PASSWORD}"
            f"@{cls.POSTGRES_HOST}:{cls.POSTGRES_PORT}/{cls.POSTGRES_DB}"
        )

    @classmethod
    def get_async_database_url(cls):
        """Construct async PostgreSQL connection URL"""
        return (
            f"postgresql+asyncpg://{cls.POSTGRES_USER}:{cls.POSTGRES_PASSWORD}"
            f"@{cls.POSTGRES_HOST}:{cls.POSTGRES_PORT}/{cls.POSTGRES_DB}"
        )


class DatabaseManager:
    """Singleton database manager for connection pooling"""

    _instance = None
    _engine = None
    _session_factory = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(DatabaseManager, cls).__new__(cls)
            cls._instance._initialize()
        return cls._instance

    def _initialize(self):
        """Initialize database engine and session factory"""
        try:
            # Create engine with connection pooling
            self._engine = create_engine(
                DatabaseConfig.get_database_url(),
                poolclass=pool.QueuePool,
                pool_size=DatabaseConfig.POOL_SIZE,
                max_overflow=DatabaseConfig.MAX_OVERFLOW,
                pool_timeout=DatabaseConfig.POOL_TIMEOUT,
                pool_recycle=DatabaseConfig.POOL_RECYCLE,
                echo=False,  # Set to True for SQL query logging
                future=True  # Use SQLAlchemy 2.0 style
            )

            # Create session factory
            self._session_factory = scoped_session(
                sessionmaker(
                    bind=self._engine,
                    autocommit=False,
                    autoflush=False,
                    expire_on_commit=False
                )
            )

            logger.info("Database connection initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize database: {str(e)}")
            raise

    @property
    def engine(self):
        """Get SQLAlchemy engine"""
        return self._engine

    @property
    def session_factory(self):
        """Get session factory"""
        return self._session_factory

    def create_all_tables(self):
        """Create all tables defined in models"""
        try:
            Base.metadata.create_all(self._engine)
            logger.info("All tables created successfully")
        except Exception as e:
            logger.error(f"Failed to create tables: {str(e)}")
            raise

    def drop_all_tables(self):
        """Drop all tables (USE WITH CAUTION!)"""
        try:
            Base.metadata.drop_all(self._engine)
            logger.warning("All tables dropped")
        except Exception as e:
            logger.error(f"Failed to drop tables: {str(e)}")
            raise

    def test_connection(self):
        """Test database connection"""
        try:
            from sqlalchemy import text
            with self._engine.connect() as conn:
                result = conn.execute(text("SELECT version();"))
                version = result.fetchone()[0]
                logger.info(f"Database connection successful: {version}")
                return True
        except Exception as e:
            logger.error(f"Database connection failed: {str(e)}")
            return False

    def get_session(self):
        """Get a new database session"""
        return self._session_factory()

    def close_session(self, session):
        """Close a database session"""
        try:
            session.close()
        except Exception as e:
            logger.error(f"Error closing session: {str(e)}")

    def dispose_engine(self):
        """Dispose of the engine and connection pool"""
        try:
            self._engine.dispose()
            logger.info("Database engine disposed")
        except Exception as e:
            logger.error(f"Error disposing engine: {str(e)}")


# Context manager for database sessions
@contextmanager
def get_db_session():
    """
    Context manager for database sessions with automatic commit/rollback

    Usage:
        with get_db_session() as session:
            user = session.query(User).first()
            ...
    """
    db_manager = DatabaseManager()
    session = db_manager.get_session()
    try:
        yield session
        session.commit()
    except Exception as e:
        session.rollback()
        logger.error(f"Session rolled back due to error: {str(e)}")
        raise
    finally:
        db_manager.close_session(session)


# Initialize database manager (singleton)
db_manager = DatabaseManager()


# Utility functions
def init_db():
    """Initialize database and create all tables"""
    try:
        db_manager.create_all_tables()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {str(e)}")
        raise


def test_db_connection():
    """Test database connection"""
    return db_manager.test_connection()


def get_engine():
    """Get SQLAlchemy engine"""
    return db_manager.engine


def get_session():
    """Get a new database session"""
    return db_manager.get_session()


if __name__ == "__main__":
    # Test database connection
    print("Testing database connection...")
    if test_db_connection():
        print("✓ Database connection successful!")
    else:
        print("✗ Database connection failed!")
