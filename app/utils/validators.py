"""Validation functions for MGG_SYS"""
from typing import Tuple
from app.config.constants import ALLOWED_EXTENSIONS, MAX_FILE_SIZE


def validate_file_extension(filename, allowed_extensions=None) -> bool:
    """
    Validate that a filename has an allowed extension.

    Args:
        filename (str): The filename to validate
        allowed_extensions (set): Set of allowed extensions (default: ALLOWED_EXTENSIONS)

    Returns:
        bool: True if extension is valid, False otherwise
    """
    if allowed_extensions is None:
        allowed_extensions = ALLOWED_EXTENSIONS

    if not filename or '.' not in filename:
        return False

    extension = filename.rsplit('.', 1)[1].lower()
    return extension in allowed_extensions


def validate_file_size(file, max_size=None) -> bool:
    """
    Validate that a file is within the maximum allowed size.

    Args:
        file: File object from request.files
        max_size (int): Maximum file size in bytes (default: MAX_FILE_SIZE)

    Returns:
        bool: True if file size is valid, False otherwise
    """
    if max_size is None:
        max_size = MAX_FILE_SIZE

    # Move to the end of the file to get size
    file.seek(0, 2)
    size = file.tell()
    # Reset file pointer to beginning
    file.seek(0)

    return size <= max_size


def is_valid_excel_file(file) -> Tuple[bool, str]:
    """
    Validate that a file is a valid Excel file (.xlsx).

    Args:
        file: File object from request.files

    Returns:
        Tuple[bool, str]: (is_valid, error_message)
    """
    if not file:
        return False, '没有上传文件'

    if file.filename == '':
        return False, '文件名为空'

    if not file.filename.endswith('.xlsx'):
        return False, '仅支持 .xlsx 格式文件'

    return True, ''


def validate_nc_usage(value) -> bool:
    """
    Validate NC usage value.

    Args:
        value: Value to validate (string or number)

    Returns:
        bool: True if valid, False otherwise
    """
    try:
        float_value = float(value)
        return float_value >= 0
    except (ValueError, TypeError):
        return False


def validate_simulation_params(data) -> Tuple[bool, list]:
    """
    Validate simulation parameters.

    Args:
        data (dict): Dictionary of simulation parameters

    Returns:
        Tuple[bool, list]: (is_valid, list_of_errors)
    """
    errors = []

    # Check required NC usage
    nc_usage_1 = data.get('nc_usage_1')
    if not nc_usage_1:
        errors.append('NC用量1 is required')
    elif not validate_nc_usage(nc_usage_1):
        errors.append('NC用量1 must be a valid number >= 0')

    # Add more validation as needed

    return len(errors) == 0, errors
