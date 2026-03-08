import json
import os

from flask import Blueprint, render_template, request, jsonify, current_app, flash, redirect, url_for
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from app import db
from app.models import Simulation, TestResult
from app.utils.errors import (
    FileValidationError,
    SimulationError,
    SubprocessError,
    SubprocessTimeoutError,
    DataProcessingError
)
from app.middleware import log_simulation_run, log_file_upload
from app.utils.decorators import research_required, lab_required

bp = Blueprint('simulation', __name__, url_prefix='/simulation')

@bp.route('/')
@login_required
@research_required
def index():
    return render_template('simulation/index.html')

@bp.route('/reverse')
@login_required
@research_required
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

        # Log successful simulation
        log_simulation_run(
            username=current_user.username,
            user_id=current_user.id,
            simulation_params=data,
            success=True
        )

        return jsonify(result)

    except SubprocessTimeoutError as e:
        log_simulation_run(
            username=current_user.username,
            user_id=current_user.id,
            simulation_params=request.form.to_dict(),
            success=False,
            error=f'Timeout: {str(e)}'
        )
        return jsonify({
            'success': False,
            'message': str(e)
        })

    except (SimulationError, SubprocessError) as e:
        log_simulation_run(
            username=current_user.username,
            user_id=current_user.id,
            simulation_params=request.form.to_dict(),
            success=False,
            error=str(e)
        )
        return jsonify({
            'success': False,
            'message': str(e)
        })

    except Exception as e:
        current_app.logger.error('Unexpected simulation error: %s', e, exc_info=True)
        log_simulation_run(
            username=current_user.username,
            user_id=current_user.id,
            simulation_params=request.form.to_dict(),
            success=False,
            error=str(e)
        )
        return jsonify({
            'success': False,
            'message': '服务器内部错误，请稍后重试'
        }), 500

@bp.route('/upload', methods=['POST'])
@login_required
def upload_test_result():
    """Upload actual test result file (.xlsx)"""
    try:
        if 'file' not in request.files:
            return jsonify({'success': False, 'message': '没有上传文件'})

        file = request.files['file']
        simulation_id = request.form.get('simulation_id')
        work_order = request.form.get('work_order')
        
        # Capture recipe parameters from current form state (if available)
        recipe_params = {
            'ignition_model': request.form.get('ignition_model'),
            'nc_type_1': request.form.get('nc_type_1'),
            'nc_usage_1': request.form.get('nc_usage_1'),
            'nc_type_2': request.form.get('nc_type_2'),
            'nc_usage_2': request.form.get('nc_usage_2'),
            'gp_type': request.form.get('gp_type'),
            'gp_usage': request.form.get('gp_usage'),
            'shell_model': request.form.get('shell_model'),
            'current': request.form.get('current'),
            'sensor_model': request.form.get('sensor_model'),
            'body_model': request.form.get('body_model'),
        }
        
        result = current_app.file_service.process_test_result_upload(
            file, current_user.id, simulation_id=simulation_id, 
            work_order=work_order, recipe_params=recipe_params
        )

        # Log successful upload
        log_file_upload(
            username=current_user.username,
            user_id=current_user.id,
            filename=file.filename,
            file_size=len(file.read()) if hasattr(file, 'read') else 0,
            success=True
        )
        # Reset file pointer after reading size
        if hasattr(file, 'seek'):
            file.seek(0)

        return jsonify(result)

    except FileValidationError as e:
        log_file_upload(
            username=current_user.username,
            user_id=current_user.id,
            filename=request.files['file'].filename if 'file' in request.files else 'unknown',
            file_size=0,
            success=False,
            error=f'Validation error: {str(e)}'
        )
        return jsonify({'success': False, 'message': str(e)})

    except DataProcessingError as e:
        log_file_upload(
            username=current_user.username,
            user_id=current_user.id,
            filename=request.files['file'].filename if 'file' in request.files else 'unknown',
            file_size=0,
            success=False,
            error=f'Processing error: {str(e)}'
        )
        return jsonify({'success': False, 'message': str(e)})

    except Exception as e:
        current_app.logger.error('Unexpected file upload error: %s', e, exc_info=True)
        log_file_upload(
            username=current_user.username,
            user_id=current_user.id,
            filename=request.files['file'].filename if 'file' in request.files else 'unknown',
            file_size=0,
            success=False,
            error=str(e)
        )
        return jsonify({'success': False, 'message': '服务器内部错误，请稍后重试'}), 500

@bp.route('/history')
@login_required
@lab_required
def history():
    """View simulation history"""
    simulations = current_app.simulation_service.get_simulation_history(current_user.id)
    return render_template('simulation/history.html', simulations=simulations)

