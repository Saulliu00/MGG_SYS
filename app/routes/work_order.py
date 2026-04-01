"""Routes for 工单查询 (Work Order Query) — research_engineer access only."""
import re

from flask import Blueprint, render_template, jsonify, current_app
from flask_login import login_required, current_user
from app.utils.decorators import research_required

_WO_RE = re.compile(r'^[\w\-]{1,100}$')


def _valid_work_order(wo: str) -> bool:
    """Return True if the work_order string is safe for use in queries."""
    return bool(wo and _WO_RE.match(wo))

wp = Blueprint('wp', __name__, url_prefix='/work_order')


@wp.route('/')
@login_required
@research_required
def index():
    return render_template('work_order/index.html')


@wp.route('/list')
@login_required
@research_required
def list_work_orders():
    """Return all work orders as JSON for the left panel."""
    try:
        work_orders = current_app.work_order_service.get_all_work_orders()
        return jsonify({'success': True, 'work_orders': work_orders})
    except Exception as e:
        current_app.logger.error('Error listing work orders: %s', e, exc_info=True)
        return jsonify({'success': False, 'message': '服务器内部错误'}), 500


@wp.route('/<work_order>/recipe')
@login_required
@research_required
def work_order_recipe(work_order):
    """Return recipe fields for a work order — used by 逆向 page to pre-fill inputs."""
    if not _valid_work_order(work_order):
        return jsonify({'success': False, 'message': '无效的工单号'}), 400
    try:
        data = current_app.work_order_service.get_work_order_recipe(work_order)
        return jsonify({'success': True, **data})
    except Exception as e:
        current_app.logger.error('Error fetching recipe for work order %s: %s', work_order, e, exc_info=True)
        return jsonify({'success': False, 'message': '服务器内部错误'}), 500


@wp.route('/<work_order>/detail')
@login_required
@research_required
def work_order_detail(work_order):
    """Return combined payload: test results, chart, statistics."""
    if not _valid_work_order(work_order):
        return jsonify({'success': False, 'message': '无效的工单号'}), 400
    try:
        detail = current_app.work_order_service.get_work_order_detail(work_order)
        if not detail.get('found'):
            return jsonify({'success': False, 'message': '工单不存在'}), 404
        return jsonify({'success': True, **detail})
    except Exception as e:
        current_app.logger.error('Error fetching work order detail: %s', e, exc_info=True)
        return jsonify({'success': False, 'message': '服务器内部错误'}), 500


@wp.route('/test_result/<int:result_id>', methods=['DELETE'])
@login_required
@research_required
def delete_test_result(result_id):
    """Delete a test result — admin can delete any; others only their own."""
    try:
        result = current_app.work_order_service.delete_test_result(
            result_id, current_user.id, is_admin=(current_user.role == 'admin')
        )
        return jsonify(result)
    except Exception as e:
        current_app.logger.error('Error deleting test result %s: %s', result_id, e, exc_info=True)
        return jsonify({'success': False, 'message': '服务器内部错误'}), 500


@wp.route('/<work_order>', methods=['DELETE'])
@login_required
@research_required
def delete_work_order(work_order):
    """Delete a work order and all its linked data — admin or creator only."""
    if not _valid_work_order(work_order):
        return jsonify({'success': False, 'message': '无效的工单号'}), 400
    try:
        result = current_app.work_order_service.delete_work_order(
            work_order, current_user.id, is_admin=(current_user.role == 'admin')
        )
        return jsonify(result)
    except Exception as e:
        current_app.logger.error('Error deleting work order %s: %s', work_order, e, exc_info=True)
        return jsonify({'success': False, 'message': '服务器内部错误'}), 500
