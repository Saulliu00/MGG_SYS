-- =============================================================================
-- MGG Simulation System — SQLite Schema Backup
-- Generated from: instance/simulation_system.db
-- Source of truth: database/models.py
-- =============================================================================

-- User accounts and roles
CREATE TABLE user (
    id              INTEGER     NOT NULL,
    username        VARCHAR(80),
    employee_id     VARCHAR(120) NOT NULL,
    password_hash   VARCHAR(128) NOT NULL,
    phone           VARCHAR(20),
    role            VARCHAR(20)  NOT NULL,   -- 'admin' | 'research_engineer' | 'lab_engineer'
    is_active       BOOLEAN,
    created_at      DATETIME,
    PRIMARY KEY (id),
    UNIQUE (employee_id)
);

-- Complete set of test conditions (one row = one full parameter combination)
CREATE TABLE recipe (
    id                  INTEGER     NOT NULL,
    user_id             INTEGER     NOT NULL,
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
    created_at          DATETIME,
    PRIMARY KEY (id),
    FOREIGN KEY (user_id) REFERENCES user (id)
);

-- 工单 — links a recipe (test conditions) with experiment files and simulations
CREATE TABLE work_order (
    id                  INTEGER     NOT NULL,
    work_order_number   VARCHAR(50) NOT NULL,  -- unique 工单号
    recipe_id           INTEGER     NOT NULL,
    user_id             INTEGER     NOT NULL,
    employee_id         VARCHAR(100),           -- 工号
    test_name           VARCHAR(200),           -- 测试名称
    notes               TEXT,
    test_date           DATE,
    test_time           VARCHAR(10),
    source              VARCHAR(20),            -- 'simulation' | 'experiment'
    created_at          DATETIME,
    updated_at          DATETIME,
    PRIMARY KEY (id),
    FOREIGN KEY (recipe_id) REFERENCES recipe (id),
    FOREIGN KEY (user_id)   REFERENCES user (id)
);

CREATE UNIQUE INDEX ix_work_order_work_order_number ON work_order (work_order_number);

-- Simulation runs (正向 tab)
CREATE TABLE simulation (
    id              INTEGER     NOT NULL,
    user_id         INTEGER     NOT NULL,
    work_order_id   INTEGER,                    -- FK to work_order (nullable)
    -- Parameters (legacy columns kept for backward compatibility)
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
    employee_id     VARCHAR(100),
    test_name       VARCHAR(200),
    notes           TEXT,
    work_order      VARCHAR(50),                -- legacy string, superseded by work_order_id
    result_data     TEXT,                       -- JSON simulation results
    chart_image     VARCHAR(255),
    created_at      DATETIME,
    PRIMARY KEY (id),
    FOREIGN KEY (user_id)       REFERENCES user (id),
    FOREIGN KEY (work_order_id) REFERENCES work_order (id)
);

-- Uploaded Excel files (time vs pressure data) associated with a work order
CREATE TABLE experiment_file (
    id                  INTEGER     NOT NULL,
    work_order_id       INTEGER     NOT NULL,
    user_id             INTEGER     NOT NULL,
    original_filename   VARCHAR(255) NOT NULL,  -- original name from user's machine
    stored_filename     VARCHAR(255) NOT NULL,  -- UUID-based name on disk
    file_path           VARCHAR(500) NOT NULL,  -- absolute path on server
    file_size           INTEGER,                -- bytes
    uploaded_at         DATETIME,
    PRIMARY KEY (id),
    FOREIGN KEY (work_order_id) REFERENCES work_order (id),
    FOREIGN KEY (user_id)       REFERENCES user (id)
);

-- Legacy test result uploads (pre-work-order system)
CREATE TABLE test_result (
    id              INTEGER     NOT NULL,
    user_id         INTEGER     NOT NULL,
    simulation_id   INTEGER,
    filename        VARCHAR(255) NOT NULL,
    file_path       VARCHAR(500) NOT NULL,
    data            TEXT,                       -- JSON parsed test data
    uploaded_at     DATETIME,
    PRIMARY KEY (id),
    FOREIGN KEY (user_id)       REFERENCES user (id),
    FOREIGN KEY (simulation_id) REFERENCES simulation (id)
);
