# MGG Database Architecture

## Overview

The MGG Simulation System uses **Flask-SQLAlchemy with SQLite** for data storage. The database tracks users, test recipes (parameter combinations), work orders (工单), uploaded experiment files, and simulation results.

## Database Schema

### 6 Tables

```
┌──────────┐     ┌──────────┐     ┌──────────────┐     ┌─────────────────┐
│   user   │────►│  recipe   │────►│  work_order  │────►│ experiment_file │
│          │     │           │     │              │     │  (multiple per  │
│ login &  │     │ full set  │     │ 工单: links  │     │   work order)   │
│ roles    │     │ of test   │     │ recipe +     │     └─────────────────┘
│          │     │ conditions│     │ files +      │
│          │     └───────────┘     │ metadata     │────►┌──────────────┐
│          │                       │              │     │  simulation  │
│          │──────────────────────►│              │     │  (PT curve   │
│          │                       └──────────────┘     │   results)   │
│          │                                            └──────────────┘
│          │──────────────────────────────────────────►┌──────────────┐
│          │                                           │ test_result  │
│          │                                           │ (PT compare) │
└──────────┘                                           └──────────────┘
```

---

### Table 1: `user`

User accounts with role-based access control.

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER PK | |
| username | VARCHAR(80) | Display name |
| employee_id | VARCHAR(120) UNIQUE NOT NULL | Login identifier (工号) |
| password_hash | VARCHAR(128) NOT NULL | Bcrypt hash |
| phone | VARCHAR(20) | |
| role | VARCHAR(20) NOT NULL | `admin`, `research_engineer`, `lab_engineer` |
| is_active | BOOLEAN | Account enabled/disabled |
| created_at | DATETIME | |

---

### Table 2: `recipe`

A complete set of test conditions. One row = one full combination of all parameters. Created when a research engineer clicks "生成工单" in the 正向 tab.

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER PK | |
| user_id | FK → user.id | Who created this recipe |
| ignition_model | VARCHAR(50) | 点火具型号 |
| nc_type_1 | VARCHAR(50) | NC类型1 |
| nc_usage_1 | FLOAT | NC用量1 (毫克) |
| nc_type_2 | VARCHAR(50) | NC类型2 |
| nc_usage_2 | FLOAT | NC用量2 (毫克) |
| gp_type | VARCHAR(50) | GP类型 |
| gp_usage | FLOAT | GP用量 (毫克) |
| shell_model | VARCHAR(50) | 管壳高度 (mm) |
| current_condition | VARCHAR(50) | 通电条件 |
| sensor_range | VARCHAR(50) | 传感器量程 |
| body_model | VARCHAR(50) | 容积 |
| equipment | VARCHAR(50) | 测试设备 |
| created_at | DATETIME | |

Dropdown options for these fields are hardcoded in HTML templates with a "自定义" (custom) option. Custom values are stored directly in the recipe row.

---

### Table 3: `work_order`

The 工单 is the core linking entity. It connects a recipe (test conditions) with experiment files and simulations, plus captures administrative metadata.

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER PK | |
| work_order_number | VARCHAR(50) UNIQUE NOT NULL | e.g. `WO202602181430225678` |
| recipe_id | FK → recipe.id NOT NULL | The test conditions |
| user_id | FK → user.id NOT NULL | Who created it |
| employee_id | VARCHAR(100) | 工号 |
| test_name | VARCHAR(200) | 测试名称 |
| notes | TEXT | 备注 |
| test_date | DATE | Test date |
| test_time | VARCHAR(10) | Test time |
| source | VARCHAR(20) | `simulation` (正向 tab) or `experiment` (实验结果 tab) |
| created_at | DATETIME | |
| updated_at | DATETIME | |

**Two creation paths:**
1. **正向 tab** — research engineer clicks "生成工单", work_order_number is auto-generated, `source='simulation'`
2. **实验结果 tab** — lab engineer manually types the work_order_number, `source='experiment'`

---

### Table 4: `experiment_file`

Each uploaded Excel file (time vs pressure data). Multiple files can belong to one work order — this is normal because chemical tests are repeated multiple times under the same conditions.

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER PK | |
| work_order_id | FK → work_order.id NOT NULL | Which 工单 this belongs to |
| user_id | FK → user.id NOT NULL | Who uploaded it |
| original_filename | VARCHAR(255) NOT NULL | User-facing filename |
| stored_filename | VARCHAR(255) NOT NULL | UUID-based name on disk |
| file_path | VARCHAR(500) NOT NULL | Full path on disk |
| file_size | INTEGER | Bytes |
| uploaded_at | DATETIME | |

---

### Table 5: `simulation`

Simulation results from the 正向 tab. Existing table with a new `work_order_id` FK.

| Column | Type | Description |
|--------|------|-------------|
| ... | ... | All existing columns unchanged |
| work_order_id | FK → work_order.id | NEW — links to work order (nullable for old data) |
| work_order | VARCHAR(50) | OLD — kept for backward compat |

---

### Table 6: `test_result`

Single file uploads from the "实际数据存储" tab in the 正向 page (for PT curve comparison). Separate workflow from batch experiment uploads. Unchanged.

---

## Relationships

```
recipe ◄──(1:1)── work_order ──(1:*)──► experiment_file
                      │
                      └──(1:*)──► simulation
```

- One `recipe` per `work_order` (the test conditions are fixed for a work order)
- Many `experiment_file` rows per `work_order` (multiple test runs)
- A `work_order` may have zero or more `simulation` results

---

## Data Flows

### Research Engineer — 正向 Simulation

```
1. Select parameters (点火具, NC, GP, 管壳, 通电条件, 传感器量程, 容积, 设备)
2. Click "生成工单" → auto-generate work order number
3. Click "计算"
4. Backend: recipe → work_order → simulation (with PT curve result)
```

### Lab Engineer — 实验结果 Upload

```
1. Type 工单号 (received from research engineer)
2. Fill metadata (工号, 测试设备, 日期, 时间)
3. Upload multiple .xlsx files (repeated test runs)
4. Backend: find/create work_order → create experiment_file rows
```

### Data Retrieval — Plotting

```
1. Look up work_order by number
2. JOIN recipe to see test conditions
3. Load experiment_file records → read Excel files
4. Plot individual PT curves or compute average
```

---

## Concurrency

The app supports multiple simultaneous users on the local network.

| Scenario | Handling |
|----------|----------|
| Two users create different work orders | No conflict — different rows |
| Two users upload files to the same work order | Safe — independent experiment_file rows |
| Concurrent reads + writes | SQLite WAL mode allows readers not to block writers |
| File upload failure | DB transaction rollback + cleanup file from disk |

**SQLite WAL mode** is enabled for concurrent read/write performance.

---

## Note on `database/` Directory

This directory also contains files for a planned PostgreSQL migration (`models.py`, `schema.sql`, `init_db.py`, `archive_manager.py`, etc.). These are **not connected** to the running Flask app. The active database models live in `app/models.py` using Flask-SQLAlchemy with SQLite.
