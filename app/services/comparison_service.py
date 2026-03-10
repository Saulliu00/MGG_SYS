"""Comparison service for PT curve analysis"""
import numpy as np
from typing import Dict, List, Tuple, Optional
from app.utils.errors import DataProcessingError
from app.utils.plotter import Plotter


class ComparisonService:
    """Service for comparing simulation and test data"""

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

    @staticmethod
    def average_datasets(datasets: List[Dict]) -> Dict:
        """
        Interpolate multiple time-series datasets to a common timebase and
        return the element-wise average.

        Args:
            datasets: List of dicts, each with 'time' and 'pressure' lists.
                      Must contain at least one entry.

        Returns:
            Dict with 'time' and 'pressure' lists representing the average curve.
        """
        if len(datasets) == 1:
            return datasets[0]

        # Overlap region shared by all datasets
        min_t = max(min(d['time']) for d in datasets)
        max_t = min(max(d['time']) for d in datasets)
        n_pts = max(len(d['time']) for d in datasets)

        common_time = np.linspace(min_t, max_t, n_pts)

        all_pressures = [
            np.interp(common_time, d['time'], d['pressure'])
            for d in datasets
        ]
        avg_pressure = np.mean(all_pressures, axis=0)

        return {
            'time': common_time.tolist(),
            'pressure': avg_pressure.tolist()
        }
