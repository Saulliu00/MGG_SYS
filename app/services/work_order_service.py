"""Work order service — browse, detail, statistics, and delete for 工单查询"""
import json
import os
import numpy as np
from typing import Dict, List

from app.models import Simulation, TestResult
from app.services.comparison_service import ComparisonService
from app.utils.plotter import Plotter


class WorkOrderService:
    """Service for the 工单查询 (work order query) feature."""

    def __init__(self, db):
        self.db = db

    def get_all_work_orders(self) -> List[Dict]:
        """
        Return all simulations that have a non-empty work_order, newest first.

        Returns:
            List of dicts: {work_order, simulation_id, owner_id, recipe_summary, created_at}
        """
        sims = (
            Simulation.query
            .filter(Simulation.work_order.isnot(None))
            .filter(Simulation.work_order != '')
            .order_by(Simulation.created_at.desc())
            .all()
        )
        result = []
        for s in sims:
            result.append({
                'work_order': s.work_order,
                'simulation_id': s.id,
                'owner_id': s.user_id,
                'recipe_summary': WorkOrderService._recipe_summary(s),
                'created_at': s.created_at.strftime('%Y-%m-%d %H:%M') if s.created_at else '',
            })
        return result

    def get_work_order_detail(self, work_order: str) -> Dict:
        """
        Find the simulation with the given work_order, load all linked TestResults,
        build a multi-run chart, and compute statistics.

        Returns:
            {
              'found': bool,
              'simulation': {id, work_order, recipe_summary, created_at},
              'test_results': [{id, user_id, filename, uploaded_at}],
              'chart': <Plotly dict>,
              'statistics': {count, peaks, mean_p, std_p, cv_p, mean_t, std_t, cv_t}
            }
        """
        sim = (
            Simulation.query
            .filter_by(work_order=work_order)
            .first()
        )
        if not sim:
            return {'found': False}

        test_results = TestResult.query.filter_by(simulation_id=sim.id).all()

        tr_list = []
        datasets = []
        labels = []

        for tr in test_results:
            tr_list.append({
                'id': tr.id,
                'user_id': tr.user_id,
                'filename': tr.filename,
                'uploaded_at': tr.uploaded_at.strftime('%Y-%m-%d %H:%M') if tr.uploaded_at else '',
            })
            if tr.data:
                try:
                    d = json.loads(tr.data)
                    if d.get('time') and d.get('pressure'):
                        datasets.append(d)
                        labels.append(tr.filename)
                except (json.JSONDecodeError, TypeError):
                    pass

        chart = Plotter.create_multi_run_chart(datasets, labels)
        statistics = self._compute_statistics(datasets, labels)

        return {
            'found': True,
            'simulation': {
                'id': sim.id,
                'work_order': sim.work_order,
                'recipe_summary': self._recipe_summary(sim),
                'created_at': sim.created_at.strftime('%Y-%m-%d %H:%M') if sim.created_at else '',
            },
            'test_results': tr_list,
            'chart': chart,
            'statistics': statistics,
        }

    def delete_test_result(self, test_result_id: int, user_id: int) -> Dict:
        """
        Delete a TestResult if it belongs to user_id.

        Returns:
            {'success': True} or {'success': False, 'message': str}
        """
        tr = self.db.session.get(TestResult, test_result_id)
        if not tr:
            return {'success': False, 'message': '记录不存在'}
        if tr.user_id != user_id:
            return {'success': False, 'message': '无权限删除他人数据'}

        # Remove physical file
        if tr.file_path and os.path.isfile(tr.file_path):
            try:
                os.remove(tr.file_path)
            except OSError:
                pass  # Non-fatal — still remove the DB record

        self.db.session.delete(tr)
        self.db.session.commit()
        return {'success': True}

    # ── private helpers ──────────────────────────────────────────────────────

    @staticmethod
    def _compute_statistics(datasets: List[Dict], labels: List[str]) -> Dict:
        """Compute per-run and aggregate statistics across all runs."""
        if not datasets:
            return {'count': 0, 'peaks': []}

        peaks = []
        for ds, label in zip(datasets, labels):
            peak_p, peak_t = ComparisonService.find_peak_pressure(
                ds['pressure'], ds['time']
            )
            peaks.append({
                'filename': label,
                'peak_pressure': round(peak_p, 3),
                'peak_time': round(peak_t, 3),
            })

        pressures = [p['peak_pressure'] for p in peaks]
        times = [p['peak_time'] for p in peaks]

        mean_p = float(np.mean(pressures))
        std_p = float(np.std(pressures, ddof=1)) if len(pressures) > 1 else 0.0
        cv_p = (std_p / mean_p * 100) if mean_p != 0 else 0.0

        mean_t = float(np.mean(times))
        std_t = float(np.std(times, ddof=1)) if len(times) > 1 else 0.0
        cv_t = (std_t / mean_t * 100) if mean_t != 0 else 0.0

        return {
            'count': len(peaks),
            'peaks': peaks,
            'mean_p': round(mean_p, 3),
            'std_p': round(std_p, 3),
            'cv_p': round(cv_p, 2),
            'mean_t': round(mean_t, 3),
            'std_t': round(std_t, 3),
            'cv_t': round(cv_t, 2),
        }

    @staticmethod
    def _recipe_summary(sim: Simulation) -> str:
        parts = []
        if sim.ignition_model:
            parts.append(f'点火具:{sim.ignition_model}')
        if sim.nc_type_1:
            parts.append(f'NC1:{sim.nc_type_1}/{sim.nc_usage_1}mg')
        if sim.shell_model:
            parts.append(f'管壳:{sim.shell_model}mm')
        if sim.current:
            parts.append(f'通电:{sim.current}A')
        return ' · '.join(parts)
