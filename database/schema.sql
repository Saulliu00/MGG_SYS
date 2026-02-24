-- ============================================================================
-- MGG Simulation System - Optimized Hybrid Schema
-- Compatible with: SQLite (development) and PostgreSQL (production)
-- Design Philosophy: Simplicity + Performance
-- ============================================================================
-- 
-- Key Design Decisions:
-- 1. Embedded parameter strings (not FK lookups) - simpler queries
-- 2. CHECK constraints for data validation - enforce valid values
-- 3. Separated time series tables - efficient querying of large datasets
-- 4. Recipe abstraction - reusable parameter sets
-- 5. Proper indexes - optimized for common queries
--
-- ============================================================================

-- ============================================
-- USERS AND AUTHENTICATION
-- ============================================

CREATE TABLE user (
    id              INTEGER     NOT NULL,
    username        VARCHAR(80) NOT NULL,
    employee_id     VARCHAR(120) NOT NULL UNIQUE,
    email           VARCHAR(120) UNIQUE,
    password_hash   VARCHAR(128) NOT NULL,
    phone           VARCHAR(20),
    role            VARCHAR(20)  NOT NULL DEFAULT 'research_engineer',
    department      VARCHAR(50),
    is_active       BOOLEAN     DEFAULT 1,
    created_at      DATETIME    DEFAULT CURRENT_TIMESTAMP,
    last_seen_at    DATETIME,
    session_token   VARCHAR(36),
    
    PRIMARY KEY (id),
    CHECK (role IN ('admin', 'research_engineer', 'lab_engineer'))
);

CREATE INDEX idx_user_employee_id ON user(employee_id);
CREATE INDEX idx_user_email ON user(email);
CREATE INDEX idx_user_role ON user(role);


-- ============================================
-- RECIPES (Reusable Parameter Sets)
-- ============================================

CREATE TABLE recipe (
    id                  INTEGER     NOT NULL,
    user_id             INTEGER     NOT NULL,
    
    -- Test Parameters (complete parameter combination)
    ignition_model      VARCHAR(50),         -- 点火具型号
    nc_type_1           VARCHAR(50),         -- NC类型1
    nc_usage_1          FLOAT,               -- NC用量1 (毫克)
    nc_type_2           VARCHAR(50),         -- NC类型2
    nc_usage_2          FLOAT,               -- NC用量2 (毫克)
    gp_type             VARCHAR(50),         -- GP类型
    gp_usage            FLOAT,               -- GP用量 (毫克)
    shell_model         VARCHAR(50),         -- 管壳高度 (mm)
    current_condition   VARCHAR(50),         -- 通电条件
    sensor_range        VARCHAR(50),         -- 传感器量程
    body_model          VARCHAR(50),         -- 容积
    equipment           VARCHAR(50),         -- 测试设备
    
    -- Metadata
    recipe_name         VARCHAR(200),        -- Optional friendly name
    description         TEXT,
    created_at          DATETIME    DEFAULT CURRENT_TIMESTAMP,
    updated_at          DATETIME    DEFAULT CURRENT_TIMESTAMP,
    
    PRIMARY KEY (id),
    FOREIGN KEY (user_id) REFERENCES user(id)
);

CREATE INDEX idx_recipe_user ON recipe(user_id);
CREATE INDEX idx_recipe_created ON recipe(created_at);


-- ============================================
-- WORK ORDERS (Links Recipes with Tests)
-- ============================================

CREATE TABLE work_order (
    id                  INTEGER     NOT NULL,
    work_order_number   VARCHAR(50) NOT NULL UNIQUE,
    recipe_id           INTEGER     NOT NULL,
    user_id             INTEGER     NOT NULL,
    
    -- Metadata
    employee_id         VARCHAR(100),        -- 工号
    test_name           VARCHAR(200),        -- 测试名称
    notes               TEXT,
    test_date           DATE,
    test_time           VARCHAR(10),
    
    -- Status tracking
    source              VARCHAR(20) DEFAULT 'simulation',  -- 'simulation' | 'experiment'
    status              VARCHAR(20) DEFAULT 'pending',     -- 'pending' | 'in_progress' | 'completed' | 'cancelled'
    priority            VARCHAR(10) DEFAULT 'normal',      -- 'low' | 'normal' | 'high' | 'urgent'
    
    created_at          DATETIME    DEFAULT CURRENT_TIMESTAMP,
    updated_at          DATETIME    DEFAULT CURRENT_TIMESTAMP,
    completed_at        DATETIME,
    
    PRIMARY KEY (id),
    FOREIGN KEY (recipe_id) REFERENCES recipe(id),
    FOREIGN KEY (user_id) REFERENCES user(id),
    CHECK (source IN ('simulation', 'experiment')),
    CHECK (status IN ('pending', 'in_progress', 'completed', 'cancelled')),
    CHECK (priority IN ('low', 'normal', 'high', 'urgent'))
);

