"""Response helper functions for standardized JSON responses"""
from typing import Dict, List, Tuple, Any


def success_response(data=None, message="Success", code=200) -> Tuple[Dict, int]:
    """
    Create a standardized success response.

    Args:
        data: Response data (optional)
        message: Success message (default: "Success")
        code: HTTP status code (default: 200)

    Returns:
        Tuple of (response_dict, status_code)
    """
    response = {
        'success': True,
        'message': message
    }
    if data is not None:
        if isinstance(data, dict):
            response.update(data)
        else:
            response['data'] = data
    return response, code


def error_response(message, code=400) -> Tuple[Dict, int]:
    """
    Create a standardized error response.

    Args:
        message: Error message
        code: HTTP status code (default: 400)

    Returns:
        Tuple of (response_dict, status_code)
    """
    return {
        'success': False,
        'error': message
    }, code


def validation_error(errors, message="Validation failed", code=400) -> Tuple[Dict, int]:
    """
    Create a validation error response.

    Args:
        errors: List of validation error messages or single error string
        message: Main error message (default: "Validation failed")
        code: HTTP status code (default: 400)

    Returns:
        Tuple of (response_dict, status_code)
    """
    if isinstance(errors, str):
        errors = [errors]

    return {
        'success': False,
        'error': message,
        'errors': errors
    }, code


def file_error(message, code=400) -> Tuple[Dict, int]:
    """
    Create a file-related error response.

    Args:
        message: Error message
        code: HTTP status code (default: 400)

    Returns:
        Tuple of (response_dict, status_code)
    """
    return {
        'success': False,
        'error': message
    }, code


def simulation_error(message, details=None, code=500) -> Tuple[Dict, int]:
    """
    Create a simulation error response.

    Args:
        message: Error message
        details: Additional error details (optional)
        code: HTTP status code (default: 500)

    Returns:
        Tuple of (response_dict, status_code)
    """
    response = {
        'success': False,
        'error': message
    }
    if details:
        response['details'] = details
    return response, code
