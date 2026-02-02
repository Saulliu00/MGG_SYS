"""
SQLAlchemy ORM Models
Defines all database models matching the PostgreSQL schema
"""

from sqlalchemy import Column, Integer, String, Text, Numeric, Boolean, DateTime, Date, ForeignKey, CheckConstraint
from sqlalchemy.dialects.postgresql import INET
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from db_config import Base


class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    username = Column(String(50), unique=True, nullable=False)
    email = Column(String(100), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(100))
    role = Column(String(20), nullable=False, default='user')
    department = Column(String(50))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.current_timestamp())
    updated_at = Column(DateTime, default=func.current_timestamp(), onupdate=func.current_timestamp())
    last_login = Column(DateTime)
    created_by = Column(Integer, ForeignKey('users.id'))

    # Relationships
    work_orders = relationship('WorkOrder', back_populates='creator', foreign_keys='WorkOrder.created_by')
    forward_simulations = relationship('ForwardSimulation', back_populates='user')
    reverse_simulations = relationship('ReverseSimulation', back_populates='user')
    test_results = relationship('TestResult', back_populates='user')
    operation_logs = relationship('OperationLog', back_populates='user')

    __table_args__ = (
        CheckConstraint("role IN ('admin', 'user', 'engineer')", name='check_role'),
    )


class IgniterType(Base):
    __tablename__ = 'igniter_types'

    id = Column(Integer, primary_key=True)
    type_code = Column(String(20), unique=True, nullable=False)
    description = Column(Text)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.current_timestamp())

    # Relationships
    forward_simulations = relationship('ForwardSimulation', back_populates='igniter_type')
    reverse_simulations = relationship('ReverseSimulation', back_populates='igniter_type')


class NCType1(Base):
    __tablename__ = 'nc_types1'

    id = Column(Integer, primary_key=True)
    type_code = Column(String(20), unique=True, nullable=False)
    description = Column(Text)
    density = Column(Numeric(10, 4))
    specific_heat = Column(Numeric(10, 4))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.current_timestamp())

    # Relationships
    forward_simulations = relationship('ForwardSimulation', back_populates='nc_type1')


class NCType2(Base):
    __tablename__ = 'nc_types2'

    id = Column(Integer, primary_key=True)
    type_code = Column(String(20), unique=True, nullable=False)
    description = Column(Text)
    density = Column(Numeric(10, 4))
    specific_heat = Column(Numeric(10, 4))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.current_timestamp())

    # Relationships
    forward_simulations = relationship('ForwardSimulation', back_populates='nc_type2')


class GPType(Base):
    __tablename__ = 'gp_types'

    id = Column(Integer, primary_key=True)
    type_code = Column(String(20), unique=True, nullable=False)
    description = Column(Text)
    density = Column(Numeric(10, 4))
    specific_heat = Column(Numeric(10, 4))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.current_timestamp())

    # Relationships
    forward_simulations = relationship('ForwardSimulation', back_populates='gp_type')


class ShellType(Base):
    __tablename__ = 'shell_types'

    id = Column(Integer, primary_key=True)
    type_code = Column(String(20), unique=True, nullable=False)
    description = Column(Text)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.current_timestamp())

    # Relationships
    forward_simulations = relationship('ForwardSimulation', back_populates='shell_type')
    reverse_simulations = relationship('ReverseSimulation', back_populates='shell_type')


class CurrentType(Base):
    __tablename__ = 'current_types'

    id = Column(Integer, primary_key=True)
    type_code = Column(String(20), unique=True, nullable=False)
    current_value = Column(Numeric(10, 4))
    description = Column(Text)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.current_timestamp())

    # Relationships
    forward_simulations = relationship('ForwardSimulation', back_populates='current_type')
    reverse_simulations = relationship('ReverseSimulation', back_populates='current_type')


