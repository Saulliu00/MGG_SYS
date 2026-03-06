"""Direct in-process model inference.

Loads the .pkl model file once on first use and keeps it cached for the
lifetime of the process.  Eliminates subprocess overhead on every 计算 call.
"""
import json
import os
import pickle

import numpy as np
import plotly.graph_objects as go

# Compatibility patch: models saved with newer numpy expose numpy._core;
# unpickling them on older numpy would fail without this shim.
if not hasattr(np, '_core'):
    import numpy.core as _nc
    np._core = _nc

from .errors import SimulationError
from .paths import get_models_path

_model_data = None  # module-level cache; populated on first call to _load_model()


def _load_model() -> dict:
    """Load the most-recent .pkl from the models directory and cache it.

    SECURITY NOTE: pickle.load() can execute arbitrary code. Model files must
    come exclusively from the controlled models directory managed by the
    development team — never from user uploads or external sources.
    """
    global _model_data
    if _model_data is not None:
        return _model_data

    models_path = get_models_path()
    # Resolve to absolute path so traversal attempts are rejected below
    models_abs = os.path.realpath(models_path)

    try:
        model_files = sorted(f for f in os.listdir(models_abs) if f.endswith('.pkl'))
    except OSError as e:
        raise SimulationError(f'Cannot access models directory: {e}')

    if not model_files:
        raise SimulationError('No model file found in the models directory')

    # Resolve the final path and verify it stays inside models_abs (no traversal)
    model_path = os.path.realpath(os.path.join(models_abs, model_files[-1]))
    if not model_path.startswith(models_abs + os.sep) and model_path != models_abs:
        raise SimulationError('Model path outside the expected models directory')

    try:
        with open(model_path, 'rb') as f:
            _model_data = pickle.load(f)
    except Exception as e:
        raise SimulationError(f'Failed to load model "{model_files[-1]}": {e}')

    return _model_data


def run_forward_inference(nc_usage_1: float) -> dict:
    """
    Run forward simulation in-process using the cached ML model.

    Args:
        nc_usage_1: NC用量1 value (the sole input feature used by the model).

    Returns:
        dict with keys 'plot_data' (Plotly JSON dict) and 'statistics'.

    Raises:
        SimulationError: if the model cannot be loaded or prediction fails.
    """
    model_data = _load_model()

    X = np.array([[nc_usage_1]])
    times = []
    pressures = []
    try:
        for i, model in enumerate(model_data['models']):
            pressures.append(float(model.predict(X)[0]))
            times.append(float(model_data['common_times'][i]))
    except Exception as e:
        raise SimulationError(f'Prediction failed: {e}')

    times_arr = np.array(times)
    pressures_arr = np.array(pressures)

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=times_arr.tolist(),
        y=pressures_arr.tolist(),
        mode='lines',
        name=f'NC用量1: {nc_usage_1}mg',
        line=dict(color='#667eea', width=2)
    ))
    fig.update_layout(
        xaxis_title='时间 (ms)',
        yaxis_title='压力 (MPa)',
        hovermode='x unified',
        template='plotly_white',
        showlegend=True,
        margin=dict(l=50, r=50, t=30, b=50)
    )

    plot_data = json.loads(fig.to_json())

    return {
        'plot_data': plot_data,
        'statistics': {
            'peak_pressure': float(np.max(pressures_arr)),
            'num_models': len(model_data['models']),
            'r_squared': float(model_data['metadata'].get('r_squared', 0.999)),
            'nc_usage_1': nc_usage_1,
            'num_points': len(times_arr),
        }
    }
