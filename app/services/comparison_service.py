"""Comparison service for PT curve analysis"""
import numpy as np
from typing import Dict, List, Tuple, Optional
from app.utils.errors import DataProcessingError
from app.utils.plotter import Plotter


class ComparisonService:
    """Service for comparing simulation and test data"""

    @staticmethod
    def calculate_rmse(actual: List[float], predicted: List[float]) -> float:
        """
        Calculate Root Mean Square Error.

        Args:
            actual: Actual values
            predicted: Predicted values

        Returns:
            float: RMSE value

        Raises:
            DataProcessingError: If arrays have different lengths
        """
        if len(actual) != len(predicted):
            raise DataProcessingError('Arrays must have the same length for RMSE calculation')

        actual_array = np.array(actual)
        predicted_array = np.array(predicted)

        mse = np.mean((actual_array - predicted_array) ** 2)
        rmse = np.sqrt(mse)

        return float(rmse)

    @staticmethod
    def calculate_correlation(x: List[float], y: List[float]) -> float:
        """
        Calculate Pearson correlation coefficient.

        Args:
            x: First array
            y: Second array

        Returns:
            float: Correlation coefficient (-1 to 1)

        Raises:
            DataProcessingError: If arrays have different lengths
        """
        if len(x) != len(y):
            raise DataProcessingError('Arrays must have the same length for correlation calculation')

        x_array = np.array(x)
        y_array = np.array(y)

        correlation = np.corrcoef(x_array, y_array)[0, 1]

        return float(correlation)

    @staticmethod
    def find_peak_pressure(pressure: List[float], time: List[float] = None) -> Tuple[float, float]:
        """
        Find peak pressure and the time at which it occurs.

        Args:
            pressure: Pressure array
            time: Time array (optional)

        Returns:
            Tuple[float, float]: (peak_pressure, peak_time)
        """
        pressure_array = np.array(pressure)
        peak_idx = np.argmax(pressure_array)
        peak_pressure = float(pressure_array[peak_idx])

        if time:
            peak_time = float(time[peak_idx])
        else:
            peak_time = float(peak_idx)

        return peak_pressure, peak_time

    @staticmethod
    def interpolate_to_common_timebase(
        time1: List[float],
        pressure1: List[float],
        time2: List[float],
        pressure2: List[float]
    ) -> Tuple[List[float], List[float], List[float]]:
        """
        Interpolate two datasets to a common timebase for comparison.

        Args:
            time1: Time array for first dataset
            pressure1: Pressure array for first dataset
            time2: Time array for second dataset
            pressure2: Pressure array for second dataset

        Returns:
            Tuple[List, List, List]: (common_time, interpolated_pressure1, interpolated_pressure2)
        """
        # Create common timebase (use the one with finer resolution)
        min_time = max(min(time1), min(time2))
        max_time = min(max(time1), max(time2))

        # Determine number of points (use the dataset with more points)
        num_points = max(len(time1), len(time2))

        common_time = np.linspace(min_time, max_time, num_points)

        # Interpolate both datasets
        pressure1_interp = np.interp(common_time, time1, pressure1)
        pressure2_interp = np.interp(common_time, time2, pressure2)

        return (
            common_time.tolist(),
            pressure1_interp.tolist(),
            pressure2_interp.tolist()
        )

    @staticmethod
    def compare_pt_curves(simulation_data: Dict, test_data: Dict) -> Dict:
        """
        Compare PT curves between simulation and test data.

        Args:
            simulation_data: Dictionary with 'time' and 'pressure' keys
            test_data: Dictionary with 'time' and 'pressure' keys

        Returns:
            Dict: Comparison metrics including RMSE, correlation, peak differences

        Raises:
            DataProcessingError: If data format is invalid
        """
        try:
            # Extract data
            sim_time = simulation_data.get('time', [])
            sim_pressure = simulation_data.get('pressure', [])
            test_time = test_data.get('time', [])
            test_pressure = test_data.get('pressure', [])

            if not all([sim_time, sim_pressure, test_time, test_pressure]):
                raise DataProcessingError('Invalid data format: missing time or pressure data')

            # Interpolate to common timebase
            common_time, sim_pressure_interp, test_pressure_interp = \
                ComparisonService.interpolate_to_common_timebase(
                    sim_time, sim_pressure, test_time, test_pressure
                )

            # Calculate metrics
            rmse = ComparisonService.calculate_rmse(test_pressure_interp, sim_pressure_interp)
            correlation = ComparisonService.calculate_correlation(sim_pressure_interp, test_pressure_interp)

            # Find peak pressures
            sim_peak_pressure, sim_peak_time = ComparisonService.find_peak_pressure(sim_pressure, sim_time)
            test_peak_pressure, test_peak_time = ComparisonService.find_peak_pressure(test_pressure, test_time)

            # Calculate differences
            peak_pressure_diff = abs(sim_peak_pressure - test_peak_pressure)
            peak_time_diff = abs(sim_peak_time - test_peak_time)
            peak_pressure_error_pct = (peak_pressure_diff / test_peak_pressure) * 100 if test_peak_pressure > 0 else 0

            return {
                'rmse': round(rmse, 4),
                'correlation': round(correlation, 4),
                'simulation_peak_pressure': round(sim_peak_pressure, 2),
                'simulation_peak_time': round(sim_peak_time, 2),
                'test_peak_pressure': round(test_peak_pressure, 2),
                'test_peak_time': round(test_peak_time, 2),
                'peak_pressure_difference': round(peak_pressure_diff, 2),
                'peak_time_difference': round(peak_time_diff, 2),
                'peak_pressure_error_percent': round(peak_pressure_error_pct, 2)
            }

        except Exception as e:
            raise DataProcessingError(f'Error comparing PT curves: {str(e)}')

    @staticmethod
    def generate_comparison_chart_data(simulation_data: Dict, test_data: Dict) -> Dict:
        """
        Prepare data for Plotly visualization of PT curve comparison.

        Args:
            simulation_data: Dictionary with 'time' and 'pressure' keys
            test_data: Dictionary with 'time' and 'pressure' keys

        Returns:
            Dict: Chart data formatted for Plotly

        Raises:
            DataProcessingError: If data format is invalid
        """
        try:
            return {
                'simulation': {
                    'time': simulation_data.get('time', []),
                    'pressure': simulation_data.get('pressure', []),
                    'name': 'Simulation'
                },
                'test': {
                    'time': test_data.get('time', []),
                    'pressure': test_data.get('pressure', []),
                    'name': 'Test Data'
                }
            }

        except Exception as e:
            raise DataProcessingError(f'Error generating chart data: {str(e)}')

    @staticmethod
    def generate_comparison_chart(
        simulation_data: Optional[Dict] = None,
        test_data: Optional[Dict] = None
    ) -> Dict:
        """
        Generate a Plotly comparison chart figure.

        Args:
            simulation_data: Dictionary with 'time' and 'pressure' keys (optional)
            test_data: Dictionary with 'time' and 'pressure' keys (optional)

        Returns:
            Dict: Plotly figure as JSON-serializable dict

        Raises:
            DataProcessingError: If chart generation fails
        """
        try:
            return Plotter.create_comparison_chart(
                simulation_data=simulation_data,
                test_data=test_data
            )
        except Exception as e:
            raise DataProcessingError(f'Error generating comparison chart: {str(e)}')