@bp.route('/experiment', methods=['POST'])
@login_required
@lab_required
def experiment():
    """Submit experiment data with batch file upload"""
    try:
        ticket_number = request.form.get('ticket_number', '').strip()

        files = request.files.getlist('files')
        if not files or all(f.filename == '' for f in files):
            return jsonify({'success': False, 'message': '请至少上传一个文件'})

        upload_folder = os.path.join(current_app.root_path, 'static', 'uploads', 'experiments')
        os.makedirs(upload_folder, exist_ok=True)

        # Resolve linked simulation via ticket_number (work order).
        # If no simulation exists for this work order, create a stub so the
        # work order appears in 工单查询.
        linked_sim_id = None
        if ticket_number:
            sim = (
                Simulation.query
                .filter_by(work_order=ticket_number)
                .order_by(Simulation.created_at.desc())
                .first()
            )
            if sim:
                linked_sim_id = sim.id
            else:
                stub = Simulation(user_id=current_user.id, work_order=ticket_number)
                db.session.add(stub)
                db.session.flush()
                linked_sim_id = stub.id

        saved_files = []
        for file in files:
            if file.filename == '':
                continue
            filename = secure_filename(file.filename)
            if ticket_number:
                filename = f"{ticket_number}_{filename}"
            filepath = os.path.join(upload_folder, filename)
            file.save(filepath)
            saved_files.append(filename)

            # Create TestResult DB record so 工单查询 can find this upload
            try:
                data_dict = current_app.file_service.file_handler.load_excel_data_as_dict(filepath)
                test_result = TestResult(
                    user_id=current_user.id,
                    simulation_id=linked_sim_id,
                    filename=filename,
                    file_path=filepath,
                    data=json.dumps(data_dict)
                )
                db.session.add(test_result)
            except Exception as parse_err:
                current_app.logger.warning('Could not parse experiment file %s: %s', filename, parse_err)

        db.session.commit()

        return jsonify({
            'success': True,
            'message': f'成功上传 {len(saved_files)} 个文件',
            'files': saved_files
        })

    except Exception as e:
        current_app.logger.error('Experiment submission error: %s', e, exc_info=True)
        return jsonify({'success': False, 'message': '服务器内部错误，请稍后重试'}), 500

@bp.route('/predict', methods=['POST'])
@login_required
def predict():
    """Run prediction"""
    try:
        data = request.get_json()
        nc_usage_1 = float(data.get('nc_usage_1', 0))

        result = current_app.simulation_service.run_prediction(nc_usage_1)
        return jsonify(result)

    except SubprocessTimeoutError as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

    except (SimulationError, SubprocessError) as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

    except Exception as e:
        current_app.logger.error('Unexpected prediction error: %s', e, exc_info=True)
        return jsonify({
            'success': False,
            'message': '服务器内部错误，请稍后重试'
        }), 500

@bp.route('/save_to_data_folder', methods=['POST'])
@login_required
def save_to_data_folder():
    """Save uploaded .xlsx file to demo/data folder with NC value naming"""
    try:
        if 'file' not in request.files:
            return jsonify({
                'success': False,
                'message': '没有上传文件'
            }), 400

        file = request.files['file']
        nc_value = request.form.get('nc_value')
        custom_name = request.form.get('custom_name', 'value')

        result = current_app.file_service.save_to_demo_data_folder(file, nc_value, custom_name)
        return jsonify(result)

    except FileValidationError as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 400

    except Exception as e:
        current_app.logger.error('Save to data folder error: %s', e, exc_info=True)
        return jsonify({
            'success': False,
            'message': '服务器内部错误，请稍后重试'
        }), 500


@bp.route('/load_test_data', methods=['POST'])
@login_required
def load_test_data():
    """Load test data from uploaded .xlsx file for comparison"""
    try:
        if 'file' not in request.files:
            return jsonify({
                'success': False,
                'message': '没有上传文件'
            }), 400

        file = request.files['file']
        result = current_app.file_service.load_test_data_file(file)
        return jsonify(result)

    except FileValidationError as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 400

    except SubprocessTimeoutError as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

    except SubprocessError as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

    except Exception as e:
        current_app.logger.error('Load test data error: %s', e, exc_info=True)
        return jsonify({
            'success': False,
            'message': '服务器内部错误，请稍后重试'
        }), 500


@bp.route('/validate_upload', methods=['POST'])
@login_required
def validate_upload():
    """Validate an uploaded test-data file without persisting it to the database."""
    try:
        if 'file' not in request.files:
            return jsonify({'valid': False, 'errors': ['未收到文件']})

        file = request.files['file']
        result = current_app.file_service.validate_upload_file(file)
        return jsonify(result)

    except Exception as e:
        current_app.logger.error('File validation error: %s', e, exc_info=True)
        return jsonify({'valid': False, 'errors': ['服务器内部错误，请稍后重试']}), 500


@bp.route('/fetch_recipe_test_data', methods=['POST'])
@login_required
def fetch_recipe_test_data():
    """Find and return averaged test data matching the current recipe parameters."""
    try:
        params = request.get_json()
        result = current_app.simulation_service.find_and_average_recipe_test_data(
            current_user.id, params
        )
        return jsonify(result)

    except Exception as e:
        current_app.logger.error('Error fetching recipe test data: %s', e, exc_info=True)
        return jsonify({'found': False, 'message': '服务器内部错误，请稍后重试'}), 500


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
            'message': str(e)
        }), 400

    except Exception as e:
        current_app.logger.error('Comparison chart generation error: %s', e, exc_info=True)
        return jsonify({
            'success': False,
            'message': '服务器内部错误，请稍后重试'
        }), 500
