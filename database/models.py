"""
Optimized Database Models - Hybrid Design
Combines simplicity of embedded parameters with efficiency of separated time series
"""
from database.extensions import db, login_manager, bcrypt
from flask_login import UserMixin
from datetime import datetime
from sqlalchemy import CheckConstraint, Index


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


class User(db.Model, UserMixin):
    """User accounts with authentication and role management"""
    __tablename__ = 'user'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), nullable=False)
    employee_id = db.Column(db.String(120), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=True)
    password_hash = db.Column(db.String(128), nullable=False)
    phone = db.Column(db.String(20))
    role = db.Column(db.String(20), nullable=False, default='research_engineer')
    department = db.Column(db.String(50))
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_seen_at = db.Column(db.DateTime, nullable=True)
    session_token = db.Column(db.String(36), nullable=True)

    # Relationships
    simulations = db.relationship('Simulation', backref='user', lazy='dynamic')
    test_results = db.relationship('TestResult', backref='user', lazy='dynamic')
    recipes = db.relationship('Recipe', backref='creator', lazy='dynamic')
    work_orders = db.relationship('WorkOrder', backref='creator', lazy='dynamic')
    experiment_files = db.relationship('ExperimentFile', backref='user', lazy='dynamic')

    __table_args__ = (
        CheckConstraint(
            "role IN ('admin', 'research_engineer', 'lab_engineer')",
            name='check_user_role'
        ),
    )

    @property
    def is_admin(self):
        return self.role == 'admin'

    @property
    def is_lab_engineer(self):
        return self.role == 'lab_engineer'

    @property
    def is_research_engineer(self):
        return self.role == 'research_engineer'

    def set_password(self, password):
        self.password_hash = bcrypt.generate_password_hash(password).decode('utf-8')

    def check_password(self, password):
        return bcrypt.check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f'<User {self.username}>'


class Recipe(db.Model):
    """
    Complete set of test conditions (one row = one full parameter combination).
    Multiple work orders can reference the same recipe for repeatability.
    """
    __tablename__ = 'recipe'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    # Test Parameters - using validated strings instead of FK lookups
    ignition_model = db.Column(db.String(50))      # 点火具型号
    nc_type_1 = db.Column(db.String(50))           # NC类型1
    nc_usage_1 = db.Column(db.Float)               # NC用量1 (毫克)
    nc_type_2 = db.Column(db.String(50))           # NC类型2
    nc_usage_2 = db.Column(db.Float)               # NC用量2 (毫克)
    gp_type = db.Column(db.String(50))             # GP类型
    gp_usage = db.Column(db.Float)                 # GP用量 (毫克)
    shell_model = db.Column(db.String(50))         # 管壳高度 (mm)
    current_condition = db.Column(db.String(50))   # 通电条件
    sensor_range = db.Column(db.String(50))        # 传感器量程
    body_model = db.Column(db.String(50))          # 容积
    equipment = db.Column(db.String(50))           # 测试设备

    # Metadata
    recipe_name = db.Column(db.String(200))        # Optional friendly name
    description = db.Column(db.Text)               # Recipe notes
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    work_orders = db.relationship('WorkOrder', backref='recipe', lazy='dynamic')

    def __repr__(self):
        return f'<Recipe {self.id}: {self.recipe_name or "Unnamed"}>'


