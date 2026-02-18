from database.extensions import db, login_manager, bcrypt
from flask_login import UserMixin
from datetime import datetime

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80))
    employee_id = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    phone = db.Column(db.String(20))
    role = db.Column(db.String(20), nullable=False, default='research_engineer')
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    simulations = db.relationship('Simulation', backref='user', lazy=True)
    test_results = db.relationship('TestResult', backref='user', lazy=True)
    recipes = db.relationship('Recipe', backref='user', lazy=True)
    work_orders = db.relationship('WorkOrder', backref='user', lazy=True)
    experiment_files = db.relationship('ExperimentFile', backref='user', lazy=True)

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


class Simulation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    # Test parameters (测试参数)
    ignition_model = db.Column(db.String(50))  # 点火具型号
    nc_type_1 = db.Column(db.String(50))  # NC类型1
    nc_usage_1 = db.Column(db.Float)  # NC用量1 (毫克)
    nc_type_2 = db.Column(db.String(50))  # NC类型2
    nc_usage_2 = db.Column(db.Float)  # NC用量2 (毫克)
    gp_type = db.Column(db.String(50))  # GP类型
    gp_usage = db.Column(db.Float)  # GP用量 (毫克)
    shell_model = db.Column(db.String(50))  # 管壳高度 (mm)
    current = db.Column(db.Float)  # 电流
    sensor_model = db.Column(db.String(50))  # 传感器量程
    body_model = db.Column(db.String(50))  # 容积
    equipment = db.Column(db.String(50))  # 测试设备

    # Test metadata
    employee_id = db.Column(db.String(100))  # 工号
    test_name = db.Column(db.String(200))  # 测试名称
    notes = db.Column(db.Text)  # 备注
    work_order = db.Column(db.String(50))  # 工单号 (legacy, kept for backward compat)
    work_order_id = db.Column(db.Integer, db.ForeignKey('work_order.id'), nullable=True)

    # Results
    result_data = db.Column(db.Text)  # JSON formatted simulation results
    chart_image = db.Column(db.String(255))  # Path to generated chart

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<Simulation {self.id} - {self.test_name}>'


class TestResult(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    simulation_id = db.Column(db.Integer, db.ForeignKey('simulation.id'), nullable=True)

    filename = db.Column(db.String(255), nullable=False)
    file_path = db.Column(db.String(500), nullable=False)
    data = db.Column(db.Text)  # JSON formatted test data

    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<TestResult {self.id} - {self.filename}>'


class Recipe(db.Model):
    """Complete set of test conditions (one row = one full parameter combination)."""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    # Complete test conditions
    ignition_model = db.Column(db.String(50))       # 点火具型号
    nc_type_1 = db.Column(db.String(50))             # NC类型1
    nc_usage_1 = db.Column(db.Float)                 # NC用量1 (毫克)
    nc_type_2 = db.Column(db.String(50))             # NC类型2
    nc_usage_2 = db.Column(db.Float)                 # NC用量2 (毫克)
    gp_type = db.Column(db.String(50))               # GP类型
    gp_usage = db.Column(db.Float)                   # GP用量 (毫克)
    shell_model = db.Column(db.String(50))           # 管壳高度 (mm)
    current_condition = db.Column(db.String(50))     # 通电条件
    sensor_range = db.Column(db.String(50))          # 传感器量程
    body_model = db.Column(db.String(50))            # 容积
    equipment = db.Column(db.String(50))             # 测试设备

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    work_orders = db.relationship('WorkOrder', backref='recipe', lazy=True)

    def __repr__(self):
        return f'<Recipe {self.id}>'


class WorkOrder(db.Model):
    """工单 — links a recipe (test conditions) with experiment files and simulations."""
    id = db.Column(db.Integer, primary_key=True)
    work_order_number = db.Column(db.String(50), unique=True, nullable=False, index=True)
    recipe_id = db.Column(db.Integer, db.ForeignKey('recipe.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    # Metadata
    employee_id = db.Column(db.String(100))          # 工号
    test_name = db.Column(db.String(200))            # 测试名称
    notes = db.Column(db.Text)                       # 备注
    test_date = db.Column(db.Date)                   # 日期
    test_time = db.Column(db.String(10))             # 时间

    source = db.Column(db.String(20), default='simulation')  # 'simulation' or 'experiment'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    simulations = db.relationship('Simulation', backref='work_order_ref', lazy=True)
    experiment_files = db.relationship('ExperimentFile', backref='work_order', lazy=True,
                                       cascade='all, delete-orphan')

    def __repr__(self):
        return f'<WorkOrder {self.work_order_number}>'


class ExperimentFile(db.Model):
    """An uploaded Excel file (time vs pressure data) associated with a work order."""
    id = db.Column(db.Integer, primary_key=True)
    work_order_id = db.Column(db.Integer, db.ForeignKey('work_order.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    original_filename = db.Column(db.String(255), nullable=False)
    stored_filename = db.Column(db.String(255), nullable=False)   # UUID-based name on disk
    file_path = db.Column(db.String(500), nullable=False)
    file_size = db.Column(db.Integer)

    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<ExperimentFile {self.original_filename}>'
