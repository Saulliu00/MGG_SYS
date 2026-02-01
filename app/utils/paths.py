"""Path resolution utilities for MGG_SYS"""
import os
from app.config.constants import (
    DEMO_DIR,
    DATA_DIR,
    TEMP_DIR,
    MODELS_DIR,
    UPLOAD_FOLDER,
    RUN_SIMULATION_SCRIPT,
    LOAD_TEST_DATA_SCRIPT
)


def get_project_root():
    """
    Get the project root directory dynamically.

    Returns:
        str: Absolute path to project root directory
    """
    # From app/utils/paths.py, go up 2 levels to reach project root
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def get_models_path():
    """
    Get the path to the models directory.

    Returns:
        str: Absolute path to models directory
    """
    return os.path.join(get_project_root(), MODELS_DIR)


def get_demo_scripts_path():
    """
    Get the path to the demo scripts directory.

    Returns:
        str: Absolute path to demo directory
    """
    return os.path.join(get_project_root(), DEMO_DIR)


def get_simulation_script_path():
    """
    Get the path to the run_simulation.py script.

    Returns:
        str: Absolute path to run_simulation.py
    """
    return os.path.join(get_demo_scripts_path(), RUN_SIMULATION_SCRIPT)


def get_load_test_data_script_path():
    """
    Get the path to the load_test_data.py script.

    Returns:
        str: Absolute path to load_test_data.py
    """
    return os.path.join(get_demo_scripts_path(), LOAD_TEST_DATA_SCRIPT)


def get_data_directory():
    """
    Get the path to the demo/data directory.

    Returns:
        str: Absolute path to demo/data directory
    """
    return os.path.join(get_demo_scripts_path(), DATA_DIR)


def get_temp_directory():
    """
    Get the path to the demo/temp directory.

    Returns:
        str: Absolute path to demo/temp directory
    """
    return os.path.join(get_demo_scripts_path(), TEMP_DIR)


def get_upload_directory():
    """
    Get the path to the upload directory.

    Returns:
        str: Absolute path to upload directory
    """
    return UPLOAD_FOLDER


def ensure_directory_exists(directory_path):
    """
    Ensure that a directory exists, creating it if necessary.

    Args:
        directory_path (str): Path to the directory

    Returns:
        str: The directory path
    """
    os.makedirs(directory_path, exist_ok=True)
    return directory_path