class WorkOrder(db.Model):
    """
    工单 — links a recipe (test conditions) with experiment files and simulations.
    One work order can have multiple simulations and experiment files.
    """
    __tablename__ = 'work_order'
    
    id = db.Column(db.Integer, primary_key=True)
    work_order_number = db.Column(db.String(50), unique=True, nullable=False, index=True)
    recipe_id = db.Column(db.Integer, db.ForeignKey('recipe.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    # Metadata
    employee_id = db.Column(db.String(100))        # 工号
    test_name = db.Column(db.String(200))          # 测试名称
    notes = db.Column(db.Text)                     # 备注
    test_date = db.Column(db.Date)                 # 日期
    test_time = db.Column(db.String(10))           # 时间

    # Status tracking
    source = db.Column(db.String(20), default='simulation')  # 'simulation' or 'experiment'
    status = db.Column(db.String(20), default='pending')     # 'pending', 'in_progress', 'completed'
    priority = db.Column(db.String(10), default='normal')    # 'low', 'normal', 'high'
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    completed_at = db.Column(db.DateTime, nullable=True)

    # Relationships
    simulations = db.relationship('Simulation', backref='work_order_ref', lazy='dynamic')
    experiment_files = db.relationship('ExperimentFile', backref='work_order', 
                                       lazy='dynamic', cascade='all, delete-orphan')

    __table_args__ = (
        CheckConstraint(
            "source IN ('simulation', 'experiment')",
            name='check_work_order_source'
        ),
        CheckConstraint(
            "status IN ('pending', 'in_progress', 'completed', 'cancelled')",
            name='check_work_order_status'
        ),
        CheckConstraint(
            "priority IN ('low', 'normal', 'high', 'urgent')",
            name='check_work_order_priority'
        ),
    )

    def __repr__(self):
        return f'<WorkOrder {self.work_order_number}>'


class Simulation(db.Model):
    """
    Simulation runs (forward predictions).
    Parameters can be stored here for quick access, or referenced from Recipe via WorkOrder.
    Time series data stored in separate SimulationTimeSeries table for efficiency.
    """
    __tablename__ = 'simulation'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    work_order_id = db.Column(db.Integer, db.ForeignKey('work_order.id'), nullable=True)

    # Test parameters (denormalized for quick display - can also get from Recipe via WorkOrder)
    ignition_model = db.Column(db.String(50))
    nc_type_1 = db.Column(db.String(50))
    nc_usage_1 = db.Column(db.Float)
    nc_type_2 = db.Column(db.String(50))
    nc_usage_2 = db.Column(db.Float)
    gp_type = db.Column(db.String(50))
    gp_usage = db.Column(db.Float)
    shell_model = db.Column(db.String(50))
    current = db.Column(db.Float)
    sensor_model = db.Column(db.String(50))
    body_model = db.Column(db.String(50))
    equipment = db.Column(db.String(50))

    # Test metadata
    employee_id = db.Column(db.String(100))
    test_name = db.Column(db.String(200))
    notes = db.Column(db.Text)

    # Simulation results summary (detailed data in SimulationTimeSeries)
    peak_pressure = db.Column(db.Float)            # Maximum pressure reached
    peak_time = db.Column(db.Float)                # Time of peak pressure
    model_version = db.Column(db.String(50))       # Model/algorithm version used
    num_data_points = db.Column(db.Integer)        # Number of time series points
    r_squared = db.Column(db.Float)                # Model fit quality
    
    # Output files
    chart_image = db.Column(db.String(255))        # Path to generated chart
    
    # Status
    status = db.Column(db.String(20), default='completed')
    execution_time = db.Column(db.Float)           # Seconds
    error_message = db.Column(db.Text)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    time_series = db.relationship('SimulationTimeSeries', backref='simulation',
                                 lazy='dynamic', cascade='all, delete-orphan')

    __table_args__ = (
        CheckConstraint(
            "status IN ('running', 'completed', 'failed')",
            name='check_simulation_status'
        ),
        Index('idx_simulation_work_order', 'work_order_id'),
        Index('idx_simulation_user_created', 'user_id', 'created_at'),
    )

    def __repr__(self):
        return f'<Simulation {self.id} - {self.test_name}>'


class SimulationTimeSeries(db.Model):
    """
    Time series data for simulations (time vs pressure).
    Separated from Simulation table for efficient querying and pagination.
    This is CRITICAL for performance with large datasets.
    """
    __tablename__ = 'simulation_time_series'
    
    id = db.Column(db.Integer, primary_key=True)
    simulation_id = db.Column(db.Integer, db.ForeignKey('simulation.id'), nullable=False)
    
    time_point = db.Column(db.Float, nullable=False)    # Time in milliseconds
    pressure = db.Column(db.Float, nullable=False)      # Pressure value
    sequence_number = db.Column(db.Integer)             # Order in sequence
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index('idx_sim_ts_simulation_seq', 'simulation_id', 'sequence_number'),
        Index('idx_sim_ts_simulation_time', 'simulation_id', 'time_point'),
    )

    def __repr__(self):
        return f'<SimTimeSeries sim={self.simulation_id} t={self.time_point}>'


class TestResult(db.Model):
    """
    Uploaded test result files (experimental data).
    Time series data stored in separate TestTimeSeries table.
    """
    __tablename__ = 'test_result'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    work_order_id = db.Column(db.Integer, db.ForeignKey('work_order.id'), nullable=True)
    simulation_id = db.Column(db.Integer, db.ForeignKey('simulation.id'), nullable=True)

    # File info
    filename = db.Column(db.String(255), nullable=False)
    file_path = db.Column(db.String(500), nullable=False)
    file_size = db.Column(db.Integer)
    
    # Test metadata
    test_date = db.Column(db.Date)
    tester_id = db.Column(db.String(50))
    notes = db.Column(db.Text)
    
    # Results summary
    peak_pressure = db.Column(db.Float)
    peak_time = db.Column(db.Float)
    num_data_points = db.Column(db.Integer)
    
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    time_series = db.relationship('TestTimeSeries', backref='test_result',
                                 lazy='dynamic', cascade='all, delete-orphan')

    __table_args__ = (
        Index('idx_test_result_work_order', 'work_order_id'),
    )

    def __repr__(self):
        return f'<TestResult {self.id} - {self.filename}>'


class TestTimeSeries(db.Model):
    """
    Time series data from experimental test results.
    Separated for efficient querying and comparison with simulations.
    """
    __tablename__ = 'test_time_series'
    
    id = db.Column(db.Integer, primary_key=True)
    test_result_id = db.Column(db.Integer, db.ForeignKey('test_result.id'), nullable=False)
    
    time_point = db.Column(db.Float, nullable=False)
    pressure = db.Column(db.Float, nullable=False)
    sequence_number = db.Column(db.Integer)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index('idx_test_ts_result_seq', 'test_result_id', 'sequence_number'),
        Index('idx_test_ts_result_time', 'test_result_id', 'time_point'),
    )

    def __repr__(self):
        return f'<TestTimeSeries test={self.test_result_id} t={self.time_point}>'


