from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, current_user
from app import db
from app.models import User
from app.middleware import log_user_login, log_user_logout
from app.utils import log_manager

bp = Blueprint('auth', __name__, url_prefix='/auth')

@bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))

    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        user = User.query.filter_by(username=username).first()

        if user and user.check_password(password) and user.is_active:
            login_user(user, remember=True)
            # Log successful login
            log_user_login(
                username=user.username,
                user_id=user.id,
                ip_address=request.remote_addr,
                success=True
            )
            next_page = request.args.get('next')
            return redirect(next_page if next_page else url_for('simulation.index'))
        else:
            # Log failed login attempt
            log_user_login(
                username=username,
                user_id=None,
                ip_address=request.remote_addr,
                success=False
            )
            flash('用户名或密码错误，或账户已被禁用', 'danger')

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
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')

        if password != confirm_password:
            flash('两次输入的密码不一致', 'danger')
            return render_template('auth/register.html')

        if User.query.filter_by(username=username).first():
            flash('用户名已存在', 'danger')
            return render_template('auth/register.html')

        if User.query.filter_by(email=email).first():
            flash('邮箱已被注册', 'danger')
            return render_template('auth/register.html')

        new_user = User(username=username, email=email)
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()

        # Log user registration
        log_manager.log_info(
            message=f'New user registered: {username}',
            action='user_registration',
            username=username,
            user_id=new_user.id,
            ip_address=request.remote_addr
        )

        flash('注册成功！请登录', 'success')
        return redirect(url_for('auth.login'))

    return render_template('auth/register.html')
