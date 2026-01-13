"""
Load Test Data Script for PT Curve Comparison
This script reads .xlsx files containing test data and returns plot-ready JSON
"""

import pandas as pd
import plotly.graph_objects as go
import json
import sys
import os

def load_test_data(file_path):
    """Load test data from Excel file - skip first 4 rows, first column is x-axis, second column is y-axis"""
    try:
        # Read the Excel file, skipping the first 4 rows
        df = pd.read_excel(file_path, skiprows=4, header=None)

        # Check if file has at least 2 columns
        if len(df.columns) < 2:
            raise ValueError("Excel file must have at least 2 columns")

        # First column is x-axis (time), second column is y-axis (pressure)
        time_col = df.columns[0]
        pressure_col = df.columns[1]

        # Extract data and drop NaN values
        time = df[time_col].dropna().tolist()
        pressure = df[pressure_col].dropna().tolist()

        # Ensure same length
        min_len = min(len(time), len(pressure))
        time = time[:min_len]
        pressure = pressure[:min_len]

        return time, pressure

    except Exception as e:
        print(f"Error loading test data: {str(e)}", file=sys.stderr)
        import traceback
        traceback.print_exc(file=sys.stderr)
        return None, None

def create_plotly_json(time, pressure, file_name):
    """Create Plotly JSON data for the test data curve"""
    try:
        fig = go.Figure()

        fig.add_trace(go.Scatter(
            x=time,
            y=pressure,
            mode='lines+markers',
            name=f'实际测试数据: {file_name}',
            line=dict(color='#e74c3c', width=2),
            marker=dict(size=4)
        ))

        fig.update_layout(
            xaxis_title='时间 (ms)',
            yaxis_title='压力 (MPa)',
            hovermode='x unified',
            template='plotly_white',
            showlegend=True,
            margin=dict(l=50, r=50, t=30, b=50)
        )

        return fig.to_json()

    except Exception as e:
        print(f"Error creating plot: {str(e)}", file=sys.stderr)
        return None

def main():
    """Main function to load test data"""
    try:
        if len(sys.argv) < 2:
            print("Usage: python load_test_data.py <file_path>", file=sys.stderr)
            sys.exit(1)

        file_path = sys.argv[1]

        if not os.path.exists(file_path):
            print(f"File not found: {file_path}", file=sys.stderr)
            sys.exit(1)

        # Load data from Excel
        time, pressure = load_test_data(file_path)
        if time is None or pressure is None:
            print("Failed to load test data", file=sys.stderr)
            sys.exit(1)

        # Calculate statistics
        peak_pressure = max(pressure)
        peak_time = time[pressure.index(peak_pressure)]
        avg_pressure = sum(pressure) / len(pressure)

        # Get file name
        file_name = os.path.basename(file_path)

        # Create plot JSON
        plot_json = create_plotly_json(time, pressure, file_name)
        if plot_json is None:
            print("Failed to create plot", file=sys.stderr)
            sys.exit(1)

        # Prepare response
        response = {
            'success': True,
            'plot_data': json.loads(plot_json),
            'statistics': {
                'peak_pressure': float(peak_pressure),
                'peak_time': float(peak_time),
                'avg_pressure': float(avg_pressure),
                'num_points': len(time),
                'file_name': file_name
            },
            'data': {
                'time': time,
                'pressure': pressure
            }
        }

        print(json.dumps(response))

    except Exception as e:
        error_response = {
            'success': False,
            'error': str(e)
        }
        print(json.dumps(error_response), file=sys.stderr)
        sys.exit(1)

if __name__ == '__main__':
    main()