class SensorType(Base):
    __tablename__ = 'sensor_types'

    id = Column(Integer, primary_key=True)
    type_code = Column(String(20), unique=True, nullable=False)
    description = Column(Text)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.current_timestamp())

    # Relationships
    forward_simulations = relationship('ForwardSimulation', back_populates='sensor_type')
    reverse_simulations = relationship('ReverseSimulation', back_populates='sensor_type')


class VolumeType(Base):
    __tablename__ = 'volume_types'

    id = Column(Integer, primary_key=True)
    type_code = Column(String(20), unique=True, nullable=False)
    volume_value = Column(Numeric(10, 4))
    description = Column(Text)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.current_timestamp())

    # Relationships
    forward_simulations = relationship('ForwardSimulation', back_populates='volume_type')
    reverse_simulations = relationship('ReverseSimulation', back_populates='volume_type')


class TestDevice(Base):
    __tablename__ = 'test_devices'

    id = Column(Integer, primary_key=True)
    device_code = Column(String(20), unique=True, nullable=False)
    device_name = Column(String(100))
    location = Column(String(100))
    calibration_date = Column(Date)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.current_timestamp())

    # Relationships
    test_results = relationship('TestResult', back_populates='test_device')
    forward_simulations = relationship('ForwardSimulation', back_populates='test_device')
    reverse_simulations = relationship('ReverseSimulation', back_populates='test_device')


class Employee(Base):
    __tablename__ = 'employees'

    id = Column(Integer, primary_key=True)
    employee_id = Column(String(50), unique=True, nullable=False)
    full_name = Column(String(100), nullable=False)
    department = Column(String(50))
    position = Column(String(50))
    email = Column(String(100))
    phone = Column(String(20))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.current_timestamp())
    updated_at = Column(DateTime, default=func.current_timestamp(), onupdate=func.current_timestamp())

    # Relationships
    forward_simulations = relationship('ForwardSimulation', back_populates='employee')
    reverse_simulations = relationship('ReverseSimulation', back_populates='employee')
    tickets = relationship('Ticket', back_populates='assigned_employee')


class Ticket(Base):
    __tablename__ = 'tickets'

    id = Column(Integer, primary_key=True)
    ticket_number = Column(String(50), unique=True, nullable=False)
    work_order_id = Column(Integer, ForeignKey('work_orders.id'))
    created_by = Column(Integer, ForeignKey('users.id'))
    assigned_to = Column(Integer, ForeignKey('employees.id'))
    status = Column(String(20), default='open')
    priority = Column(String(10), default='normal')
    title = Column(String(200), nullable=False)
    description = Column(Text)
    resolution = Column(Text)
    created_at = Column(DateTime, default=func.current_timestamp())
    updated_at = Column(DateTime, default=func.current_timestamp(), onupdate=func.current_timestamp())
    resolved_at = Column(DateTime)

    # Relationships
    work_order = relationship('WorkOrder', back_populates='tickets')
    creator = relationship('User')
    assigned_employee = relationship('Employee', back_populates='tickets')

    __table_args__ = (
        CheckConstraint("status IN ('open', 'in_progress', 'resolved', 'closed', 'cancelled')", name='check_ticket_status'),
        CheckConstraint("priority IN ('low', 'normal', 'high', 'urgent')", name='check_ticket_priority'),
    )


class WorkOrder(Base):
    __tablename__ = 'work_orders'

    id = Column(Integer, primary_key=True)
    work_order_number = Column(String(50), unique=True, nullable=False)
    created_by = Column(Integer, ForeignKey('users.id'), nullable=False)
    status = Column(String(20), default='pending')
    priority = Column(String(10), default='normal')
    description = Column(Text)
    created_at = Column(DateTime, default=func.current_timestamp())
    updated_at = Column(DateTime, default=func.current_timestamp(), onupdate=func.current_timestamp())
    completed_at = Column(DateTime)

    # Relationships
    creator = relationship('User', back_populates='work_orders', foreign_keys=[created_by])
    forward_simulations = relationship('ForwardSimulation', back_populates='work_order')
    reverse_simulations = relationship('ReverseSimulation', back_populates='work_order')
    test_results = relationship('TestResult', back_populates='work_order')
    tickets = relationship('Ticket', back_populates='work_order')

    __table_args__ = (
        CheckConstraint("status IN ('pending', 'in_progress', 'completed', 'cancelled')", name='check_status'),
        CheckConstraint("priority IN ('low', 'normal', 'high', 'urgent')", name='check_priority'),
    )


