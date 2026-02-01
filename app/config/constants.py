"""Centralized configuration constants for MGG_SYS"""
import os

# File handling constants
ALLOWED_EXTENSIONS = {'xlsx', 'xls'}
MAX_FILE_SIZE = 16 * 1024 * 1024  # 16MB
UPLOAD_FOLDER = 'app/static/uploads'

# Simulation constants
SIMULATION_TIMEOUT = 30  # seconds
SUBPROCESS_TIMEOUT = 30  # seconds

# Directory names
DEMO_DIR = 'demo'
DATA_DIR = 'data'
TEMP_DIR = 'temp'
MODELS_DIR = 'models'

# Script names
RUN_SIMULATION_SCRIPT = 'run_simulation.py'
LOAD_TEST_DATA_SCRIPT = 'load_test_data.py'

# Error messages (Chinese)
ERROR_MESSAGES = {
    'no_file_uploaded': '没有上传文件',
    'empty_filename': '文件名为空',
    'invalid_file_format': '仅支持 .xlsx 格式文件',
    'file_parse_error': '文件解析错误',
    'nc_value_missing': 'NC用量1值未提供',
    'save_file_failed': '保存文件失败',
    'load_data_failed': 'Error loading test data',
    'simulation_timeout': 'Simulation timeout (exceeded 30 seconds)',
    'file_processing_timeout': 'File processing timeout (exceeded 30 seconds)',
    'script_execution_failed': 'Script execution failed',
    'file_process_failed': 'Failed to process file',
    'simulation_error': 'Error running simulation',
}

# Success messages
SUCCESS_MESSAGES = {
    'file_saved': '文件已保存到 demo/data/{filename}',
}

# Default values
DEFAULT_NC_USAGE = 0.0
DEFAULT_CUSTOM_NAME = 'value'
