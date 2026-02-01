"""Utility functions and classes for MGG_SYS"""
from .paths import (
    get_project_root,
    get_models_path,
    get_demo_scripts_path,
    get_data_directory,
    get_temp_directory,
    get_upload_directory
)

from .errors import (
    AppError,
    FileValidationError,
    SimulationError,
    SubprocessError,
    SubprocessTimeoutError,
    DataProcessingError
)

from .responses import (
    success_response,
    error_response,
    validation_error,
    file_error,
    simulation_error
)

from .validators import (
    validate_file_extension,
    validate_file_size,
    is_valid_excel_file
)

from .file_handler import FileHandler
from .subprocess_runner import SubprocessRunner
from .plotter import Plotter
from .logo_generator import LogoGenerator
from .log_manager import log_manager, LogManager

__all__ = [
    # Paths
    'get_project_root',
    'get_models_path',
    'get_demo_scripts_path',
    'get_data_directory',
    'get_temp_directory',
    'get_upload_directory',

    # Errors
    'AppError',
    'FileValidationError',
    'SimulationError',
    'SubprocessError',
    'SubprocessTimeoutError',
    'DataProcessingError',

    # Responses
    'success_response',
    'error_response',
    'validation_error',
    'file_error',
    'simulation_error',

    # Validators
    'validate_file_extension',
    'validate_file_size',
    'is_valid_excel_file',

    # Handlers
    'FileHandler',
    'SubprocessRunner',
    'Plotter',
    'LogoGenerator',
    'LogManager',
    'log_manager',
]