class ForwardSimulation(Base):
    __tablename__ = 'forward_simulations'

    id = Column(Integer, primary_key=True)
    work_order_id = Column(Integer, ForeignKey('work_orders.id'))
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    employee_id = Column(Integer, ForeignKey('employees.id'))

    # Input Parameters
    igniter_type_id = Column(Integer, ForeignKey('igniter_types.id'))
    nc_type1_id = Column(Integer, ForeignKey('nc_types1.id'))
    nc_amount1 = Column(Numeric(10, 4))
    nc_type2_id = Column(Integer, ForeignKey('nc_types2.id'))
    nc_amount2 = Column(Numeric(10, 4))
    gp_type_id = Column(Integer, ForeignKey('gp_types.id'))
    gp_amount = Column(Numeric(10, 4))
    shell_type_id = Column(Integer, ForeignKey('shell_types.id'))
    current_type_id = Column(Integer, ForeignKey('current_types.id'))
    sensor_type_id = Column(Integer, ForeignKey('sensor_types.id'))
    volume_type_id = Column(Integer, ForeignKey('volume_types.id'))
    test_device_id = Column(Integer, ForeignKey('test_devices.id'))

    # Model Information
    model_version = Column(String(50))
    num_models = Column(Integer)
    r_squared = Column(Numeric(10, 8))

    # Results
    peak_pressure = Column(Numeric(10, 4))
    peak_time = Column(Numeric(10, 4))
    num_data_points = Column(Integer)

    # Metadata
    simulation_type = Column(String(20), default='forward')
    status = Column(String(20), default='completed')
    execution_time = Column(Numeric(10, 4))
    error_message = Column(Text)
    created_at = Column(DateTime, default=func.current_timestamp())

    # Relationships
    user = relationship('User', back_populates='forward_simulations')
    work_order = relationship('WorkOrder', back_populates='forward_simulations')
    employee = relationship('Employee', back_populates='forward_simulations')
    igniter_type = relationship('IgniterType', back_populates='forward_simulations')
    nc_type1 = relationship('NCType1', back_populates='forward_simulations')
    nc_type2 = relationship('NCType2', back_populates='forward_simulations')
    gp_type = relationship('GPType', back_populates='forward_simulations')
    shell_type = relationship('ShellType', back_populates='forward_simulations')
    current_type = relationship('CurrentType', back_populates='forward_simulations')
    sensor_type = relationship('SensorType', back_populates='forward_simulations')
    volume_type = relationship('VolumeType', back_populates='forward_simulations')
    test_device = relationship('TestDevice', back_populates='forward_simulations')
    time_series = relationship('SimulationTimeSeries', back_populates='simulation', cascade='all, delete-orphan')
    comparisons = relationship('PTComparison', back_populates='simulation')

    __table_args__ = (
        CheckConstraint("simulation_type IN ('forward', 'reverse')", name='check_simulation_type'),
        CheckConstraint("status IN ('running', 'completed', 'failed')", name='check_status'),
    )


class SimulationTimeSeries(Base):
    __tablename__ = 'simulation_time_series'

    id = Column(Integer, primary_key=True)
    simulation_id = Column(Integer, ForeignKey('forward_simulations.id', ondelete='CASCADE'))
    time_point = Column(Numeric(10, 6))
    pressure = Column(Numeric(10, 6))
    sequence_number = Column(Integer)
    created_at = Column(DateTime, default=func.current_timestamp())

    # Relationships
    simulation = relationship('ForwardSimulation', back_populates='time_series')


