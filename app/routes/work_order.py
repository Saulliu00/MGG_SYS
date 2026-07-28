"""Routes for 工单查询 and 工单对比 — research_engineer access only."""
import re

from flask import Blueprint, render_template, jsonify, request, current_app
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


@wp.route('/<work_order>/curve')
@login_required
@research_required
def work_order_curve(work_order):
    """Return the averaged time/pressure arrays for a work order's test results."""
    if not _valid_work_order(work_order):
        return jsonify({'success': False, 'message': '无效的工单号'}), 400
    try:
        data = current_app.work_order_service.get_work_order_averaged_curve(work_order)
        return jsonify({'success': True, **data})
    except Exception as e:
        current_app.logger.error('work_order_curve error for %s: %s', work_order, e, exc_info=True)
        return jsonify({'success': False, 'message': '服务器内部错误'}), 500


@wp.route('/compare')
@login_required
@research_required
def compare_index():
    return render_template('work_order/compare.html')


@wp.route('/compare/options')
@login_required
@research_required
def compare_options():
    """Return distinct values for a comparison dimension that have test data."""
    dim = request.args.get('dim', 'work_order')
    _VALID_DIMS = {'work_order', 'nc_usage_1', 'gp_usage', 'shell_model', 'ignition_model'}
    if dim not in _VALID_DIMS:
        return jsonify({'success': False, 'message': '无效的对比维度'}), 400
    try:
        options = current_app.work_order_service.get_compare_options(dim)
        return jsonify({'success': True, 'options': options})
    except Exception as e:
        current_app.logger.error('compare_options error: %s', e, exc_info=True)
        return jsonify({'success': False, 'message': '服务器内部错误'}), 500


@wp.route('/compare/run', methods=['POST'])
@login_required
@research_required
def compare_run():
    """Run a multi-value comparison and return chart + stats table."""
    _VALID_DIMS = {'work_order', 'nc_usage_1', 'gp_usage', 'shell_model', 'ignition_model'}
    try:
        body = request.get_json()
        dimension = body.get('dimension', '')
        values = body.get('values', [])
        if dimension not in _VALID_DIMS:
            return jsonify({'success': False, 'message': '无效的对比维度'}), 400
        if not values or len(values) < 2:
            return jsonify({'success': False, 'message': '请至少选择两项进行对比'}), 400
        if len(values) > 8:
            return jsonify({'success': False, 'message': '最多同时对比8项'}), 400
        result = current_app.work_order_service.run_comparison(dimension, values)
        return jsonify({'success': True, **result})
    except Exception as e:
        current_app.logger.error('compare_run error: %s', e, exc_info=True)
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
