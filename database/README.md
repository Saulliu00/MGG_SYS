# MGG Database Architecture

## Overview

The MGG Simulation System uses a **Hot-Cold Architecture**:
- **Hot Storage**: PostgreSQL for active data and real-time queries
- **Cold Storage**: Parquet files for archived historical data

This design balances performance, cost, and data retention requirements.

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    Application Layer                         │
│                  (Flask + SQLAlchemy)                        │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ├──────────────┬──────────────────────────┐
                     │              │                          │
            ┌────────▼────────┐  ┌──▼──────────────┐  ┌──────▼────────┐
            │  PostgreSQL     │  │  Archive        │  │  File         │
            │  (Hot Data)     │  │  Service        │  │  Storage      │
            │  90-365 days    │  │                 │  │  (.xlsx)      │
            └────────┬────────┘  └──┬──────────────┘  └───────────────┘
                     │              │
                     │         ┌────▼────────────────┐
                     │         │  Parquet Archive    │
                     └────────►│  (Cold Data)        │
                               │  > 365 days         │
                               └─────────────────────┘
```

## Database Schema

### Core Tables

#### Users & Authentication
- `users` - User accounts with RBAC (admin, user, engineer)
- `operation_logs` - Complete audit trail of all operations

#### Configuration
- `igniter_types` - Igniter type catalog
- `nc_types` - NC type catalog with physical properties
- `gp_types` - GP type catalog with physical properties
- `test_devices` - Test device registry

#### Work Management
- `work_orders` - Work orders linking simulations and tests

#### Simulations
- `forward_simulations` - Forward simulation metadata (正向仿真)
- `simulation_time_series` - PT curve data from simulations
- `reverse_simulations` - Reverse simulation metadata (逆向仿真)

#### Test Results
- `test_results` - Test result metadata (实验结果)
- `test_result_files` - Uploaded test files (.xlsx)
- `test_time_series` - PT curve data from tests

#### Analysis
- `pt_comparisons` - Comparison between simulation and test data

#### Archive Management
- `archive_batches` - Tracking for archived Parquet files
- `retention_policies` - Data retention configuration
- `model_versions` - ML model version tracking

## Data Flow

### 1. Forward Simulation (正向仿真)
```
User Input (NC, GP, etc.)
    ↓
forward_simulations (metadata)
    ↓
simulation_time_series (PT curve)
    ↓
[After 180 days] → Parquet Archive
```

### 2. Test Results (实验结果)
```
Upload .xlsx files
    ↓
test_results (metadata)
    ↓
test_result_files (file info)
    ↓
test_time_series (parsed PT curve)
    ↓
[After 365 days] → Parquet Archive
```

### 3. PT Curve Comparison (PT曲线对比)
```
Select Simulation + Test Data
    ↓
pt_comparisons (metrics: RMSE, correlation, etc.)
```

## Data Retention Strategy

| Table | Hot Retention | Archive | Delete After Archive |
|-------|--------------|---------|---------------------|
| operation_logs | 90 days | Yes | Yes |
| simulation_time_series | 180 days | Yes | Yes |
| test_time_series | 365 days | Yes | Yes |
| forward_simulations | 365 days | No | No (keep metadata) |
| reverse_simulations | 365 days | No | No (keep metadata) |
| test_results | 730 days | No | No (keep metadata) |

**Strategy**:
- Time series data (bulk) → Archive to Parquet and delete
- Metadata (lightweight) → Keep in PostgreSQL for queries
- Operation logs → Archive after 90 days for compliance

## Parquet Archive Structure

```
parquet_archive/
├── simulation_time_series/
│   ├── 2024-Q1.parquet
│   ├── 2024-Q2.parquet
│   └── 2024-Q3.parquet
├── test_time_series/
│   ├── 2024-Q1.parquet
│   ├── 2024-Q2.parquet
│   └── 2024-Q3.parquet
└── operation_logs/
    ├── 2024-01.parquet
    ├── 2024-02.parquet
    └── 2024-03.parquet
```

**Parquet Benefits**:
- **Compression**: 5-10x smaller than raw data
- **Columnar**: Fast analytics queries
- **Portable**: Can be read by pandas, Spark, DuckDB
- **Cost-effective**: Cheap storage for historical data

## Indexes Strategy

### Primary Indexes
- All `id` columns (primary keys)
- Foreign key columns for joins

### Query Optimization Indexes
- `users.username`, `users.email` - Login queries
- `work_orders.work_order_number` - Work order lookup
- `*_simulations.created_at DESC` - Recent simulations
- `operation_logs.created_at DESC` - Recent activity
- Composite: `operation_logs(user_id, log_type)` - User activity by type

### Time Series Indexes
- `(simulation_id, sequence_number)` - Ordered curve data
- `(test_result_id, sequence_number)` - Ordered test data

## Views

### v_active_simulations
Quick view of recent completed simulations with user info.

### v_test_results_summary
Summary of test results with file counts and device info.

## Installation

### 1. Install PostgreSQL
```bash
# macOS
brew install postgresql@15
brew services start postgresql@15

# Ubuntu
sudo apt-get install postgresql-15
```

### 2. Create Database
```bash
createdb mgg_simulation
```

### 3. Run Schema
```bash
psql mgg_simulation < database/schema.sql
```

### 4. Install Python Dependencies
```bash
pip install psycopg2-binary sqlalchemy pandas pyarrow
```

## Connection String

Development:
```
postgresql://user:password@localhost:5432/mgg_simulation
```

Production:
```
postgresql://user:password@prod-db.example.com:5432/mgg_simulation?sslmode=require
```

## Backup Strategy

### PostgreSQL Backups
```bash
# Daily backup
pg_dump -Fc mgg_simulation > backup_$(date +%Y%m%d).dump

# Restore
pg_restore -d mgg_simulation backup_20240115.dump
```

### Parquet Archive Backups
- Store Parquet files in S3/object storage
- Enable versioning for disaster recovery
- Parquet files are immutable (no updates)

## Migration Path from SQLite

See `database/migrate_from_sqlite.py` for migration script.

## Performance Tuning

### PostgreSQL Configuration
```sql
-- Increase shared buffers (25% of RAM)
ALTER SYSTEM SET shared_buffers = '2GB';

-- Increase work memory for sorting
ALTER SYSTEM SET work_mem = '64MB';

-- Enable query planner statistics
ALTER SYSTEM SET track_activities = on;
ALTER SYSTEM SET track_counts = on;
```

### Partitioning (Future)
For very large datasets, consider partitioning by date:
```sql
-- Partition simulation_time_series by month
CREATE TABLE simulation_time_series_2024_01 PARTITION OF simulation_time_series
FOR VALUES FROM ('2024-01-01') TO ('2024-02-01');
```

## Monitoring

### Key Metrics
- Query performance (slow query log)
- Table sizes (`pg_total_relation_size`)
- Index usage (`pg_stat_user_indexes`)
- Archive batch success rate

### Queries
```sql
-- Table sizes
SELECT
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;

-- Unused indexes
SELECT
    schemaname,
    tablename,
    indexname,
    idx_scan
FROM pg_stat_user_indexes
WHERE idx_scan = 0
ORDER BY pg_relation_size(indexrelid) DESC;
```

## Security

### Access Control
- Use least privilege principle
- Separate read-only and read-write roles
- Enable row-level security for multi-tenant data

### Encryption
- Enable SSL/TLS for connections
- Encrypt backups
- Use pgcrypto for sensitive data fields

## Next Steps

1. Implement database connection pool (SQLAlchemy)
2. Create archival automation script
3. Build admin dashboard for database monitoring
4. Set up automated backups
5. Implement data validation triggers
