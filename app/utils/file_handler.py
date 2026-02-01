"""File handling utilities for MGG_SYS"""
import os
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
            df = pd.read_excel(file_path, skiprows=skip_rows)

            # Assume first column is time, second column is pressure
            time_data = df.iloc[:, 0].tolist()
            pressure_data = df.iloc[:, 1].tolist()

            return time_data, pressure_data

        except FileNotFoundError:
            raise DataProcessingError(f'File not found: {file_path}')
        except Exception as e:
            raise DataProcessingError(f'{ERROR_MESSAGES["file_parse_error"]}: {str(e)}')

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
        import time

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
                    except Exception:
                        pass  # Silently ignore errors during cleanup

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
        except Exception:
            pass  # Silently ignore errors
