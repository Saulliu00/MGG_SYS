from flask import Blueprint, render_template, redirect, url_for, flash, request, session
from flask_login import login_user, logout_user, current_user, login_required
from urllib.parse import urlparse
from app import db
from app.models import User
from app.middleware import log_user_login, log_user_logout
from app.utils import log_manager
from datetime import date

bp = Blueprint('auth', __name__, url_prefix='/auth')

@bp.before_app_request
def check_daily_login():
    """Force re-login every day at midnight (local time)"""
    # Skip auth routes and static files to avoid redirect loops
    if request.endpoint and (
        request.endpoint.startswith('auth.') or
        request.endpoint == 'static'
    ):
        return
    if current_user.is_authenticated:
        login_date = session.get('login_date')
        today = date.today().isoformat()
        if login_date != today:
            logout_user()
            flash('新的一天，请重新登录', 'info')
            return redirect(url_for('auth.login'))

@bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))

    if request.method == 'POST':
        employee_id = request.form.get('employee_id')
        password = request.form.get('password')

        user = User.query.filter_by(employee_id=employee_id).first()

        if user and user.check_password(password) and user.is_active:
            login_user(user, remember=True)
            session['login_date'] = date.today().isoformat()
            # Log successful login
            log_user_login(
                username=user.username,
                user_id=user.id,
                ip_address=request.remote_addr,
                success=True
            )
            next_page = request.args.get('next')
            # Prevent open redirect: only allow relative URLs
            if next_page and urlparse(next_page).netloc:
                next_page = None
            return redirect(next_page if next_page else url_for('simulation.index'))
        else:
            # Log failed login attempt
            log_user_login(
                username=employee_id,
                user_id=None,
                ip_address=request.remote_addr,
                success=False
            )
            flash('工号或密码错误，或账户已被禁用', 'danger')

    return render_template('auth/login.html')

@bp.route('/logout')
def logout():
    # Log logout before clearing session
    if current_user.is_authenticated:
        log_user_logout(
            username=current_user.username,
            user_id=current_user.id,
            ip_address=request.remote_addr
        )
    logout_user()
    return redirect(url_for('auth.login'))

@bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))

    if request.method == 'POST':
        employee_id = request.form.get('employee_id')
        username = request.form.get('username', '').strip() or None
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')

        if password != confirm_password:
            flash('两次输入的密码不一致', 'danger')
            return render_template('auth/register.html')

        if User.query.filter_by(employee_id=employee_id).first():
            flash('工号已被注册', 'danger')
            return render_template('auth/register.html')

        new_user = User(employee_id=employee_id, username=username)
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()

        # Log user registration
        log_manager.log_info(
            message=f'New user registered: {employee_id}',
            action='user_registration',
            username=employee_id,
            user_id=new_user.id,
            ip_address=request.remote_addr
        )

        flash('注册成功！请登录', 'success')
        return redirect(url_for('auth.login'))

    return render_template('auth/register.html')

@bp.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    if request.method == 'POST':
        action = request.form.get('action')

        if action == 'update_info':
            username = request.form.get('username', '').strip() or None
            phone = request.form.get('phone', '').strip()
            current_user.username = username
            current_user.phone = phone
            db.session.commit()
            flash('个人信息已更新', 'success')

        elif action == 'change_password':
            current_password = request.form.get('current_password')
            new_password = request.form.get('new_password')
            confirm_password = request.form.get('confirm_password')

            if not current_user.check_password(current_password):
                flash('当前密码错误', 'danger')
            elif new_password != confirm_password:
                flash('两次输入的新密码不一致', 'danger')
            elif len(new_password) < 6:
                flash('新密码长度不能少于6位', 'danger')
            else:
                current_user.set_password(new_password)
                db.session.commit()
                flash('密码已修改成功', 'success')

        return redirect(url_for('auth.settings'))

    return render_template('auth/settings.html')
