"""Network configuration for MGG_SYS"""
import os

# Request timeout settings (in seconds)
TIMEOUTS = {
    'default_request': 30,          # Default request timeout
    'simulation': 120,               # Simulation endpoints (longer timeout)
    'file_upload': 60,              # File upload endpoints
    'database_query': 10,            # Database query timeout
    'static_files': 5,              # Static file serving
}

# Connection pool settings
CONNECTION_POOL = {
    'max_connections': 100,          # Maximum number of connections
    'max_keepalive': 50,            # Maximum keepalive connections
    'keepalive_timeout': 5,         # Keepalive timeout in seconds
}

# Rate limiting (optional - can be enabled if needed)
RATE_LIMIT = {
    'enabled': False,                # Set to True to enable rate limiting
    'default': '100 per minute',     # Default rate limit
    'simulation': '10 per minute',   # Simulation endpoint rate limit
    'upload': '20 per minute',       # Upload endpoint rate limit
}

# CORS settings for local network access
CORS_CONFIG = {
    'origins': os.environ.get('CORS_ORIGINS', '*'),  # Allow all origins by default for local network
    'methods': ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'],
    'allow_headers': ['Content-Type', 'Authorization'],
    'expose_headers': ['Content-Range', 'X-Content-Range'],
    'supports_credentials': True,
    'max_age': 3600,
}

# Session configuration for multi-user support
SESSION_CONFIG = {
    'session_timeout': 3600,         # Session timeout in seconds (1 hour)
    'permanent_session_lifetime': 86400,  # Permanent session lifetime (24 hours)
    'session_cookie_secure': False,  # Set to True if using HTTPS
    'session_cookie_httponly': True,  # Prevent XSS attacks
    'session_cookie_samesite': 'Lax',  # CSRF protection
}

# Worker configuration for multi-user access
WORKER_CONFIG = {
    'workers': os.cpu_count() * 2 + 1,  # Number of worker processes
    'threads': 4,                        # Threads per worker
    'worker_class': 'sync',             # Worker class (sync, gevent, eventlet)
    'max_requests': 1000,               # Max requests per worker before restart
    'max_requests_jitter': 50,          # Random jitter to prevent all workers restarting simultaneously
    'timeout': 30,                      # Worker timeout
    'graceful_timeout': 30,             # Graceful shutdown timeout
}

# Request size limits
REQUEST_LIMITS = {
    'max_content_length': 16 * 1024 * 1024,  # 16MB max request size
    'max_form_memory_size': 2 * 1024 * 1024,  # 2MB max form memory
}

# Logging configuration for network issues
NETWORK_LOGGING = {
    'log_slow_requests': True,       # Log requests that exceed timeout
    'slow_request_threshold': 5.0,   # Threshold in seconds
    'log_failed_requests': True,     # Log failed requests
    'log_network_errors': True,      # Log network errors
}

# Health check configuration
HEALTH_CHECK = {
    'endpoint': '/health',
    'enabled': True,
    'check_database': True,
    'check_file_system': True,
}

# Gunicorn production server configuration
GUNICORN_CONFIG = {
    'bind': '0.0.0.0:5001',
    'workers': WORKER_CONFIG['workers'],
    'threads': WORKER_CONFIG['threads'],
    'worker_class': WORKER_CONFIG['worker_class'],
    'max_requests': WORKER_CONFIG['max_requests'],
    'max_requests_jitter': WORKER_CONFIG['max_requests_jitter'],
    'timeout': WORKER_CONFIG['timeout'],
    'graceful_timeout': WORKER_CONFIG['graceful_timeout'],
    'keepalive': CONNECTION_POOL['keepalive_timeout'],
    'accesslog': '-',  # Log to stdout
    'errorlog': '-',   # Log to stderr
    'loglevel': 'info',
    'preload_app': True,  # Preload app for faster worker spawning
}
