-- MGG Simulation System Database Schema
-- PostgreSQL Database for Production Use
-- Architecture: Hot PostgreSQL + Cold Parquet Archive

-- ============================================
-- USERS AND AUTHENTICATION
-- ============================================

CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(100),
    role VARCHAR(20) NOT NULL DEFAULT 'user', -- 'admin', 'user', 'engineer'
    department VARCHAR(50),
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP,
    created_by INTEGER REFERENCES users(id),

    CONSTRAINT check_role CHECK (role IN ('admin', 'user', 'engineer'))
);

CREATE INDEX idx_users_username ON users(username);
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_role ON users(role);
CREATE INDEX idx_users_is_active ON users(is_active);

-- ============================================
-- SIMULATION PARAMETERS AND CONFIGURATION
-- ============================================

CREATE TABLE igniter_types (
    id SERIAL PRIMARY KEY,
    type_code VARCHAR(20) UNIQUE NOT NULL,
    description TEXT,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE nc_types (
    id SERIAL PRIMARY KEY,
    type_code VARCHAR(20) UNIQUE NOT NULL,
    description TEXT,
    density DECIMAL(10, 4),
    specific_heat DECIMAL(10, 4),
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE gp_types (
    id SERIAL PRIMARY KEY,
    type_code VARCHAR(20) UNIQUE NOT NULL,
    description TEXT,
    density DECIMAL(10, 4),
    specific_heat DECIMAL(10, 4),
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE test_devices (
    id SERIAL PRIMARY KEY,
    device_code VARCHAR(20) UNIQUE NOT NULL,
    device_name VARCHAR(100),
    location VARCHAR(100),
    calibration_date DATE,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================
-- WORK ORDERS
-- ============================================

CREATE TABLE work_orders (
    id SERIAL PRIMARY KEY,
    work_order_number VARCHAR(50) UNIQUE NOT NULL, -- Format: WO-YYYYMMDD-HHMMSS
    created_by INTEGER REFERENCES users(id) NOT NULL,
    status VARCHAR(20) DEFAULT 'pending', -- 'pending', 'in_progress', 'completed', 'cancelled'
    priority VARCHAR(10) DEFAULT 'normal', -- 'low', 'normal', 'high', 'urgent'
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,

    CONSTRAINT check_status CHECK (status IN ('pending', 'in_progress', 'completed', 'cancelled')),
    CONSTRAINT check_priority CHECK (priority IN ('low', 'normal', 'high', 'urgent'))
);

CREATE INDEX idx_work_orders_number ON work_orders(work_order_number);
CREATE INDEX idx_work_orders_status ON work_orders(status);
CREATE INDEX idx_work_orders_created_by ON work_orders(created_by);
CREATE INDEX idx_work_orders_created_at ON work_orders(created_at DESC);

-- ============================================
-- FORWARD SIMULATIONS (正向仿真)
-- ============================================

CREATE TABLE forward_simulations (
    id SERIAL PRIMARY KEY,
    work_order_id INTEGER REFERENCES work_orders(id),
    user_id INTEGER REFERENCES users(id) NOT NULL,

    -- Input Parameters
    shell_height DECIMAL(10, 4),
    current_condition DECIMAL(10, 4),
    igniter_type_id INTEGER REFERENCES igniter_types(id),
    nc_type_id INTEGER REFERENCES nc_types(id),
    nc_amount DECIMAL(10, 4), -- NC用量1 (mg)
    gp_type_id INTEGER REFERENCES gp_types(id),
    gp_amount DECIMAL(10, 4),

    -- Model Information
    model_version VARCHAR(50),
    num_models INTEGER, -- Number of time-point models used
    r_squared DECIMAL(10, 8),

    -- Simulation Results
    peak_pressure DECIMAL(10, 4), -- MPa
    peak_time DECIMAL(10, 4), -- ms
    num_data_points INTEGER,

    -- Metadata
    simulation_type VARCHAR(20) DEFAULT 'forward',
    status VARCHAR(20) DEFAULT 'completed', -- 'running', 'completed', 'failed'
    execution_time DECIMAL(10, 4), -- seconds
    error_message TEXT,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT check_simulation_type CHECK (simulation_type IN ('forward', 'reverse')),
    CONSTRAINT check_status CHECK (status IN ('running', 'completed', 'failed'))
);

CREATE INDEX idx_forward_sim_user ON forward_simulations(user_id);
CREATE INDEX idx_forward_sim_work_order ON forward_simulations(work_order_id);
CREATE INDEX idx_forward_sim_created_at ON forward_simulations(created_at DESC);
CREATE INDEX idx_forward_sim_nc_amount ON forward_simulations(nc_amount);

-- ============================================
-- SIMULATION TIME SERIES DATA
-- ============================================

CREATE TABLE simulation_time_series (
    id SERIAL PRIMARY KEY,
    simulation_id INTEGER REFERENCES forward_simulations(id) ON DELETE CASCADE,
    time_point DECIMAL(10, 6), -- ms
    pressure DECIMAL(10, 6), -- MPa
    sequence_number INTEGER, -- For ordering

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_sim_ts_simulation ON simulation_time_series(simulation_id);
CREATE INDEX idx_sim_ts_sequence ON simulation_time_series(simulation_id, sequence_number);

-- ============================================
-- REVERSE SIMULATIONS (逆向仿真)
-- ============================================

CREATE TABLE reverse_simulations (
    id SERIAL PRIMARY KEY,
    work_order_id INTEGER REFERENCES work_orders(id),
    user_id INTEGER REFERENCES users(id) NOT NULL,

    -- Input Parameters
    shell_height DECIMAL(10, 4),
    current_condition DECIMAL(10, 4),
    igniter_type_id INTEGER REFERENCES igniter_types(id),
    test_device_id INTEGER REFERENCES test_devices(id),

    -- Uploaded Pressure Data Reference
    pressure_data_file VARCHAR(255), -- Path to uploaded file

    -- Prediction Results
    predicted_nc_type_id INTEGER REFERENCES nc_types(id),
    predicted_nc_amount DECIMAL(10, 4),
    predicted_gp_type_id INTEGER REFERENCES gp_types(id),
    predicted_gp_amount DECIMAL(10, 4),
    confidence_score DECIMAL(5, 2), -- 0-100%

    -- Metadata
    model_version VARCHAR(50),
    status VARCHAR(20) DEFAULT 'completed',
    execution_time DECIMAL(10, 4),
    error_message TEXT,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT check_status CHECK (status IN ('running', 'completed', 'failed'))
);

CREATE INDEX idx_reverse_sim_user ON reverse_simulations(user_id);
CREATE INDEX idx_reverse_sim_work_order ON reverse_simulations(work_order_id);
CREATE INDEX idx_reverse_sim_created_at ON reverse_simulations(created_at DESC);

-- ============================================
-- TEST RESULTS (实验结果)
-- ============================================

CREATE TABLE test_results (
    id SERIAL PRIMARY KEY,
    work_order_id INTEGER REFERENCES work_orders(id),
    user_id INTEGER REFERENCES users(id) NOT NULL,
    tester_id VARCHAR(50), -- Employee ID
    test_device_id INTEGER REFERENCES test_devices(id),
    test_date DATE NOT NULL,
    notes TEXT,

    -- Metadata
    status VARCHAR(20) DEFAULT 'submitted',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT check_status CHECK (status IN ('submitted', 'validated', 'archived'))
);

CREATE INDEX idx_test_results_work_order ON test_results(work_order_id);
CREATE INDEX idx_test_results_user ON test_results(user_id);
CREATE INDEX idx_test_results_date ON test_results(test_date DESC);
CREATE INDEX idx_test_results_device ON test_results(test_device_id);

-- ============================================
-- TEST RESULT FILES
-- ============================================

CREATE TABLE test_result_files (
    id SERIAL PRIMARY KEY,
    test_result_id INTEGER REFERENCES test_results(id) ON DELETE CASCADE,
    file_name VARCHAR(255) NOT NULL,
    file_path VARCHAR(500) NOT NULL,
    file_size BIGINT, -- bytes
    file_type VARCHAR(50), -- 'xlsx', 'csv', etc.
    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_test_files_result ON test_result_files(test_result_id);

-- ============================================
-- TEST TIME SERIES DATA
-- ============================================

CREATE TABLE test_time_series (
    id SERIAL PRIMARY KEY,
    test_result_id INTEGER REFERENCES test_results(id) ON DELETE CASCADE,
    file_id INTEGER REFERENCES test_result_files(id),
    time_point DECIMAL(10, 6), -- ms
    pressure DECIMAL(10, 6), -- MPa
    sequence_number INTEGER,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_test_ts_result ON test_time_series(test_result_id);
CREATE INDEX idx_test_ts_file ON test_time_series(file_id);
CREATE INDEX idx_test_ts_sequence ON test_time_series(test_result_id, sequence_number);

-- ============================================
-- COMPARISONS (PT曲线对比)
-- ============================================

CREATE TABLE pt_comparisons (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) NOT NULL,
    simulation_id INTEGER REFERENCES forward_simulations(id),
    test_result_id INTEGER REFERENCES test_results(id),

    -- Comparison Metrics
    peak_pressure_diff DECIMAL(10, 4), -- MPa
    peak_time_diff DECIMAL(10, 4), -- ms
    rmse DECIMAL(10, 6), -- Root Mean Square Error
    correlation DECIMAL(10, 8), -- Correlation coefficient

    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_comparisons_user ON pt_comparisons(user_id);
CREATE INDEX idx_comparisons_simulation ON pt_comparisons(simulation_id);
CREATE INDEX idx_comparisons_test ON pt_comparisons(test_result_id);
CREATE INDEX idx_comparisons_created_at ON pt_comparisons(created_at DESC);

-- ============================================
-- OPERATION LOGS (操作日志)
-- ============================================

CREATE TABLE operation_logs (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    log_type VARCHAR(20) NOT NULL, -- 'login', 'simulation', 'upload', 'download', 'comparison', 'work_order', 'navigation'
    action VARCHAR(100) NOT NULL,
    details TEXT,
    ip_address INET,
    user_agent TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT check_log_type CHECK (log_type IN ('login', 'simulation', 'upload', 'download', 'comparison', 'work_order', 'navigation', 'admin'))
);

CREATE INDEX idx_logs_user ON operation_logs(user_id);
CREATE INDEX idx_logs_type ON operation_logs(log_type);
CREATE INDEX idx_logs_created_at ON operation_logs(created_at DESC);
CREATE INDEX idx_logs_user_type ON operation_logs(user_id, log_type);

-- ============================================
-- PARQUET ARCHIVE TRACKING
-- ============================================

CREATE TABLE archive_batches (
    id SERIAL PRIMARY KEY,
    batch_name VARCHAR(100) UNIQUE NOT NULL,
    table_name VARCHAR(50) NOT NULL,
    start_date TIMESTAMP NOT NULL,
    end_date TIMESTAMP NOT NULL,
    row_count BIGINT,
    parquet_file_path VARCHAR(500),
    parquet_file_size BIGINT,
    compression_type VARCHAR(20) DEFAULT 'snappy',
    archived_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    archived_by INTEGER REFERENCES users(id),

    -- Status
    status VARCHAR(20) DEFAULT 'completed', -- 'in_progress', 'completed', 'failed'
    checksum VARCHAR(64), -- SHA256 hash for verification

    CONSTRAINT check_status CHECK (status IN ('in_progress', 'completed', 'failed'))
);

CREATE INDEX idx_archive_table ON archive_batches(table_name);
CREATE INDEX idx_archive_dates ON archive_batches(start_date, end_date);
CREATE INDEX idx_archive_status ON archive_batches(status);

-- ============================================
-- MODEL VERSIONS
-- ============================================

CREATE TABLE model_versions (
    id SERIAL PRIMARY KEY,
    version_name VARCHAR(50) UNIQUE NOT NULL,
    model_type VARCHAR(20) NOT NULL, -- 'forward', 'reverse'
    file_path VARCHAR(500) NOT NULL,
    num_models INTEGER, -- Number of models in ensemble
    training_date DATE,
    r_squared DECIMAL(10, 8),
    description TEXT,
    is_active BOOLEAN DEFAULT false,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by INTEGER REFERENCES users(id),

    CONSTRAINT check_model_type CHECK (model_type IN ('forward', 'reverse'))
);

CREATE INDEX idx_model_versions_type ON model_versions(model_type);
CREATE INDEX idx_model_versions_active ON model_versions(is_active);

-- ============================================
-- DATA RETENTION POLICIES
-- ============================================

CREATE TABLE retention_policies (
    id SERIAL PRIMARY KEY,
    table_name VARCHAR(50) UNIQUE NOT NULL,
    retention_days INTEGER NOT NULL, -- Days to keep in hot PostgreSQL
    archive_enabled BOOLEAN DEFAULT true,
    delete_after_archive BOOLEAN DEFAULT true,
    last_cleanup_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Insert default retention policies
INSERT INTO retention_policies (table_name, retention_days, archive_enabled) VALUES
('operation_logs', 90, true),
('simulation_time_series', 180, true),
('test_time_series', 365, true),
('forward_simulations', 365, false),
('reverse_simulations', 365, false),
('test_results', 730, false);

-- ============================================
-- TRIGGERS FOR UPDATED_AT
-- ============================================

CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_work_orders_updated_at BEFORE UPDATE ON work_orders
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_test_results_updated_at BEFORE UPDATE ON test_results
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ============================================
-- VIEWS FOR COMMON QUERIES
-- ============================================

-- Active simulations with user info
CREATE VIEW v_active_simulations AS
SELECT
    fs.id,
    wo.work_order_number,
    u.username,
    u.full_name,
    fs.nc_amount,
    fs.peak_pressure,
    fs.peak_time,
    fs.created_at
FROM forward_simulations fs
JOIN users u ON fs.user_id = u.id
LEFT JOIN work_orders wo ON fs.work_order_id = wo.id
WHERE fs.status = 'completed'
ORDER BY fs.created_at DESC;

-- Test results summary
CREATE VIEW v_test_results_summary AS
SELECT
    tr.id,
    wo.work_order_number,
    u.username,
    tr.tester_id,
    td.device_name,
    tr.test_date,
    COUNT(trf.id) as file_count,
    tr.created_at
FROM test_results tr
JOIN users u ON tr.user_id = u.id
LEFT JOIN work_orders wo ON tr.work_order_id = wo.id
LEFT JOIN test_devices td ON tr.test_device_id = td.id
LEFT JOIN test_result_files trf ON tr.id = trf.test_result_id
GROUP BY tr.id, wo.work_order_number, u.username, tr.tester_id, td.device_name, tr.test_date, tr.created_at
ORDER BY tr.created_at DESC;

-- ============================================
-- COMMENTS
-- ============================================

COMMENT ON TABLE users IS 'System users with authentication and role-based access';
COMMENT ON TABLE work_orders IS 'Work orders linking simulations and tests';
COMMENT ON TABLE forward_simulations IS 'Forward simulations (正向仿真) predicting PT curves';
COMMENT ON TABLE reverse_simulations IS 'Reverse simulations (逆向仿真) predicting formulation';
COMMENT ON TABLE test_results IS 'Experimental test results (实验结果)';
COMMENT ON TABLE pt_comparisons IS 'PT curve comparisons between simulation and test data';
COMMENT ON TABLE operation_logs IS 'Complete audit trail of all user operations';
COMMENT ON TABLE archive_batches IS 'Tracking for data archived to Parquet files';
COMMENT ON TABLE retention_policies IS 'Data retention and archival policies';
