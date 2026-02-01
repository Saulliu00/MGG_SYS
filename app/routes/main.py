from flask import Blueprint, render_template, redirect, url_for
from flask_login import login_required, current_user

bp = Blueprint('main', __name__)

@bp.route('/')
def index():
    # Redirect to login if not authenticated, otherwise to simulation page
    if not current_user.is_authenticated:
        return redirect(url_for('auth.login'))
    return redirect(url_for('simulation.index'))
