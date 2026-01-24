from flask import Blueprint, render_template, request, jsonify, send_file
from flask_login import login_required, current_user
from app import db
from app.models import Simulation, TestResult
import json
import os
from werkzeug.utils import secure_filename
import pandas as pd
import subprocess
import sys

bp = Blueprint('simulation', __name__, url_prefix='/simulation')

@bp.route('/')
@login_required
def index():
    return render_template('simulation/index.html')

@bp.route('/run', methods=['POST'])
@login_required
def run_simulation():
    """Run simulation with provided parameters"""
    data = request.form.to_dict()

    # Create new simulation record
    simulation = Simulation(
        user_id=current_user.id,
        ignition_model=data.get('ignition_model'),
        nc_type_1=data.get('nc_type_1'),
        nc_usage_1=float(data.get('nc_usage_1', 0)),
        nc_type_2=data.get('nc_type_2'),
        nc_usage_2=float(data.get('nc_usage_2', 0)),
        gp_type=data.get('gp_type'),
        gp_usage=float(data.get('gp_usage', 0)),
        shell_model=data.get('shell_model'),
        current=float(data.get('current', 0)),
        sensor_model=data.get('sensor_model'),
        body_model=data.get('body_model'),
        equipment=data.get('equipment'),
        test_operator=data.get('test_operator'),
        test_name=data.get('test_name'),
        notes=data.get('notes')
    )

    # Run actual Python simulation script
    try:
        nc_usage_1 = float(data.get('nc_usage_1', 0))

        # Get project root directory
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        models_path = os.path.join(project_root, 'models')
        script_path = os.path.join(project_root, 'demo', 'run_simulation.py')

        # Call the Python simulation script
        result = subprocess.run(
            [sys.executable, script_path, str(nc_usage_1), models_path],
            capture_output=True,
            text=True,
            timeout=30
        )

        if result.returncode == 0:
            # Parse the JSON output from the script
            response_data = json.loads(result.stdout)

            if response_data.get('success'):
                result_data = {
                    'plot_data': response_data['plot_data'],
                    'statistics': response_data['statistics']
                }
            else:
                # Script returned an error
                return jsonify({
                    'success': False,
                    'message': f"Simulation error: {response_data.get('error', 'Unknown error')}"
                })
        else:
            # Script execution failed
            return jsonify({
                'success': False,
                'message': f"Script execution failed: {result.stderr}"
            })

    except subprocess.TimeoutExpired:
        return jsonify({
            'success': False,
            'message': 'Simulation timeout (exceeded 30 seconds)'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error running simulation: {str(e)}'
        })

    simulation.result_data = json.dumps(result_data)
    db.session.add(simulation)
    db.session.commit()

    return jsonify({
        'success': True,
        'simulation_id': simulation.id,
        'data': result_data
    })

@bp.route('/upload', methods=['POST'])
@login_required
def upload_test_result():
    """Upload actual test result file (.xlsx)"""
    if 'file' not in request.files:
        return jsonify({'success': False, 'message': '没有上传文件'})

    file = request.files['file']
    if file.filename == '':
        return jsonify({'success': False, 'message': '文件名为空'})

    if file and file.filename.endswith('.xlsx'):
        filename = secure_filename(file.filename)
        filepath = os.path.join('app/static/uploads', filename)
        file.save(filepath)

        # Read Excel file
        try:
            df = pd.read_excel(filepath)
            # Assume columns are 'Time' and 'Pressure'
            data = {
                'time': df.iloc[:, 0].tolist(),
                'pressure': df.iloc[:, 1].tolist()
            }

            test_result = TestResult(
                user_id=current_user.id,
                filename=filename,
                file_path=filepath,
                data=json.dumps(data)
            )
            db.session.add(test_result)
            db.session.commit()

            return jsonify({
                'success': True,
                'test_result_id': test_result.id,
                'data': data
            })
        except Exception as e:
            return jsonify({'success': False, 'message': f'文件解析错误: {str(e)}'})

    return jsonify({'success': False, 'message': '仅支持 .xlsx 格式文件'})