CREATE UNIQUE INDEX idx_work_order_number ON work_order(work_order_number);
CREATE INDEX idx_work_order_recipe ON work_order(recipe_id);
CREATE INDEX idx_work_order_user ON work_order(user_id);
CREATE INDEX idx_work_order_status ON work_order(status);
CREATE INDEX idx_work_order_created ON work_order(created_at);


-- ============================================
-- SIMULATIONS (Forward Predictions)
-- ============================================

CREATE TABLE simulation (
    id              INTEGER     NOT NULL,
    user_id         INTEGER     NOT NULL,
    work_order_id   INTEGER,
    
    -- Test Parameters (denormalized for quick display)
    ignition_model  VARCHAR(50),
    nc_type_1       VARCHAR(50),
    nc_usage_1      FLOAT,
    nc_type_2       VARCHAR(50),
    nc_usage_2      FLOAT,
    gp_type         VARCHAR(50),
    gp_usage        FLOAT,
    shell_model     VARCHAR(50),
    current         FLOAT,
    sensor_model    VARCHAR(50),
    body_model      VARCHAR(50),
    equipment       VARCHAR(50),
    
    -- Test Metadata
    employee_id     VARCHAR(100),
    test_name       VARCHAR(200),
    notes           TEXT,
    
    -- Results Summary (detailed data in simulation_time_series)
    peak_pressure   FLOAT,                  -- Maximum pressure reached
    peak_time       FLOAT,                  -- Time of peak pressure
    model_version   VARCHAR(50),            -- Model/algorithm version used
    num_data_points INTEGER,                -- Number of time series points
    r_squared       FLOAT,                  -- Model fit quality (0-1)
    
    -- Output Files
    chart_image     VARCHAR(255),           -- Path to generated chart
    
    -- Status
    status          VARCHAR(20) DEFAULT 'completed',
    execution_time  FLOAT,                  -- Seconds
    error_message   TEXT,
    
    created_at      DATETIME    DEFAULT CURRENT_TIMESTAMP,
    
    PRIMARY KEY (id),
    FOREIGN KEY (user_id) REFERENCES user(id),
    FOREIGN KEY (work_order_id) REFERENCES work_order(id),
    CHECK (status IN ('running', 'completed', 'failed'))
);

CREATE INDEX idx_simulation_user ON simulation(user_id);
CREATE INDEX idx_simulation_work_order ON simulation(work_order_id);
CREATE INDEX idx_simulation_created ON simulation(created_at);
CREATE INDEX idx_simulation_user_created ON simulation(user_id, created_at);


-- ============================================
-- SIMULATION TIME SERIES (Separated for Performance)
-- ============================================

CREATE TABLE simulation_time_series (
    id              INTEGER     NOT NULL,
    simulation_id   INTEGER     NOT NULL,
    
    time_point      FLOAT       NOT NULL,   -- Time in milliseconds
    pressure        FLOAT       NOT NULL,   -- Pressure value
    sequence_number INTEGER,                -- Order in sequence (1, 2, 3, ...)
    
    created_at      DATETIME    DEFAULT CURRENT_TIMESTAMP,
    
    PRIMARY KEY (id),
    FOREIGN KEY (simulation_id) REFERENCES simulation(id) ON DELETE CASCADE
);

-- Critical indexes for efficient querying
CREATE INDEX idx_sim_ts_simulation ON simulation_time_series(simulation_id);
CREATE INDEX idx_sim_ts_simulation_seq ON simulation_time_series(simulation_id, sequence_number);
CREATE INDEX idx_sim_ts_simulation_time ON simulation_time_series(simulation_id, time_point);


-- ============================================
-- TEST RESULTS (Experimental Data)
-- ============================================

CREATE TABLE test_result (
    id              INTEGER     NOT NULL,
    user_id         INTEGER     NOT NULL,
    work_order_id   INTEGER,
    simulation_id   INTEGER,                -- Optional link to simulation for comparison
    
    -- File Info
    filename        VARCHAR(255) NOT NULL,
    file_path       VARCHAR(500) NOT NULL,
    file_size       INTEGER,
    
    -- Test Metadata
    test_date       DATE,
    tester_id       VARCHAR(50),
    notes           TEXT,
    
    -- Results Summary (detailed data in test_time_series)
    peak_pressure   FLOAT,
    peak_time       FLOAT,
    num_data_points INTEGER,
    
    uploaded_at     DATETIME    DEFAULT CURRENT_TIMESTAMP,
    
    PRIMARY KEY (id),
    FOREIGN KEY (user_id) REFERENCES user(id),
    FOREIGN KEY (work_order_id) REFERENCES work_order(id),
    FOREIGN KEY (simulation_id) REFERENCES simulation(id)
);

