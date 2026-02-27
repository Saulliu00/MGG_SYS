"""Simulation service for handling simulation business logic"""
import json
from typing import Dict, List
from app.models import Simulation, TestResult
from app.utils.model_runner import run_forward_inference
from app.utils.errors import SimulationError
from app.services.comparison_service import ComparisonService


class SimulationService:
    """Service for managing simulation operations"""

    def __init__(self, db):
        """
        Initialize simulation service.

        Args:
            db: SQLAlchemy database instance
        """
        self.db = db

    def run_forward_simulation(self, user_id: int, params: Dict) -> Dict:
        """
        Run forward simulation with provided parameters.

        Args:
            user_id: ID of the user running the simulation
            params: Dictionary of simulation parameters

        Returns:
            Dict: Simulation results with simulation_id and data

        Raises:
            SimulationError: If simulation fails
            SubprocessTimeoutError: If simulation times out
        """
        try:
            # Extract NC usage value
            nc_usage_1 = float(params.get('nc_usage_1', 0))

            # Create new simulation record
            simulation = Simulation(
                user_id=user_id,
                ignition_model=params.get('ignition_model'),
                nc_type_1=params.get('nc_type_1'),
                nc_usage_1=nc_usage_1,
                nc_type_2=params.get('nc_type_2'),
                nc_usage_2=float(params.get('nc_usage_2', 0)),
                gp_type=params.get('gp_type'),
                gp_usage=float(params.get('gp_usage', 0)),
                shell_model=params.get('shell_model'),
                current=float(params.get('current', 0)),
                sensor_model=params.get('sensor_model'),
                body_model=params.get('body_model'),
                equipment=params.get('equipment'),
                employee_id=params.get('employee_id'),
                test_name=params.get('test_name'),
                notes=params.get('notes'),
                work_order=params.get('work_order')
            )

            # Run inference in-process using the loaded ML model
            response_data = run_forward_inference(nc_usage_1)

            # Save result to database
            simulation.result_data = json.dumps(response_data)
            self.db.session.add(simulation)
            self.db.session.commit()

            return {
                'success': True,
                'simulation_id': simulation.id,
                'data': response_data
            }

        except SimulationError:
            raise

        except Exception as e:
            raise SimulationError(f'Error running simulation: {str(e)}')

    def run_prediction(self, nc_usage_1: float) -> Dict:
        """
        Run quick prediction without authentication (for demo page).

        Args:
            nc_usage_1: NC usage value

        Returns:
            Dict: Prediction results

        Raises:
            SimulationError: If prediction fails
            SubprocessTimeoutError: If prediction times out
        """
        try:
            return run_forward_inference(nc_usage_1)

        except SimulationError:
            raise

        except Exception as e:
            raise SimulationError(f'Error running prediction: {str(e)}')

    def get_simulation_history(self, user_id: int, limit=50) -> List[Simulation]:
        """
        Retrieve user's simulation history.

        Args:
            user_id: ID of the user
            limit: Maximum number of records to return (default: 50)

        Returns:
            List[Simulation]: List of simulation records
        """
        return Simulation.query.filter_by(user_id=user_id)\
            .order_by(Simulation.created_at.desc())\
            .limit(limit)\
            .all()

    def get_simulation_by_id(self, simulation_id: int, user_id: int) -> Simulation:
        """
        Get a single simulation by ID.

        Args:
            simulation_id: ID of the simulation
            user_id: ID of the user (for authorization)

        Returns:
            Simulation: Simulation record

        Raises:
            SimulationError: If simulation not found or unauthorized
        """
        simulation = Simulation.query.filter_by(
            id=simulation_id,
            user_id=user_id
        ).first()

        if not simulation:
            raise SimulationError('Simulation not found or unauthorized')

        return simulation

    def get_simulation_results(self, simulation_id: int, user_id: int) -> Dict:
        """
        Get simulation results as a dictionary.

        Args:
            simulation_id: ID of the simulation
            user_id: ID of the user (for authorization)

        Returns:
            Dict: Simulation results

        Raises:
            SimulationError: If simulation not found or unauthorized
        """
        simulation = self.get_simulation_by_id(simulation_id, user_id)

        if not simulation.result_data:
            return {}

        try:
            return json.loads(simulation.result_data)
        except json.JSONDecodeError:
            return {}

    def find_and_average_recipe_test_data(self, user_id: int, params: Dict) -> Dict:
        """
        Find all test results whose parent simulation matches the given recipe
        parameters, then return an averaged time-series.

        Returns:
            {'found': True,  'data': {'time': [...], 'pressure': [...]}, 'count': N}
            {'found': False} if no matching test data exists.
        """
        # Build query for simulations that match the recipe
        query = Simulation.query.filter_by(user_id=user_id)

        # Numeric fields – compare as floats with a small tolerance
        numeric_fields = ('nc_usage_1', 'nc_usage_2', 'gp_usage', 'current')
        # String recipe fields (exclude metadata like employee_id, notes, work_order)
        string_fields = (
            'ignition_model', 'nc_type_1', 'nc_type_2',
            'gp_type', 'shell_model', 'sensor_model', 'body_model'
        )

        for field in string_fields:
            value = params.get(field)
            if value:
                query = query.filter(getattr(Simulation, field) == value)

        for field in numeric_fields:
            raw = params.get(field)
            if raw not in (None, '', 'None'):
                try:
                    query = query.filter(getattr(Simulation, field) == float(raw))
                except (ValueError, TypeError):
                    pass

        matching_sims = query.all()
        if not matching_sims:
            return {'found': False}

        sim_ids = [s.id for s in matching_sims]
        test_results = TestResult.query.filter(
            TestResult.simulation_id.in_(sim_ids)
        ).all()

        if not test_results:
            return {'found': False}

        # Parse data from each linked test result
        datasets = []
        for tr in test_results:
            if not tr.data:
                continue
            try:
                d = json.loads(tr.data)
                if d.get('time') and d.get('pressure'):
                    datasets.append(d)
            except (json.JSONDecodeError, TypeError):
                continue

        if not datasets:
            return {'found': False}

        averaged = ComparisonService.average_datasets(datasets)
        return {'found': True, 'data': averaged, 'count': len(datasets)}
