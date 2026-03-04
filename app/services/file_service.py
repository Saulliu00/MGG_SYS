"""File service for handling file operations and test data"""
import json
import os
from typing import Dict
from werkzeug.datastructures import FileStorage
from werkzeug.utils import secure_filename

from app.models import TestResult
from app.utils.file_handler import FileHandler
from app.utils.subprocess_runner import SubprocessRunner
from app.utils.paths import (
    get_upload_directory,
    get_data_directory,
    get_temp_directory,
    ensure_directory_exists
)
from app.utils.errors import FileValidationError, DataProcessingError, SubprocessError
from app.config.constants import ERROR_MESSAGES, SUCCESS_MESSAGES, DEFAULT_CUSTOM_NAME


class FileService:
    """Service for managing file operations"""

    def __init__(self, db):
        """
        Initialize file service.

        Args:
            db: SQLAlchemy database instance
        """
        self.db = db
        self.file_handler = FileHandler()

    def process_test_result_upload(self, file: FileStorage, user_id: int, simulation_id=None, work_order=None) -> Dict:
        """
        Process uploaded test result file and save to database.

        Args:
            file: Uploaded file from request.files
            user_id: ID of the user uploading the file
            simulation_id: Optional simulation ID to link this result to
            work_order: Optional work order number to auto-link to latest simulation

        Returns:
            Dict: Success response with test_result_id and data

        Raises:
            FileValidationError: If file validation fails
            DataProcessingError: If file processing fails
        """
        # Validate file
        self.file_handler.validate_excel_file(file)

        # Generate secure filename
        filename = secure_filename(file.filename)

        # Get upload directory
        upload_dir = get_upload_directory()
        ensure_directory_exists(upload_dir)

        # Save file
        filepath = os.path.join(upload_dir, filename)
        file.save(filepath)

        try:
            # Load Excel data
            data_dict = self.file_handler.load_excel_data_as_dict(filepath)

            # Resolve simulation_id
            # work_order takes priority when explicitly provided (UI intent: "leave blank
            # to use current simulation result"), falling back to simulation_id if no
            # matching simulation is found for that work order.
            linked_sim_id = None
            if work_order:
                from app.models import Simulation
                sim = (
                    Simulation.query
                    .filter_by(work_order=str(work_order).strip())
                    .order_by(Simulation.created_at.desc())
                    .first()
                )
                if sim:
                    linked_sim_id = sim.id
                elif simulation_id:
                    try:
                        linked_sim_id = int(simulation_id)
                    except (ValueError, TypeError):
                        pass
            elif simulation_id:
                try:
                    linked_sim_id = int(simulation_id)
                except (ValueError, TypeError):
                    pass

            # Create test result record
            test_result = TestResult(
                user_id=user_id,
                simulation_id=linked_sim_id,
                filename=filename,
                file_path=filepath,
                data=json.dumps(data_dict)
            )

            self.db.session.add(test_result)
            self.db.session.commit()

            return {
                'success': True,
                'test_result_id': test_result.id,
                'data': data_dict
            }

        except Exception as e:
            # Clean up file if database operation fails
            self.file_handler.delete_file(filepath)
            raise DataProcessingError(f'{ERROR_MESSAGES["file_parse_error"]}: {str(e)}')

    def validate_upload_file(self, file: FileStorage) -> Dict:
        """
        Save file to temp directory, validate it, then delete the temp file.

        Returns the validation result dict from FileHandler.validate_test_data_file.
        """
        temp_dir = get_temp_directory()
        ensure_directory_exists(temp_dir)

        filename = secure_filename(file.filename)
        temp_path = os.path.join(temp_dir, filename)
        file.save(temp_path)

        try:
            result = self.file_handler.validate_test_data_file(temp_path)
        finally:
            self.file_handler.delete_file(temp_path)

        return result

    def save_to_demo_data_folder(self, file: FileStorage, nc_value: str, custom_name: str = None) -> Dict:
        """
        Save uploaded file to demo/data folder with custom naming (no authentication required).

        Args:
            file: Uploaded file from request.files
            nc_value: NC value for filename
            custom_name: Custom name for filename (default: 'value')

        Returns:
            Dict: Success response with filename and message

        Raises:
            FileValidationError: If file validation fails
        """
        # Validate file
        self.file_handler.validate_excel_file(file)

        # Validate NC value
        if not nc_value:
            raise FileValidationError(ERROR_MESSAGES['nc_value_missing'])

        # Use default custom name if not provided
        if not custom_name:
            custom_name = DEFAULT_CUSTOM_NAME

        # Create filename: {nc_value}_{custom_name}.xlsx
        new_filename = f"{nc_value}_{custom_name}.xlsx"

        # Get data directory
        data_dir = get_data_directory()
        ensure_directory_exists(data_dir)

        # Save file
        file_path = os.path.join(data_dir, new_filename)
        file.save(file_path)

        return {
            'success': True,
            'filename': new_filename,
            'message': SUCCESS_MESSAGES['file_saved'].format(filename=new_filename)
        }

    def load_test_data_file(self, file: FileStorage) -> Dict:
        """
        Load test data from uploaded file using subprocess (temporary file handling).

        Args:
            file: Uploaded file from request.files

        Returns:
            Dict: Test data with time and pressure arrays

        Raises:
            FileValidationError: If file validation fails
            SubprocessError: If file processing fails
        """
        # Validate file
        self.file_handler.validate_excel_file(file)

        # Get temp directory
        temp_dir = get_temp_directory()
        ensure_directory_exists(temp_dir)

        # Save file temporarily
        filename = secure_filename(file.filename)
        temp_path = os.path.join(temp_dir, filename)
        file.save(temp_path)

        try:
            # Run data loader script
            response_data = SubprocessRunner.run_data_loader_script(temp_path)

            # Clean up temp file on success
            self.file_handler.delete_file(temp_path)

            return response_data

        except Exception as e:
            # Clean up temp file on error
            self.file_handler.delete_file(temp_path)
            raise

    def get_test_result_by_id(self, test_result_id: int, user_id: int) -> TestResult:
        """
        Get a test result by ID.

        Args:
            test_result_id: ID of the test result
            user_id: ID of the user (for authorization)

        Returns:
            TestResult: Test result record

        Raises:
            DataProcessingError: If test result not found or unauthorized
        """
        test_result = TestResult.query.filter_by(
            id=test_result_id,
            user_id=user_id
        ).first()

        if not test_result:
            raise DataProcessingError('Test result not found or unauthorized')

        return test_result

    def get_test_result_data(self, test_result_id: int, user_id: int) -> Dict:
        """
        Get test result data as a dictionary.

        Args:
            test_result_id: ID of the test result
            user_id: ID of the user (for authorization)

        Returns:
            Dict: Test result data

        Raises:
            DataProcessingError: If test result not found or unauthorized
        """
        test_result = self.get_test_result_by_id(test_result_id, user_id)

        if not test_result.data:
            return {}

        try:
            return json.loads(test_result.data)
        except json.JSONDecodeError:
            return {}

    def cleanup_old_temp_files(self, max_age_minutes=60):
        """
        Clean up old temporary files.

        Args:
            max_age_minutes: Maximum age of files to keep (default: 60)
        """
        temp_dir = get_temp_directory()
        self.file_handler.cleanup_temp_files(temp_dir, max_age_minutes)
