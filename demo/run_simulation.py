"""
Simulation Script for Forward Prediction
This script loads the trained models and generates PT curve predictions
"""

import pickle
import numpy as np
import plotly.graph_objects as go
import json
import sys
import os

# Add numpy._core compatibility for older model files
if not hasattr(np, '_core'):
    import numpy.core as _core
    np._core = _core

def load_models(models_path):
    """
    Load the trained models from the models folder

    Args:
        models_path: Path to the models folder

    Returns:
        Dictionary containing models and metadata
    """
    try:
        # Find the latest model file in the models folder
        model_files = [f for f in os.listdir(models_path) if f.endswith('.pkl')]

        if not model_files:
            return None

        # Get the most recent model file
        latest_model = sorted(model_files)[-1]
        model_path = os.path.join(models_path, latest_model)

        with open(model_path, 'rb') as f:
            model_data = pickle.load(f)

        return model_data

    except Exception as e:
        print(f"Error loading models: {str(e)}", file=sys.stderr)
        return None


def predict_pt_curve(model_data, nc_usage_1):
    """
    Predict PT curve for given NC usage value

    Args:
        model_data: Dictionary containing models and metadata
        nc_usage_1: NC用量1 value (feature input)

    Returns:
        times: Array of time points
        pressures: Array of predicted pressure values
    """
    try:
        # Create input array with the feature value
        X_input = np.array([[nc_usage_1]])

        predictions = []
        times = []

        # Iterate through all models (each represents one time point)
        for i, model in enumerate(model_data['models']):
            pred = model.predict(X_input)
            predictions.append(pred[0])
            times.append(model_data['common_times'][i])

        return np.array(times), np.array(predictions)

    except Exception as e:
        print(f"Error during prediction: {str(e)}", file=sys.stderr)
        return None, None


def create_plotly_json(times, pressures, nc_usage_1):
    """
    Create Plotly JSON data for the PT curve

    Args:
        times: Array of time points
        pressures: Array of pressure values
        nc_usage_1: NC用量1 value

    Returns:
        JSON string containing Plotly data and layout
    """
    try:
        # Create Plotly figure
        fig = go.Figure()

        # Add trace
        fig.add_trace(go.Scatter(
            x=times.tolist(),
            y=pressures.tolist(),
            mode='lines',
            name=f'NC用量1: {nc_usage_1}mg',
            line=dict(color='#667eea', width=2)
        ))

        # Update layout
        fig.update_layout(
            xaxis_title='时间 (ms)',
            yaxis_title='压力 (MPa)',
            hovermode='x unified',
            template='plotly_white',
            showlegend=True,
            margin=dict(l=50, r=50, t=30, b=50)
        )

        # Convert to JSON
        return fig.to_json()

    except Exception as e:
        print(f"Error creating plot: {str(e)}", file=sys.stderr)
        return None


def main():
    """
    Main function to run the simulation

    Expected command line arguments:
        sys.argv[1]: NC用量1 value
        sys.argv[2]: Path to models folder
    """
    try:
        # Parse command line arguments
        if len(sys.argv) < 3:
            print("Usage: python run_simulation.py <nc_usage_1> <models_path>", file=sys.stderr)
            sys.exit(1)

        nc_usage_1 = float(sys.argv[1])
        models_path = sys.argv[2]

        # Load models
        model_data = load_models(models_path)

        if model_data is None:
            print("Failed to load models", file=sys.stderr)
            sys.exit(1)

        # Predict PT curve
        times, pressures = predict_pt_curve(model_data, nc_usage_1)

        if times is None or pressures is None:
            print("Failed to generate predictions", file=sys.stderr)
            sys.exit(1)

        # Calculate statistics
        peak_pressure = np.max(pressures)
        num_models = len(model_data['models'])
        r_squared = model_data['metadata'].get('r_squared', 0.999)

        # Create Plotly JSON
        plot_json = create_plotly_json(times, pressures, nc_usage_1)

        if plot_json is None:
            print("Failed to create plot", file=sys.stderr)
            sys.exit(1)

        # Create response JSON
        response = {
            'success': True,
            'plot_data': json.loads(plot_json),
            'statistics': {
                'peak_pressure': float(peak_pressure),
                'num_models': num_models,
                'r_squared': float(r_squared),
                'nc_usage_1': nc_usage_1,
                'num_points': len(times)
            }
        }

        # Output JSON to stdout
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
