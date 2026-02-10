"""Simulation service for handling simulation business logic"""
import json
from typing import Dict, List
from app.models import Simulation
from app.utils.subprocess_runner import SubprocessRunner
from app.utils.errors import SimulationError, SubprocessError, SubprocessTimeoutError


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

            # Run the simulation script
            response_data = SubprocessRunner.run_simulation_script(nc_usage_1)

            # Extract result data
            result_data = {
                'plot_data': response_data.get('plot_data'),
                'statistics': response_data.get('statistics')
            }

            # Save result to database
            simulation.result_data = json.dumps(result_data)
            self.db.session.add(simulation)
            self.db.session.commit()

            return {
                'success': True,
                'simulation_id': simulation.id,
                'data': result_data
            }

        except (SubprocessError, SubprocessTimeoutError, SimulationError):
            # Re-raise custom exceptions
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
            # Run the simulation script
            response_data = SubprocessRunner.run_simulation_script(nc_usage_1)
            return response_data

        except (SubprocessError, SubprocessTimeoutError, SimulationError):
            # Re-raise custom exceptions
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
