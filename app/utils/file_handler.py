"""File handling utilities for MGG_SYS"""
import logging
import os
import time

import pandas as pd
from typing import Tuple, List
from werkzeug.utils import secure_filename
from werkzeug.datastructures import FileStorage

from app.config.constants import ERROR_MESSAGES
from .errors import FileValidationError, DataProcessingError
from .validators import is_valid_excel_file
from .paths import ensure_directory_exists


class FileHandler:
    """Handles file operations for the application"""

    @staticmethod
    def validate_excel_file(file) -> Tuple[bool, str]:
        """
        Validate that a file is a valid Excel file.

        Args:
            file: File object from request.files

        Returns:
            Tuple[bool, str]: (is_valid, error_message)

        Raises:
            FileValidationError: If file validation fails
        """
        is_valid, error_msg = is_valid_excel_file(file)
        if not is_valid:
            raise FileValidationError(error_msg)
        return True, ''

    @staticmethod
    def save_uploaded_file(file: FileStorage, destination_dir: str, custom_filename=None) -> str:
        """
        Save an uploaded file to the specified directory.

        Args:
            file: File object from request.files
            destination_dir: Directory to save the file
            custom_filename: Custom filename (optional, defaults to secure version of original)

        Returns:
            str: Full path to the saved file

        Raises:
            FileValidationError: If file is invalid
        """
        # Validate file first
        FileHandler.validate_excel_file(file)

        # Ensure destination directory exists
        ensure_directory_exists(destination_dir)

        # Generate filename
        if custom_filename:
            filename = secure_filename(custom_filename)
        else:
            filename = secure_filename(file.filename)

        # Save file
        filepath = os.path.join(destination_dir, filename)
        file.save(filepath)

        return filepath

    @staticmethod
    def load_excel_data(file_path: str, skip_rows=0) -> Tuple[List, List]:
        """
        Load time and pressure data from an Excel file.

        Args:
            file_path: Path to the Excel file
            skip_rows: Number of rows to skip (default: 0)

        Returns:
            Tuple[List, List]: (time_data, pressure_data)

        Raises:
            DataProcessingError: If file cannot be read or parsed
        """
        try:
            df = pd.read_excel(file_path, skiprows=skip_rows, header=None)

            # Assume first column is time, second column is pressure.
            # Drop any rows where either column is not a real number
            # (catches header/comment rows like '[ms]', '注释', etc.)
            col_t = df.iloc[:, 0]
            col_p = df.iloc[:, 1]
            numeric_mask = (
                pd.to_numeric(col_t, errors='coerce').notna() &
                pd.to_numeric(col_p, errors='coerce').notna()
            )
            time_data = pd.to_numeric(col_t[numeric_mask], errors='coerce').tolist()
            pressure_data = pd.to_numeric(col_p[numeric_mask], errors='coerce').tolist()

            if not time_data:
                raise DataProcessingError('文件中未找到有效的数值数据，请检查文件格式')

            return time_data, pressure_data

        except FileNotFoundError:
            raise DataProcessingError(f'File not found: {file_path}')
        except Exception as e:
            raise DataProcessingError(f'{ERROR_MESSAGES["file_parse_error"]}: {str(e)}')

    @staticmethod
    def validate_test_data_file(file_path: str) -> dict:
        """
        Validate an Excel test-data file WITHOUT saving to the database.

        Rules:
          - Exactly 2 columns after stripping non-numeric header rows
          - Column 1 (time) first value must be 0 or close to 0 (≤ 1.0)
          - Column 1 (time) must be monotonically non-decreasing
          - At least 2 numeric data rows must be present

        Returns:
            dict with keys:
              valid   (bool)
              errors  (list[str])  – non-empty when valid is False
              stats   (dict)       – present when valid is True:
                        rows, time_range [min, max], pressure_range [min, max]
        """
        try:
            df = pd.read_excel(file_path, header=None)

            # Column count check (before stripping header rows)
            if df.shape[1] < 2:
                return {'valid': False, 'errors': ['文件必须包含2列数据（时间列和压力列）']}
            if df.shape[1] > 2:
                return {
                    'valid': False,
                    'errors': [f'文件包含 {df.shape[1]} 列，请确保只有2列数据（时间列和压力列）']
                }

            # Strip non-numeric header rows
            col_t = df.iloc[:, 0]
            col_p = df.iloc[:, 1]
            numeric_mask = (
                pd.to_numeric(col_t, errors='coerce').notna() &
                pd.to_numeric(col_p, errors='coerce').notna()
            )
            time_data = pd.to_numeric(col_t[numeric_mask], errors='coerce').tolist()
            pressure_data = pd.to_numeric(col_p[numeric_mask], errors='coerce').tolist()

            if len(time_data) < 2:
                return {'valid': False, 'errors': ['文件中有效数值行数不足，请检查文件内容']}

            # Column 1 must start from near 0
            if time_data[0] > 1.0:
                return {
                    'valid': False,
                    'errors': [f'时间列第一个值为 {time_data[0]:.4f}，必须从 0 开始']
                }

            # Column 1 must be non-decreasing
            for i in range(len(time_data) - 1):
                if time_data[i] > time_data[i + 1]:
                    return {
                        'valid': False,
                        'errors': [
                            f'时间列在第 {i + 2} 行出现下降（{time_data[i]:.4f} → '
                            f'{time_data[i+1]:.4f}），时间列必须单调递增'
                        ]
                    }

            return {
                'valid': True,
                'stats': {
                    'rows': len(time_data),
                    'time_range': [round(time_data[0], 4), round(time_data[-1], 4)],
                    'pressure_range': [
                        round(min(pressure_data), 4),
                        round(max(pressure_data), 4)
                    ]
                }
            }

        except FileNotFoundError:
            return {'valid': False, 'errors': ['文件未找到，请重新上传']}
        except Exception as e:
            return {'valid': False, 'errors': [f'文件解析失败：{str(e)}']}

    @staticmethod
    def load_excel_data_as_dict(file_path: str, skip_rows=0) -> dict:
        """
        Load time and pressure data from an Excel file as a dictionary.

        Args:
            file_path: Path to the Excel file
            skip_rows: Number of rows to skip (default: 0)

        Returns:
            dict: {'time': [...], 'pressure': [...]}

        Raises:
            DataProcessingError: If file cannot be read or parsed
        """
        time_data, pressure_data = FileHandler.load_excel_data(file_path, skip_rows)
        return {
            'time': time_data,
            'pressure': pressure_data
        }

    @staticmethod
    def ensure_directory_exists(path: str) -> str:
        """
        Ensure that a directory exists, creating it if necessary.

        Args:
            path: Directory path

        Returns:
            str: The directory path
        """
        return ensure_directory_exists(path)

    @staticmethod
    def cleanup_temp_files(directory: str, max_age_minutes=60):
        """
        Clean up temporary files older than max_age_minutes.

        Args:
            directory: Directory containing temp files
            max_age_minutes: Maximum age of files to keep (default: 60)
        """
        if not os.path.exists(directory):
            return

        current_time = time.time()
        max_age_seconds = max_age_minutes * 60

        for filename in os.listdir(directory):
            file_path = os.path.join(directory, filename)
            if os.path.isfile(file_path):
                file_age = current_time - os.path.getmtime(file_path)
                if file_age > max_age_seconds:
                    try:
                        os.remove(file_path)
                    except Exception as e:
                        logging.getLogger(__name__).warning('Failed to clean up temp file %s: %s', file_path, e)

    @staticmethod
    def delete_file(file_path: str):
        """
        Safely delete a file.

        Args:
            file_path: Path to the file to delete
        """
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
        except Exception as e:
            logging.getLogger(__name__).warning('Failed to delete file %s: %s', file_path, e)