class ReverseSimulation(Base):
    __tablename__ = 'reverse_simulations'

    id = Column(Integer, primary_key=True)
    work_order_id = Column(Integer, ForeignKey('work_orders.id'))
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    employee_id = Column(Integer, ForeignKey('employees.id'))

    # Input Parameters
    igniter_type_id = Column(Integer, ForeignKey('igniter_types.id'))
    shell_type_id = Column(Integer, ForeignKey('shell_types.id'))
    current_type_id = Column(Integer, ForeignKey('current_types.id'))
    sensor_type_id = Column(Integer, ForeignKey('sensor_types.id'))
    volume_type_id = Column(Integer, ForeignKey('volume_types.id'))
    test_device_id = Column(Integer, ForeignKey('test_devices.id'))
    pressure_data_file = Column(String(255))

    # Results
    predicted_nc_type1_id = Column(Integer, ForeignKey('nc_types1.id'))
    predicted_nc_amount1 = Column(Numeric(10, 4))
    predicted_nc_type2_id = Column(Integer, ForeignKey('nc_types2.id'))
    predicted_nc_amount2 = Column(Numeric(10, 4))
    predicted_gp_type_id = Column(Integer, ForeignKey('gp_types.id'))
    predicted_gp_amount = Column(Numeric(10, 4))
    confidence_score = Column(Numeric(5, 2))

    # Metadata
    model_version = Column(String(50))
    status = Column(String(20), default='completed')
    execution_time = Column(Numeric(10, 4))
    error_message = Column(Text)
    created_at = Column(DateTime, default=func.current_timestamp())

    # Relationships
    user = relationship('User', back_populates='reverse_simulations')
    work_order = relationship('WorkOrder', back_populates='reverse_simulations')
    employee = relationship('Employee', back_populates='reverse_simulations')
    igniter_type = relationship('IgniterType', back_populates='reverse_simulations')
    shell_type = relationship('ShellType', back_populates='reverse_simulations')
    current_type = relationship('CurrentType', back_populates='reverse_simulations')
    sensor_type = relationship('SensorType', back_populates='reverse_simulations')
    volume_type = relationship('VolumeType', back_populates='reverse_simulations')
    test_device = relationship('TestDevice', back_populates='reverse_simulations')

    __table_args__ = (
        CheckConstraint("status IN ('running', 'completed', 'failed')", name='check_status'),
    )


class TestResult(Base):
    __tablename__ = 'test_results'

    id = Column(Integer, primary_key=True)
    work_order_id = Column(Integer, ForeignKey('work_orders.id'))
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    tester_id = Column(String(50))
    test_device_id = Column(Integer, ForeignKey('test_devices.id'))
    test_date = Column(Date, nullable=False)
    notes = Column(Text)

    # Metadata
    status = Column(String(20), default='submitted')
    created_at = Column(DateTime, default=func.current_timestamp())
    updated_at = Column(DateTime, default=func.current_timestamp(), onupdate=func.current_timestamp())

    # Relationships
    user = relationship('User', back_populates='test_results')
    work_order = relationship('WorkOrder', back_populates='test_results')
    test_device = relationship('TestDevice', back_populates='test_results')
    files = relationship('TestResultFile', back_populates='test_result', cascade='all, delete-orphan')
    time_series = relationship('TestTimeSeries', back_populates='test_result', cascade='all, delete-orphan')
    comparisons = relationship('PTComparison', back_populates='test_result')

    __table_args__ = (
        CheckConstraint("status IN ('submitted', 'validated', 'archived')", name='check_status'),
    )


class TestResultFile(Base):
    __tablename__ = 'test_result_files'

    id = Column(Integer, primary_key=True)
    test_result_id = Column(Integer, ForeignKey('test_results.id', ondelete='CASCADE'))
    file_name = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    file_size = Column(Integer)
    file_type = Column(String(50))
    uploaded_at = Column(DateTime, default=func.current_timestamp())

    # Relationships
    test_result = relationship('TestResult', back_populates='files')
    time_series = relationship('TestTimeSeries', back_populates='file')


