"""Plotting utilities for generating Plotly charts"""
import plotly.graph_objects as go
from typing import List, Dict, Optional
from app.config.plot_config import (
    DEFAULT_LAYOUT,
    AXIS_CONFIG,
    LEGEND_CONFIG,
    PLACEHOLDER_CONFIG,
    PLOT_PRESETS
)


class Plotter:
    """Handles generation of Plotly charts for the application"""

    @staticmethod
    def create_simulation_chart(time_data: List[float], pressure_data: List[float]) -> Dict:
        """
        Create a simulation chart with time vs pressure data.

        Args:
            time_data: List of time points (x-axis)
            pressure_data: List of pressure values (y-axis)

        Returns:
            Dict: Plotly figure as JSON-serializable dict
        """
        # Create trace
        trace = go.Scatter(
            x=time_data,
            y=pressure_data,
            mode=PLOT_PRESETS['simulation_chart']['mode'],
            name=PLOT_PRESETS['simulation_chart']['name'],
            line=PLOT_PRESETS['simulation_chart']['line']
        )

        # Create layout
        layout = go.Layout(
            **DEFAULT_LAYOUT,
            xaxis=AXIS_CONFIG['xaxis'],
            yaxis=AXIS_CONFIG['yaxis']
        )

        # Create figure
        fig = go.Figure(data=[trace], layout=layout)

        # Return as JSON-serializable dict
        return fig.to_dict()

    @staticmethod
    def create_comparison_chart(
        simulation_data: Optional[Dict] = None,
        test_data: Optional[Dict] = None
    ) -> Dict:
        """
        Create a comparison chart overlaying simulation and test data.

        Args:
            simulation_data: Dict with 'time' and 'pressure' keys (optional)
            test_data: Dict with 'time' and 'pressure' keys (optional)

        Returns:
            Dict: Plotly figure as JSON-serializable dict
        """
        traces = []

        # Add simulation trace if provided
        if simulation_data and simulation_data.get('time') and simulation_data.get('pressure'):
            simulation_trace = go.Scatter(
                x=simulation_data['time'],
                y=simulation_data['pressure'],
                mode=PLOT_PRESETS['simulation_chart']['mode'],
                name=PLOT_PRESETS['simulation_chart']['name'],
                line=PLOT_PRESETS['simulation_chart']['line']
            )
            traces.append(simulation_trace)

        # Add test trace if provided
        if test_data and test_data.get('time') and test_data.get('pressure'):
            test_trace = go.Scatter(
                x=test_data['time'],
                y=test_data['pressure'],
                mode=PLOT_PRESETS['test_chart']['mode'],
                name=PLOT_PRESETS['test_chart']['name'],
                line=PLOT_PRESETS['test_chart']['line']
            )
            traces.append(test_trace)

        # Create layout with legend if we have multiple traces
        layout_config = {**DEFAULT_LAYOUT}
        layout_config.update({
            'xaxis': AXIS_CONFIG['xaxis'],
            'yaxis': AXIS_CONFIG['yaxis']
        })

        if len(traces) > 1:
            layout_config['legend'] = LEGEND_CONFIG

        # If no data, show placeholder
        if not traces:
            layout_config['annotations'] = [{
                'text': PLACEHOLDER_CONFIG['comparison']['text'],
                'xref': 'paper',
                'yref': 'paper',
                'x': 0.5,
                'y': 0.5,
                'showarrow': False,
                'font': PLACEHOLDER_CONFIG['comparison']['font']
            }]

        layout = go.Layout(**layout_config)
        fig = go.Figure(data=traces, layout=layout)

        return fig.to_dict()

    @staticmethod
    def create_empty_placeholder(chart_type: str = 'simulation') -> Dict:
        """
        Create an empty chart with a placeholder message.

        Args:
            chart_type: Type of chart ('simulation' or 'comparison')

        Returns:
            Dict: Plotly figure as JSON-serializable dict
        """
        placeholder_config = PLACEHOLDER_CONFIG.get(chart_type, PLACEHOLDER_CONFIG['simulation'])

        layout = go.Layout(
            **DEFAULT_LAYOUT,
            xaxis=AXIS_CONFIG['xaxis'],
            yaxis=AXIS_CONFIG['yaxis'],
            annotations=[{
                'text': placeholder_config['text'],
                'xref': 'paper',
                'yref': 'paper',
                'x': 0.5,
                'y': 0.5,
                'showarrow': False,
                'font': placeholder_config['font']
            }]
        )

        fig = go.Figure(data=[], layout=layout)
        return fig.to_dict()

    @staticmethod
    def extract_trace_data(plotly_figure: Dict) -> Dict:
        """
        Extract time and pressure arrays from a Plotly figure.

        Args:
            plotly_figure: Plotly figure as dict

        Returns:
            Dict with 'time' and 'pressure' keys
        """
        if not plotly_figure or not plotly_figure.get('data'):
            return {'time': [], 'pressure': []}

        # Extract from first trace
        first_trace = plotly_figure['data'][0]
        return {
            'time': first_trace.get('x', []),
            'pressure': first_trace.get('y', [])
        }

    @staticmethod
    def merge_layout_with_overrides(base_layout: Dict, overrides: Dict) -> Dict:
        """
        Merge a base layout with custom overrides.

        Args:
            base_layout: Base Plotly layout dict
            overrides: Custom overrides to apply

        Returns:
            Dict: Merged layout
        """
        merged = base_layout.copy()
        merged.update(overrides)
        return merged
