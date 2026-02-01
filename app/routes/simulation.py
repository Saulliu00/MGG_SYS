from flask import Blueprint, render_template, request, jsonify, current_app
from flask_login import login_required, current_user
from app.utils.errors import (
    FileValidationError,
    SimulationError,
    SubprocessError,
    SubprocessTimeoutError,
    DataProcessingError
)

bp = Blueprint('simulation', __name__, url_prefix='/simulation')

@bp.route('/')
@login_required
def index():
    return render_template('simulation/index.html')

@bp.route('/reverse')
@login_required
def reverse():
    """Reverse simulation page"""
    return render_template('simulation/reverse.html')

@bp.route('/run', methods=['POST'])
@login_required
def run_simulation():
    """Run simulation with provided parameters"""
    try:
        data = request.form.to_dict()
        result = current_app.simulation_service.run_forward_simulation(current_user.id, data)
        return jsonify(result)

    except SubprocessTimeoutError as e:
        return jsonify({
            'success': False,
            'message': str(e)
        })

    except (SimulationError, SubprocessError) as e:
        return jsonify({
            'success': False,
            'message': str(e)
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error running simulation: {str(e)}'
        })

@bp.route('/upload', methods=['POST'])
@login_required
def upload_test_result():
    """Upload actual test result file (.xlsx)"""
    try:
        if 'file' not in request.files:
            return jsonify({'success': False, 'message': '没有上传文件'})

        file = request.files['file']
        result = current_app.file_service.process_test_result_upload(file, current_user.id)
        return jsonify(result)

    except FileValidationError as e:
        return jsonify({'success': False, 'message': str(e)})

    except DataProcessingError as e:
        return jsonify({'success': False, 'message': str(e)})

    except Exception as e:
        return jsonify({'success': False, 'message': f'文件处理错误: {str(e)}'})

@bp.route('/history')
@login_required
def history():
    """View simulation history"""
    simulations = current_app.simulation_service.get_simulation_history(current_user.id)
    return render_template('simulation/history.html', simulations=simulations)

@bp.route('/predict', methods=['POST'])
def predict():
    """Run prediction for demo (no authentication required)"""
    try:
        data = request.get_json()
        nc_usage_1 = float(data.get('nc_usage_1', 0))

        result = current_app.simulation_service.run_prediction(nc_usage_1)
        return jsonify(result)

    except SubprocessTimeoutError as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

    except (SimulationError, SubprocessError) as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Error running simulation: {str(e)}'
        }), 500

@bp.route('/save_to_data_folder', methods=['POST'])
def save_to_data_folder():
    """Save uploaded .xlsx file to demo/data folder with NC value naming (no authentication required)"""
    try:
        if 'file' not in request.files:
            return jsonify({
                'success': False,
                'error': '没有上传文件'
            }), 400

        file = request.files['file']
        nc_value = request.form.get('nc_value')
        custom_name = request.form.get('custom_name', 'value')

        result = current_app.file_service.save_to_demo_data_folder(file, nc_value, custom_name)
        return jsonify(result)

    except FileValidationError as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400

    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'保存文件失败: {str(e)}'
        }), 500


@bp.route('/load_test_data', methods=['POST'])
def load_test_data():
    """Load test data from uploaded .xlsx file for comparison (no authentication required)"""
    try:
        if 'file' not in request.files:
            return jsonify({
                'success': False,
                'error': '没有上传文件'
            }), 400

        file = request.files['file']
        result = current_app.file_service.load_test_data_file(file)
        return jsonify(result)

    except FileValidationError as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400

    except SubprocessTimeoutError as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

    except SubprocessError as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Error loading test data: {str(e)}'
        }), 500


@bp.route('/generate_comparison_chart', methods=['POST'])
@login_required
def generate_comparison_chart():
    """Generate comparison chart for simulation vs test data"""
    try:
        data = request.get_json()
        simulation_data = data.get('simulation_data')
        test_data = data.get('test_data')

        # Generate chart using comparison service
        chart_figure = current_app.comparison_service.generate_comparison_chart(
            simulation_data=simulation_data,
            test_data=test_data
        )

        return jsonify({
            'success': True,
            'chart': chart_figure
        })

    except DataProcessingError as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400

    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Error generating comparison chart: {str(e)}'
        }), 500