CREATE INDEX idx_test_result_user ON test_result(user_id);
CREATE INDEX idx_test_result_work_order ON test_result(work_order_id);
CREATE INDEX idx_test_result_simulation ON test_result(simulation_id);


-- ============================================
-- TEST TIME SERIES (Separated for Performance)
-- ============================================

CREATE TABLE test_time_series (
    id              INTEGER     NOT NULL,
    test_result_id  INTEGER     NOT NULL,
    
    time_point      FLOAT       NOT NULL,
    pressure        FLOAT       NOT NULL,
    sequence_number INTEGER,
    
    created_at      DATETIME    DEFAULT CURRENT_TIMESTAMP,
    
    PRIMARY KEY (id),
    FOREIGN KEY (test_result_id) REFERENCES test_result(id) ON DELETE CASCADE
);

-- Critical indexes for efficient querying
CREATE INDEX idx_test_ts_result ON test_time_series(test_result_id);
CREATE INDEX idx_test_ts_result_seq ON test_time_series(test_result_id, sequence_number);
CREATE INDEX idx_test_ts_result_time ON test_time_series(test_result_id, time_point);


-- ============================================
-- EXPERIMENT FILES (Raw Uploads)
-- ============================================

CREATE TABLE experiment_file (
    id                  INTEGER     NOT NULL,
    work_order_id       INTEGER     NOT NULL,
    user_id             INTEGER     NOT NULL,
    
    original_filename   VARCHAR(255) NOT NULL,
    stored_filename     VARCHAR(255) NOT NULL,   -- UUID-based name on disk
    file_path           VARCHAR(500) NOT NULL,
    file_size           INTEGER,
    file_type           VARCHAR(50),             -- 'xlsx', 'csv', etc.
    
    -- Processing status
    processed           BOOLEAN     DEFAULT 0,
    test_result_id      INTEGER,                 -- Link to parsed result
    
    uploaded_at         DATETIME    DEFAULT CURRENT_TIMESTAMP,
    
    PRIMARY KEY (id),
    FOREIGN KEY (work_order_id) REFERENCES work_order(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES user(id),
    FOREIGN KEY (test_result_id) REFERENCES test_result(id)
);

CREATE INDEX idx_experiment_file_work_order ON experiment_file(work_order_id);
CREATE INDEX idx_experiment_file_user ON experiment_file(user_id);


-- ============================================
-- PT COMPARISONS (Simulation vs Experimental)
-- ============================================

CREATE TABLE pt_comparison (
    id                  INTEGER     NOT NULL,
    user_id             INTEGER     NOT NULL,
    simulation_id       INTEGER     NOT NULL,
    test_result_id      INTEGER     NOT NULL,
    
    -- Comparison Metrics
    peak_pressure_diff  FLOAT,               -- |sim_peak - test_peak|
    peak_time_diff      FLOAT,               -- |sim_peak_time - test_peak_time|
    rmse                FLOAT,               -- Root Mean Square Error
    mae                 FLOAT,               -- Mean Absolute Error
    correlation         FLOAT,               -- Pearson correlation coefficient (-1 to 1)
    r_squared           FLOAT,               -- R² fit quality (0 to 1)
    
    notes               TEXT,
    created_at          DATETIME    DEFAULT CURRENT_TIMESTAMP,
    
    PRIMARY KEY (id),
    FOREIGN KEY (user_id) REFERENCES user(id),
    FOREIGN KEY (simulation_id) REFERENCES simulation(id),
    FOREIGN KEY (test_result_id) REFERENCES test_result(id)
);

CREATE INDEX idx_pt_comp_simulation ON pt_comparison(simulation_id);
CREATE INDEX idx_pt_comp_test_result ON pt_comparison(test_result_id);
CREATE INDEX idx_pt_comp_user ON pt_comparison(user_id);


-- ============================================
-- INDEXES SUMMARY
-- ============================================
-- 
-- Primary indexes (automatic):
--   - All PRIMARY KEY columns
--   - All UNIQUE constraints
--
-- Custom indexes created:
--   - User: employee_id, email, role
--   - Recipe: user_id, created_at
--   - WorkOrder: number (unique), recipe_id, user_id, status, created_at
--   - Simulation: user_id, work_order_id, created_at, (user_id, created_at)
--   - SimulationTimeSeries: simulation_id, (simulation_id, sequence), (simulation_id, time)
--   - TestResult: user_id, work_order_id, simulation_id
--   - TestTimeSeries: test_result_id, (test_result_id, sequence), (test_result_id, time)
--   - ExperimentFile: work_order_id, user_id
--   - PTComparison: simulation_id, test_result_id, user_id
--
-- Total: 8 tables, 29 indexes (including PKs)
-- ============================================
