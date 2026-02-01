"""Logging configuration for MGG_SYS CSV-based system logs"""
import os
from datetime import datetime

# Log directory configuration
LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'log')

# Log file naming
LOG_FILE_PREFIX = 'mgg_system_log'
LOG_FILE_EXTENSION = '.csv'

# Log rotation configuration
LOG_ROTATION = {
    'enabled': True,
    'frequency': 'daily',  # 'daily', 'hourly', or 'on_reboot'
    'max_folder_size_gb': 30,  # Maximum total size of log folder in GB
    'max_folder_size_bytes': 30 * 1024 * 1024 * 1024,  # 30GB in bytes
}

# CSV log format
CSV_HEADERS = [
    'timestamp',           # ISO format timestamp
    'date',               # Date (YYYY-MM-DD)
    'time',               # Time (HH:MM:SS)
    'level',              # Log level (INFO, WARNING, ERROR, CRITICAL)
    'username',           # Username (if authenticated)
    'user_id',            # User ID (if authenticated)
    'ip_address',         # Client IP address
    'method',             # HTTP method (GET, POST, etc.)
    'endpoint',           # Flask endpoint
    'path',               # Request path
    'status_code',        # HTTP response status code
    'duration_ms',        # Request duration in milliseconds
    'action',             # Action description (login, simulation, upload, etc.)
    'message',            # Log message
    'error',              # Error message (if any)
    'traceback',          # Error traceback (if any)
    'user_agent',         # User agent string
    'request_id',         # Unique request ID
]

# Log levels
LOG_LEVELS = {
    'DEBUG': 10,
    'INFO': 20,
    'WARNING': 30,
    'ERROR': 40,
    'CRITICAL': 50,
}

# Events to log
LOG_EVENTS = {
    'system_startup': True,
    'system_shutdown': True,
    'user_login': True,
    'user_logout': True,
    'user_registration': True,
    'simulation_run': True,
    'file_upload': True,
    'file_download': True,
    'database_error': True,
    'network_error': True,
    'timeout_error': True,
    'validation_error': True,
    'all_requests': False,  # Set to True to log every HTTP request
    'slow_requests': True,  # Log requests exceeding threshold
    'failed_requests': True,  # Log 4xx and 5xx responses
}

# Slow request threshold (milliseconds)
SLOW_REQUEST_THRESHOLD_MS = 5000  # 5 seconds

# Log file retention
LOG_RETENTION = {
    'keep_days': 90,  # Keep logs for 90 days minimum before cleanup
    'compress_after_days': 7,  # Compress logs older than 7 days (optional)
}

# Exclusions (endpoints to not log)
LOG_EXCLUSIONS = {
    'endpoints': [
        '/static/*',  # Don't log static file requests
        '/health',    # Don't log health check requests (too frequent)
    ],
    'user_agents': [
        'HealthChecker',  # Exclude health check monitoring
    ],
}

# Admin log viewing
ADMIN_LOG_VIEW = {
    'enabled': True,
    'max_rows_display': 1000,  # Maximum rows to display in web interface
    'download_enabled': True,  # Allow downloading log files
}

def get_current_log_filename():
    """
    Get the current log filename based on rotation frequency.

    Returns:
        str: Log filename (without path)
    """
    now = datetime.now()

    if LOG_ROTATION['frequency'] == 'daily':
        date_str = now.strftime('%Y-%m-%d')
    elif LOG_ROTATION['frequency'] == 'hourly':
        date_str = now.strftime('%Y-%m-%d_%H')
    else:  # on_reboot
        date_str = now.strftime('%Y-%m-%d_%H-%M-%S')

    return f"{LOG_FILE_PREFIX}_{date_str}{LOG_FILE_EXTENSION}"

def get_current_log_filepath():
    """
    Get the full path to the current log file.

    Returns:
        str: Full path to log file
    """
    return os.path.join(LOG_DIR, get_current_log_filename())
