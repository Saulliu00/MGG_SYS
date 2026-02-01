"""Subprocess execution utilities for MGG_SYS"""
import subprocess
import sys
import json
from typing import Dict

from app.config.constants import SUBPROCESS_TIMEOUT, ERROR_MESSAGES
from .errors import SubprocessError, SubprocessTimeoutError, SimulationError
from .paths import (
    get_simulation_script_path,
    get_load_test_data_script_path,
    get_models_path
)


class SubprocessRunner:
    """Handles subprocess execution for simulation scripts"""

    @staticmethod
    def execute_script(script_path: str, args: list, timeout=None) -> Dict:
        """
        Execute a Python script with the given arguments.

        Args:
            script_path: Path to the script to execute
            args: List of arguments to pass to the script
            timeout: Timeout in seconds (default: SUBPROCESS_TIMEOUT)

        Returns:
            Dict: Parsed JSON output from the script

        Raises:
            SubprocessTimeoutError: If script execution times out
            SubprocessError: If script execution fails
            SimulationError: If script returns an error in JSON
        """
        if timeout is None:
            timeout = SUBPROCESS_TIMEOUT

        try:
            # Build command
            command = [sys.executable, script_path] + args

            # Execute subprocess
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=timeout
            )

            # Check return code
            if result.returncode != 0:
                raise SubprocessError(
                    f"{ERROR_MESSAGES['script_execution_failed']}: {result.stderr}",
                    stderr=result.stderr
                )

            # Parse JSON output
            try:
                response_data = json.loads(result.stdout)
            except json.JSONDecodeError as e:
                raise SubprocessError(
                    f"Failed to parse script output: {str(e)}\nOutput: {result.stdout}"
                )

            # Check if script returned an error
            if not response_data.get('success', True):
                error_msg = response_data.get('error', 'Unknown error')
                raise SimulationError(f"Simulation error: {error_msg}")

            return response_data

        except subprocess.TimeoutExpired:
            raise SubprocessTimeoutError(ERROR_MESSAGES['simulation_timeout'])

        except (SubprocessError, SubprocessTimeoutError, SimulationError):
            # Re-raise our custom exceptions
            raise

        except Exception as e:
            raise SubprocessError(f"{ERROR_MESSAGES['simulation_error']}: {str(e)}")

    @staticmethod
    def run_simulation_script(nc_usage_1: float) -> Dict:
        """
        Run the simulation script with NC usage parameter.

        Args:
            nc_usage_1: NC usage value (float)

        Returns:
            Dict: Simulation results with plot_data and statistics

        Raises:
            SubprocessTimeoutError: If simulation times out
            SubprocessError: If simulation fails
            SimulationError: If simulation returns an error
        """
        script_path = get_simulation_script_path()
        models_path = get_models_path()

        args = [str(nc_usage_1), models_path]

        return SubprocessRunner.execute_script(script_path, args)

    @staticmethod
    def run_data_loader_script(file_path: str) -> Dict:
        """
        Run the data loader script to process test data.

        Args:
            file_path: Path to the Excel file to load

        Returns:
            Dict: Loaded test data with time and pressure arrays

        Raises:
            SubprocessTimeoutError: If loading times out
            SubprocessError: If loading fails
        """
        script_path = get_load_test_data_script_path()

        args = [file_path]

        try:
            return SubprocessRunner.execute_script(script_path, args)
        except SubprocessError as e:
            # Customize error message for file processing
            raise SubprocessError(
                f"{ERROR_MESSAGES['file_process_failed']}: {str(e)}",
                stderr=e.stderr if hasattr(e, 'stderr') else None
            )

    @staticmethod
    def _parse_json_output(stdout: str) -> Dict:
        """
        Parse JSON output from subprocess stdout.

        Args:
            stdout: Standard output string from subprocess

        Returns:
            Dict: Parsed JSON data

        Raises:
            SubprocessError: If JSON parsing fails
        """
        try:
            return json.loads(stdout)
        except json.JSONDecodeError as e:
            raise SubprocessError(f"Failed to parse script output: {str(e)}")

    @staticmethod
    def _handle_error(result) -> None:
        """
        Handle subprocess errors.

        Args:
            result: subprocess.CompletedProcess result

        Raises:
            SubprocessError: Always raises with error details
        """
        raise SubprocessError(
            f"{ERROR_MESSAGES['script_execution_failed']}: {result.stderr}",
            stderr=result.stderr
        )
