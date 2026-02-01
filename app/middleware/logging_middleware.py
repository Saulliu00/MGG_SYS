"""Logging middleware for automatic request/response logging"""
import time
import uuid
import traceback as tb
from flask import request, g
from flask_login import current_user
from functools import wraps
from app.config.logging_config import (
    LOG_EVENTS,
    SLOW_REQUEST_THRESHOLD_MS,
    LOG_EXCLUSIONS
)
from app.utils.log_manager import log_manager


def should_log_request(endpoint: str, user_agent: str) -> bool:
    """
    Determine if a request should be logged based on exclusions.

    Args:
        endpoint: Flask endpoint
        user_agent: User agent string

    Returns:
        bool: True if should log, False otherwise
    """
    # Check endpoint exclusions
    for excluded_endpoint in LOG_EXCLUSIONS.get('endpoints', []):
        if excluded_endpoint.endswith('*'):
            # Wildcard matching
            prefix = excluded_endpoint[:-1]
            if endpoint and endpoint.startswith(prefix):
                return False
        elif endpoint == excluded_endpoint:
            return False

    # Check user agent exclusions
    for excluded_ua in LOG_EXCLUSIONS.get('user_agents', []):
        if excluded_ua in user_agent:
            return False

    return True


def init_logging_middleware(app):
    """
    Initialize logging middleware for the Flask app.

    Args:
        app: Flask application instance
    """

    @app.before_request
    def before_request_logging():
        """Set up request context and timing"""
        # Generate unique request ID
        g.request_id = str(uuid.uuid4())
        g.request_start_time = time.time()

        # Store request info for logging
        g.request_info = {
            'method': request.method,
            'path': request.path,
            'endpoint': request.endpoint,
            'ip_address': request.remote_addr,
            'user_agent': request.headers.get('User-Agent', ''),
        }

    @app.after_request
    def after_request_logging(response):
        """Log request after completion"""
        try:
            # Calculate request duration
            duration_ms = (time.time() - g.request_start_time) * 1000 if hasattr(g, 'request_start_time') else 0

            # Get user info if authenticated
            username = current_user.username if current_user.is_authenticated else None
            user_id = current_user.id if current_user.is_authenticated else None

            # Get request info
            method = g.request_info.get('method') if hasattr(g, 'request_info') else request.method
            path = g.request_info.get('path') if hasattr(g, 'request_info') else request.path
            endpoint = g.request_info.get('endpoint') if hasattr(g, 'request_info') else request.endpoint
            ip_address = g.request_info.get('ip_address') if hasattr(g, 'request_info') else request.remote_addr
            user_agent = g.request_info.get('user_agent') if hasattr(g, 'request_info') else request.headers.get('User-Agent', '')
            request_id = g.request_id if hasattr(g, 'request_id') else None

            # Check if we should log this request
            if not should_log_request(endpoint or path, user_agent):
                return response

            # Determine if we should log based on settings
            status_code = response.status_code
            is_error = status_code >= 400
            is_slow = duration_ms >= SLOW_REQUEST_THRESHOLD_MS

            should_log = (
                LOG_EVENTS.get('all_requests', False) or
                (LOG_EVENTS.get('failed_requests', True) and is_error) or
                (LOG_EVENTS.get('slow_requests', True) and is_slow)
            )

            if should_log:
                log_manager.log_request(
                    method=method,
                    path=path,
                    status_code=status_code,
                    duration_ms=duration_ms,
                    username=username,
                    user_id=user_id,
                    ip_address=ip_address,
                    endpoint=endpoint,
                    user_agent=user_agent,
                    request_id=request_id,
                )

        except Exception as e:
            # Don't let logging errors crash the application
            app.logger.error(f'Logging middleware error: {str(e)}')

        return response

    @app.errorhandler(Exception)
    def log_unhandled_exception(error):
        """Log unhandled exceptions"""
        try:
            # Get user info
            username = current_user.username if current_user.is_authenticated else None
            user_id = current_user.id if current_user.is_authenticated else None

            # Get error details
            error_message = str(error)
            error_traceback = tb.format_exc()

            # Log the error
            log_manager.log_error(
                message=f'Unhandled exception: {error.__class__.__name__}',
                error=error_message,
                traceback=error_traceback,
                username=username,
                user_id=user_id,
                ip_address=request.remote_addr if request else None,
                method=request.method if request else None,
                path=request.path if request else None,
                endpoint=request.endpoint if request else None,
                action='unhandled_exception',
            )

        except Exception as log_error:
            app.logger.error(f'Failed to log exception: {str(log_error)}')

        # Re-raise the original exception to let Flask handle it
        raise error

    # Log system startup
    log_manager.log_info(
        message='MGG System started',
        action='system_startup'
    )

    app.logger.info('Request logging middleware initialized')


