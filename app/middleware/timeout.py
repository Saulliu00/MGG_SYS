"""Request timeout middleware for MGG_SYS"""
import signal
from flask import request, jsonify, current_app
from functools import wraps


class TimeoutError(Exception):
    """Request timeout exception"""
    pass


def timeout_handler(signum, frame):
    """Signal handler for timeout"""
    raise TimeoutError("Request timed out")


def get_timeout_for_endpoint(endpoint: str) -> int:
    """
    Get appropriate timeout for a specific endpoint.

    Args:
        endpoint: Flask endpoint name

    Returns:
        int: Timeout in seconds
    """
    timeouts = current_app.config.get('TIMEOUTS', {})

    # Map endpoint patterns to timeout categories
    if 'simulation' in endpoint and 'run' in endpoint:
        return timeouts.get('simulation', 120)
    elif 'upload' in endpoint or 'file' in endpoint:
        return timeouts.get('file_upload', 60)
    elif 'database' in endpoint or 'query' in endpoint:
        return timeouts.get('database_query', 10)
    elif 'static' in endpoint:
        return timeouts.get('static_files', 5)
    else:
        return timeouts.get('default_request', 30)


def with_timeout(f):
    """
    Decorator to apply request timeout to a Flask route.

    Usage:
        @bp.route('/endpoint')
        @with_timeout
        def my_endpoint():
            ...
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Get timeout for this endpoint
        timeout = get_timeout_for_endpoint(request.endpoint)

        # Set up signal alarm for timeout
        signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(timeout)

        try:
            result = f(*args, **kwargs)
            signal.alarm(0)  # Cancel alarm
            return result
        except TimeoutError:
            signal.alarm(0)  # Cancel alarm
            return jsonify({
                'success': False,
                'error': f'Request timed out after {timeout} seconds'
            }), 504
        except Exception as e:
            signal.alarm(0)  # Cancel alarm
            raise e

    return decorated_function


def init_timeout_middleware(app):
    """
    Initialize timeout middleware for the Flask app.

    This adds request timeout tracking to all requests.

    Args:
        app: Flask application instance
    """
    @app.before_request
    def before_request():
        """Log request start time"""
        request._start_time = None
        # Store start time if logging is enabled
        if app.config.get('NETWORK_LOGGING', {}).get('log_slow_requests', False):
            import time
            request._start_time = time.time()

    @app.after_request
    def after_request(response):
        """Log slow requests"""
        if hasattr(request, '_start_time') and request._start_time:
            import time
            elapsed = time.time() - request._start_time
            threshold = app.config.get('NETWORK_LOGGING', {}).get('slow_request_threshold', 5.0)

            if elapsed > threshold:
                app.logger.warning(
                    f'Slow request: {request.method} {request.path} took {elapsed:.2f}s'
                )

        return response

    @app.errorhandler(504)
    def handle_timeout(error):
        """Handle timeout errors"""
        return jsonify({
            'success': False,
            'error': 'Request timed out. Please try again.'
        }), 504

    app.logger.info('Request timeout middleware initialized')