class TestTimeSeries(Base):
    __tablename__ = 'test_time_series'

    id = Column(Integer, primary_key=True)
    test_result_id = Column(Integer, ForeignKey('test_results.id', ondelete='CASCADE'))
    file_id = Column(Integer, ForeignKey('test_result_files.id'))
    time_point = Column(Numeric(10, 6))
    pressure = Column(Numeric(10, 6))
    sequence_number = Column(Integer)
    created_at = Column(DateTime, default=func.current_timestamp())

    # Relationships
    test_result = relationship('TestResult', back_populates='time_series')
    file = relationship('TestResultFile', back_populates='time_series')


class PTComparison(Base):
    __tablename__ = 'pt_comparisons'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    simulation_id = Column(Integer, ForeignKey('forward_simulations.id'))
    test_result_id = Column(Integer, ForeignKey('test_results.id'))

    # Metrics
    peak_pressure_diff = Column(Numeric(10, 4))
    peak_time_diff = Column(Numeric(10, 4))
    rmse = Column(Numeric(10, 6))
    correlation = Column(Numeric(10, 8))

    notes = Column(Text)
    created_at = Column(DateTime, default=func.current_timestamp())

    # Relationships
    user = relationship('User')
    simulation = relationship('ForwardSimulation', back_populates='comparisons')
    test_result = relationship('TestResult', back_populates='comparisons')


class OperationLog(Base):
    __tablename__ = 'operation_logs'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    log_type = Column(String(20), nullable=False)
    action = Column(String(100), nullable=False)
    details = Column(Text)
    ip_address = Column(INET)
    user_agent = Column(Text)
    created_at = Column(DateTime, default=func.current_timestamp())

    # Relationships
    user = relationship('User', back_populates='operation_logs')

    __table_args__ = (
        CheckConstraint("log_type IN ('login', 'simulation', 'upload', 'download', 'comparison', 'work_order', 'navigation', 'admin')", name='check_log_type'),
    )


class ArchiveBatch(Base):
    __tablename__ = 'archive_batches'

    id = Column(Integer, primary_key=True)
    batch_name = Column(String(100), unique=True, nullable=False)
    table_name = Column(String(50), nullable=False)
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime, nullable=False)
    row_count = Column(Integer)
    parquet_file_path = Column(String(500))
    parquet_file_size = Column(Integer)
    compression_type = Column(String(20), default='snappy')
    archived_at = Column(DateTime, default=func.current_timestamp())
    archived_by = Column(Integer, ForeignKey('users.id'))

    # Status
    status = Column(String(20), default='completed')
    checksum = Column(String(64))

    __table_args__ = (
        CheckConstraint("status IN ('in_progress', 'completed', 'failed')", name='check_status'),
    )


class ModelVersion(Base):
    __tablename__ = 'model_versions'

    id = Column(Integer, primary_key=True)
    version_name = Column(String(50), unique=True, nullable=False)
    model_type = Column(String(20), nullable=False)
    file_path = Column(String(500), nullable=False)
    num_models = Column(Integer)
    training_date = Column(Date)
    r_squared = Column(Numeric(10, 8))
    description = Column(Text)
    is_active = Column(Boolean, default=False)
    created_at = Column(DateTime, default=func.current_timestamp())
    created_by = Column(Integer, ForeignKey('users.id'))

    __table_args__ = (
        CheckConstraint("model_type IN ('forward', 'reverse')", name='check_model_type'),
    )


class RetentionPolicy(Base):
    __tablename__ = 'retention_policies'

    id = Column(Integer, primary_key=True)
    table_name = Column(String(50), unique=True, nullable=False)
    retention_days = Column(Integer, nullable=False)
    archive_enabled = Column(Boolean, default=True)
    delete_after_archive = Column(Boolean, default=True)
    last_cleanup_at = Column(DateTime)
    created_at = Column(DateTime, default=func.current_timestamp())
    updated_at = Column(DateTime, default=func.current_timestamp(), onupdate=func.current_timestamp())
