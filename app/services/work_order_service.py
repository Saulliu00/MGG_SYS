"""Work order service — browse, detail, statistics, and delete for 工单查询"""
import json
import os
import numpy as np
from typing import Dict, List, Optional, Tuple

from app.models import Simulation, TestResult
from app.services.comparison_service import ComparisonService
from app.utils.plotter import Plotter


class WorkOrderService:
    """Service for the 工单查询 (work order query) feature."""

    def __init__(self, db):
        self.db = db

    def get_all_work_orders(self) -> List[Dict]:
        """
        Return one entry per unique work_order string, newest first.
        The earliest simulation for each work_order is treated as the owner.
        Each entry also includes mean_peak_pressure and mean_peak_time so
        the frontend can sort client-side without extra round trips.

        Returns:
            List of dicts: {work_order, simulation_id, owner_id, recipe_summary,
                            created_at, mean_peak_pressure, mean_peak_time}
        """
        sims = (
            Simulation.query
            .filter(Simulation.work_order.isnot(None))
            .filter(Simulation.work_order != '')
            .order_by(Simulation.created_at)  # oldest first so first-seen = owner
            .all()
        )
        if not sims:
            return []

        # Deduplicate: one entry per unique work_order; earliest sim is the owner
        seen: Dict[str, Simulation] = {}
        for s in sims:
            if s.work_order not in seen:
                seen[s.work_order] = s

        # Build work_order → [sim_ids] mapping (all sims, not just the owner)
        sim_id_to_wo: Dict[int, str] = {s.id: s.work_order for s in sims}
        wo_datasets: Dict[str, List] = {wo: [] for wo in seen}

        # Batch-load all test results in one query and group by work_order
        all_sim_ids = [s.id for s in sims]
        test_results = TestResult.query.filter(
            TestResult.simulation_id.in_(all_sim_ids)
        ).all()
        for tr in test_results:
            wo = sim_id_to_wo.get(tr.simulation_id)
            if wo and tr.data:
                try:
                    d = json.loads(tr.data)
                    if d.get('time') and d.get('pressure'):
                        wo_datasets[wo].append(d)
                except (json.JSONDecodeError, TypeError):
                    pass

        # Sort descending by created_at for default display order
        unique_sims = sorted(seen.values(), key=lambda x: x.created_at, reverse=True)
        return [
            {
                'work_order': s.work_order,
                'simulation_id': s.id,
                'owner_id': s.user_id,
                'recipe_summary': WorkOrderService._recipe_summary(s),
                'created_at': s.created_at.strftime('%Y-%m-%d %H:%M') if s.created_at else '',
                **WorkOrderService._compute_peak_summary(wo_datasets[s.work_order]),
            }
            for s in unique_sims
        ]

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
        sims = (
            Simulation.query
            .filter_by(work_order=work_order)
            .order_by(Simulation.created_at)
            .all()
        )
        if not sims:
            return {'found': False}

        sim = sims[0]  # earliest sim for display metadata
        sim_ids = [s.id for s in sims]
        test_results = TestResult.query.filter(
            TestResult.simulation_id.in_(sim_ids)
        ).all()

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

    def get_work_order_recipe(self, work_order: str) -> Dict:
        """
        Return the recipe fields from the earliest simulation for a given
        work order.  Used by the 逆向 page to pre-fill input parameters.

        Returns:
            {
              'found': bool,
              'ignition_model': str|None,   # 点火具
              'shell_model': str|None,       # 管壳高度
              'current': float|None,         # 通电条件
              'sensor_model': str|None,      # 传感器量程
              'body_model': str|None,        # 容积
              'equipment': str|None,         # 测试设备
            }
        """
        sim = (
            Simulation.query
            .filter_by(work_order=work_order)
            .order_by(Simulation.created_at)
            .first()
        )
        if not sim:
            return {'found': False}
        return {
            'found': True,
            # Test-condition fields → fill 输入参数 form selects
            'ignition_model': sim.ignition_model,
            'shell_model': sim.shell_model,
            'current': sim.current,
            'sensor_model': sim.sensor_model,
            'body_model': sim.body_model,
            'equipment': sim.equipment,
            # Recipe fields → populate 逆向预测结果 panel
            'nc_type_1': sim.nc_type_1,
            'nc_usage_1': sim.nc_usage_1,
            'nc_type_2': sim.nc_type_2,
            'nc_usage_2': sim.nc_usage_2,
            'gp_type': sim.gp_type,
            'gp_usage': sim.gp_usage,
        }

    def delete_test_result(self, test_result_id: int, user_id: int, is_admin: bool = False) -> Dict:
        """
        Delete a TestResult. Admin can delete any; others only their own.

        Returns:
            {'success': True} or {'success': False, 'message': str}
        """
        tr = self.db.session.get(TestResult, test_result_id)
        if not tr:
            return {'success': False, 'message': '记录不存在'}
        if not is_admin and tr.user_id != user_id:
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

    def delete_work_order(self, work_order: str, user_id: int, is_admin: bool = False) -> Dict:
        """
        Delete a work order and all its linked simulations and test results.
        Admin can delete any; others only work orders they created (earliest sim owner).

        Returns:
            {'success': True} or {'success': False, 'message': str}
        """
        sims = (
            Simulation.query
            .filter_by(work_order=work_order)
            .order_by(Simulation.created_at)
            .all()
        )
        if not sims:
            return {'success': False, 'message': '工单不存在'}

        # Permission: admin or creator of the earliest simulation
        if not is_admin and sims[0].user_id != user_id:
            return {'success': False, 'message': '无权限删除此工单'}

        sim_ids = [s.id for s in sims]
        test_results = TestResult.query.filter(
            TestResult.simulation_id.in_(sim_ids)
        ).all()

        for tr in test_results:
            # Admin deletes all test results; owner only deletes their own uploads
            if not is_admin and tr.user_id != user_id:
                continue
            if tr.file_path and os.path.isfile(tr.file_path):
                try:
                    os.remove(tr.file_path)
                except OSError:
                    pass
            self.db.session.delete(tr)

        for s in sims:
            self.db.session.delete(s)

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
    def _compute_peak_summary(datasets: List[Dict]) -> Dict:
        """
        Return mean_peak_pressure (MPa) and mean_peak_time (ms) across all
        datasets for one work order.  Both values are None when there is no
        test data.

        Returns:
            {'mean_peak_pressure': float|None, 'mean_peak_time': float|None}
        """
        if not datasets:
            return {'mean_peak_pressure': None, 'mean_peak_time': None}
        pressures, times = [], []
        for d in datasets:
            peak_p, peak_t = ComparisonService.find_peak_pressure(
                d['pressure'], d['time']
            )
            pressures.append(peak_p)
            times.append(peak_t)
        return {
            'mean_peak_pressure': round(float(np.mean(pressures)), 3),
            'mean_peak_time': round(float(np.mean(times)), 3),
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