def log_action(action: str, message: str = None, **kwargs):
    """
    Decorator to log specific actions.

    Usage:
        @log_action('user_login', 'User logged in successfully')
        def login():
            ...

    Args:
        action: Action name
        message: Log message (optional, will use action if not provided)
        **kwargs: Additional log parameters
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **inner_kwargs):
            result = f(*args, **inner_kwargs)

            # Get user info if authenticated
            username = current_user.username if current_user.is_authenticated else None
            user_id = current_user.id if current_user.is_authenticated else None

            # Log the action
            log_manager.log_info(
                message=message or action,
                action=action,
                username=username,
                user_id=user_id,
                ip_address=request.remote_addr if request else None,
                **kwargs
            )

            return result

        return decorated_function
    return decorator


def log_user_login(username: str, user_id: int, ip_address: str, success: bool = True):
    """
    Log a user login attempt.

    Args:
        username: Username
        user_id: User ID
        ip_address: IP address
        success: Whether login was successful
    """
    if LOG_EVENTS.get('user_login', True):
        if success:
            log_manager.log_info(
                message=f'User login successful',
                action='user_login',
                username=username,
                user_id=user_id,
                ip_address=ip_address,
            )
        else:
            log_manager.log_warning(
                message=f'User login failed',
                action='user_login_failed',
                username=username,
                ip_address=ip_address,
            )


def log_user_logout(username: str, user_id: int, ip_address: str):
    """
    Log a user logout.

    Args:
        username: Username
        user_id: User ID
        ip_address: IP address
    """
    if LOG_EVENTS.get('user_logout', True):
        log_manager.log_info(
            message=f'User logout',
            action='user_logout',
            username=username,
            user_id=user_id,
            ip_address=ip_address,
        )


def log_simulation_run(username: str, user_id: int, simulation_params: dict, success: bool = True, error: str = None):
    """
    Log a simulation run.

    Args:
        username: Username
        user_id: User ID
        simulation_params: Simulation parameters
        success: Whether simulation was successful
        error: Error message if failed
    """
    if LOG_EVENTS.get('simulation_run', True):
        param_summary = ', '.join([f'{k}={v}' for k, v in list(simulation_params.items())[:5]])

        if success:
            log_manager.log_info(
                message=f'Simulation run: {param_summary}',
                action='simulation_run',
                username=username,
                user_id=user_id,
            )
        else:
            log_manager.log_error(
                message=f'Simulation failed: {param_summary}',
                action='simulation_run_failed',
                username=username,
                user_id=user_id,
                error=error,
            )


def log_file_upload(username: str, user_id: int, filename: str, file_size: int, success: bool = True, error: str = None):
    """
    Log a file upload.

    Args:
        username: Username
        user_id: User ID
        filename: Uploaded filename
        file_size: File size in bytes
        success: Whether upload was successful
        error: Error message if failed
    """
    if LOG_EVENTS.get('file_upload', True):
        size_mb = file_size / (1024 * 1024)

        if success:
            log_manager.log_info(
                message=f'File uploaded: {filename} ({size_mb:.2f} MB)',
                action='file_upload',
                username=username,
                user_id=user_id,
            )
        else:
            log_manager.log_error(
                message=f'File upload failed: {filename}',
                action='file_upload_failed',
                username=username,
                user_id=user_id,
                error=error,
            )