@bp.route('/history')
@login_required
def history():
    """View simulation history"""
    simulations = Simulation.query.filter_by(user_id=current_user.id).order_by(Simulation.created_at.desc()).all()
    return render_template('simulation/history.html', simulations=simulations)

@bp.route('/predict', methods=['POST'])
def predict():
    """Run prediction for demo (no authentication required)"""
    try:
        # Get NC用量1 from request
        data = request.get_json()
        nc_usage_1 = float(data.get('nc_usage_1', 0))

        # Get project root directory
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        models_path = os.path.join(project_root, 'models')
        script_path = os.path.join(project_root, 'demo', 'run_simulation.py')

        # Call the Python simulation script
        result = subprocess.run(
            [sys.executable, script_path, str(nc_usage_1), models_path],
            capture_output=True,
            text=True,
            timeout=30
        )

        if result.returncode == 0:
            # Parse the JSON output from the script
            response_data = json.loads(result.stdout)
            return jsonify(response_data)
        else:
            # Script execution failed
            return jsonify({
                'success': False,
                'error': f"Script execution failed: {result.stderr}"
            }), 500

    except subprocess.TimeoutExpired:
        return jsonify({
            'success': False,
            'error': 'Simulation timeout (exceeded 30 seconds)'
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
        # Check if file was uploaded
        if 'file' not in request.files:
            return jsonify({
                'success': False,
                'error': '没有上传文件'
            }), 400

        file = request.files['file']
        if file.filename == '':
            return jsonify({
                'success': False,
                'error': '文件名为空'
            }), 400

        if not file.filename.endswith('.xlsx'):
            return jsonify({
                'success': False,
                'error': '仅支持 .xlsx 格式文件'
            }), 400

        # Get NC value and custom filename from request
        nc_value = request.form.get('nc_value')
        custom_name = request.form.get('custom_name', 'value')

        if not nc_value:
            return jsonify({
                'success': False,
                'error': 'NC用量1值未提供'
            }), 400

        # Create filename: {nc_value}_{custom_name}.xlsx
        new_filename = f"{nc_value}_{custom_name}.xlsx"

        # Save to demo/data folder
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        data_dir = os.path.join(project_root, 'demo', 'data')
        os.makedirs(data_dir, exist_ok=True)

        file_path = os.path.join(data_dir, new_filename)
        file.save(file_path)

        return jsonify({
            'success': True,
            'filename': new_filename,
            'message': f'文件已保存到 demo/data/{new_filename}'
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'保存文件失败: {str(e)}'
        }), 500


@bp.route('/load_test_data', methods=['POST'])
def load_test_data():
    """Load test data from uploaded .xlsx file for comparison (no authentication required)"""
    try:
        # Check if file was uploaded
        if 'file' not in request.files:
            return jsonify({
                'success': False,
                'error': '没有上传文件'
            }), 400

        file = request.files['file']
        if file.filename == '':
            return jsonify({
                'success': False,
                'error': '文件名为空'
            }), 400

        if not file.filename.endswith('.xlsx'):
            return jsonify({
                'success': False,
                'error': '仅支持 .xlsx 格式文件'
            }), 400

        # Save file temporarily
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        temp_dir = os.path.join(project_root, 'demo', 'temp')
        os.makedirs(temp_dir, exist_ok=True)

        filename = secure_filename(file.filename)
        temp_path = os.path.join(temp_dir, filename)
        file.save(temp_path)

        # Call the Python script to load and process the test data
        script_path = os.path.join(project_root, 'demo', 'load_test_data.py')

        result = subprocess.run(
            [sys.executable, script_path, temp_path],
            capture_output=True,
            text=True,
            timeout=30
        )

        # Clean up temp file
        try:
            os.remove(temp_path)
        except:
            pass

        if result.returncode == 0:
            # Parse the JSON output from the script
            response_data = json.loads(result.stdout)
            return jsonify(response_data)
        else:
            # Script execution failed
            return jsonify({
                'success': False,
                'error': f"Failed to process file: {result.stderr}"
            }), 500

    except subprocess.TimeoutExpired:
        return jsonify({
            'success': False,
            'error': 'File processing timeout (exceeded 30 seconds)'
        }), 500
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Error loading test data: {str(e)}'
        }), 500
