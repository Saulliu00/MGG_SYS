from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for, send_file
from flask_login import login_required, current_user
from functools import wraps
from app import db
from app.models import User
from app.utils import log_manager
from app.config.logging_config import ADMIN_LOG_VIEW

bp = Blueprint('admin', __name__, url_prefix='/admin')

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            flash('需要管理员权限才能访问此页面', 'danger')
            return redirect(url_for('main.index'))
        return f(*args, **kwargs)
    return decorated_function

@bp.route('/')
@login_required
@admin_required
def index():
    users = User.query.all()
    return render_template('admin/index.html', users=users)

@bp.route('/users')
@login_required
@admin_required
def users():
    users = User.query.all()
    return render_template('admin/users.html', users=users)

@bp.route('/user/add', methods=['POST'])
@login_required
@admin_required
def add_user():
    username = request.form.get('username')
    email = request.form.get('email')
    password = request.form.get('password')
    is_admin = request.form.get('is_admin') == 'on'

    if User.query.filter_by(username=username).first():
        return jsonify({'success': False, 'message': '用户名已存在'})

    if User.query.filter_by(email=email).first():
        return jsonify({'success': False, 'message': '邮箱已被注册'})

    new_user = User(username=username, email=email, is_admin=is_admin)
    new_user.set_password(password)
    db.session.add(new_user)
    db.session.commit()

    return jsonify({'success': True, 'message': '用户添加成功'})

@bp.route('/user/<int:user_id>/toggle', methods=['POST'])
@login_required
@admin_required
def toggle_user(user_id):
    user = User.query.get_or_404(user_id)

    if user.id == current_user.id:
        return jsonify({'success': False, 'message': '不能禁用自己的账户'})

    user.is_active = not user.is_active
    db.session.commit()

    status = '启用' if user.is_active else '禁用'
    return jsonify({'success': True, 'message': f'用户已{status}'})

@bp.route('/user/<int:user_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_user(user_id):
    user = User.query.get_or_404(user_id)

    if user.id == current_user.id:
        return jsonify({'success': False, 'message': '不能删除自己的账户'})

    db.session.delete(user)
    db.session.commit()

    return jsonify({'success': True, 'message': '用户已删除'})

@bp.route('/user/<int:user_id>/reset-password', methods=['POST'])
@login_required
@admin_required
def reset_password(user_id):
    user = User.query.get_or_404(user_id)
    new_password = request.form.get('new_password')

    user.set_password(new_password)
    db.session.commit()

    return jsonify({'success': True, 'message': '密码已重置'})

# ============================================================
# System Logs Routes
# ============================================================

@bp.route('/logs')
@login_required
@admin_required
def logs():
    """View system logs"""
    if not ADMIN_LOG_VIEW.get('enabled', True):
        flash('日志查看功能已禁用', 'warning')
        return redirect(url_for('admin.index'))

    # Get log file list
    log_files = log_manager.get_log_files()

    # Get statistics
    stats = log_manager.get_log_statistics()

    return render_template('admin/logs.html', log_files=log_files, stats=stats)

@bp.route('/logs/view')
@login_required
@admin_required
def view_log():
    """View specific log file contents"""
    filename = request.args.get('filename')
    max_rows = int(request.args.get('max_rows', ADMIN_LOG_VIEW.get('max_rows_display', 1000)))

    # Read log entries
    if filename:
        entries = log_manager.read_log_file(filename, max_rows=max_rows)
    else:
        entries = log_manager.read_log_file(max_rows=max_rows)

    return jsonify({
        'success': True,
        'filename': filename or log_manager.current_log_file,
        'entries': entries,
        'count': len(entries)
    })

@bp.route('/logs/download/<filename>')
@login_required
@admin_required
def download_log(filename):
    """Download a log file"""
    if not ADMIN_LOG_VIEW.get('download_enabled', True):
        flash('日志下载功能已禁用', 'warning')
        return redirect(url_for('admin.logs'))

    import os
    from app.config.logging_config import LOG_DIR

    filepath = os.path.join(LOG_DIR, filename)

    if not os.path.exists(filepath):
        flash('日志文件不存在', 'danger')
        return redirect(url_for('admin.logs'))

    return send_file(filepath, as_attachment=True, download_name=filename)

@bp.route('/logs/statistics')
@login_required
@admin_required
def log_statistics():
    """Get log statistics as JSON"""
    stats = log_manager.get_log_statistics()
    return jsonify({
        'success': True,
        'statistics': stats
    })
