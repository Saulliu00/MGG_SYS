from flask import Blueprint, render_template, redirect, url_for, jsonify, current_app
from flask_login import login_required, current_user
import os

bp = Blueprint('main', __name__)

@bp.route('/')
def index():
    # Redirect to login if not authenticated, otherwise to role-appropriate page
    if not current_user.is_authenticated:
        return redirect(url_for('auth.login'))
    if current_user.role in ('admin', 'research_engineer'):
        return redirect(url_for('simulation.index'))
    else:
        return redirect(url_for('simulation.history'))

@bp.route('/health')
def health_check():
    """Health check endpoint for monitoring and load balancers"""
    from app.config.network_config import HEALTH_CHECK

    health_status = {
        'status': 'healthy',
        'checks': {}
    }

    # Check database connection
    if HEALTH_CHECK.get('check_database', True):
        try:
            from app import db
            from sqlalchemy import text
            # Simple query to check database connectivity
            db.session.execute(text('SELECT 1'))
            health_status['checks']['database'] = 'ok'
        except Exception as e:
            health_status['status'] = 'unhealthy'
            health_status['checks']['database'] = f'error: {str(e)}'

    # Check file system
    if HEALTH_CHECK.get('check_file_system', True):
        try:
            upload_folder = current_app.config.get('UPLOAD_FOLDER')
            if upload_folder and os.path.exists(upload_folder) and os.access(upload_folder, os.W_OK):
                health_status['checks']['file_system'] = 'ok'
            else:
                health_status['status'] = 'degraded'
                health_status['checks']['file_system'] = 'warning: upload folder not writable'
        except Exception as e:
            health_status['status'] = 'degraded'
            health_status['checks']['file_system'] = f'error: {str(e)}'

    # Return appropriate status code
    status_code = 200 if health_status['status'] == 'healthy' else 503

    return jsonify(health_status), status_code