class ExperimentFile(db.Model):
    """
    Uploaded Excel files (time vs pressure data) associated with a work order.
    Raw files before parsing into TestResult/TestTimeSeries.
    """
    __tablename__ = 'experiment_file'
    
    id = db.Column(db.Integer, primary_key=True)
    work_order_id = db.Column(db.Integer, db.ForeignKey('work_order.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    original_filename = db.Column(db.String(255), nullable=False)
    stored_filename = db.Column(db.String(255), nullable=False)   # UUID-based name
    file_path = db.Column(db.String(500), nullable=False)
    file_size = db.Column(db.Integer)
    file_type = db.Column(db.String(50))                          # 'xlsx', 'csv', etc.

    # Processing status
    processed = db.Column(db.Boolean, default=False)
    test_result_id = db.Column(db.Integer, db.ForeignKey('test_result.id'), nullable=True)
    
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<ExperimentFile {self.original_filename}>'


class PTComparison(db.Model):
    """
    Pressure-Time comparison between simulation and experimental results.
    Stores comparison metrics (RMSE, correlation, peak differences).
    """
    __tablename__ = 'pt_comparison'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    simulation_id = db.Column(db.Integer, db.ForeignKey('simulation.id'), nullable=False)
    test_result_id = db.Column(db.Integer, db.ForeignKey('test_result.id'), nullable=False)

    # Comparison metrics
    peak_pressure_diff = db.Column(db.Float)       # |sim_peak - test_peak|
    peak_time_diff = db.Column(db.Float)           # |sim_peak_time - test_peak_time|
    rmse = db.Column(db.Float)                     # Root Mean Square Error
    mae = db.Column(db.Float)                      # Mean Absolute Error
    correlation = db.Column(db.Float)              # Pearson correlation coefficient
    r_squared = db.Column(db.Float)                # R² fit quality
    
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<PTComparison sim={self.simulation_id} test={self.test_result_id}>'
