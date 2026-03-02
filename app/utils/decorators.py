"""Shared route decorators for role-based access control."""
from functools import wraps
from flask import flash, redirect, url_for
from flask_login import current_user


def research_required(f):
    """Allow only admin and research_engineer roles."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if current_user.role not in ('admin', 'research_engineer'):
            flash('您没有权限访问此页面', 'danger')
            if current_user.role == 'lab_engineer':
                return redirect(url_for('simulation.history'))
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function


def lab_required(f):
    """Allow only admin and lab_engineer roles."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if current_user.role not in ('admin', 'lab_engineer'):
            flash('您没有权限访问此页面', 'danger')
            if current_user.role == 'research_engineer':
                return redirect(url_for('simulation.index'))
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function
