# Demo Folder Architecture

## Overview

The demo folder is a **standalone, self-contained demonstration system** that operates completely independently from the main MGG project.

## File Structure

```
demo/
├── demo.html                    # Main demo interface (standalone, no dependencies)
├── run_simulation.py           # Standalone simulation script
├── load_test_data.py           # Standalone data loader script
├── data/                       # Demo data files
│   └── 测试数据_NC50.xlsx      # Sample test data
├── temp/                       # Temporary upload files (auto-created, gitignored)
├── README.md                   # Demo guide
├── README_ISOLATION.md         # Isolation policy (IMPORTANT!)
├── ARCHITECTURE.md             # This file
├── DEMO_GUIDE.md              # User guide
├── EXCEL_FORMAT.md            # Excel file format documentation
└── other documentation files

```

## Component Independence

### 1. demo.html
- **Type**: Standalone HTML5/CSS3/JavaScript application
- **Dependencies**:
  - Bootstrap 5 (CDN)
  - Font Awesome (CDN)
  - Plotly.js (CDN)
  - No dependencies on main project
- **Features**:
  - Complete UI with login, simulation, comparison, logs
  - Can work with mock data if backend unavailable
  - localStorage for operation logs
  - All JavaScript code embedded in single file

### 2. run_simulation.py
- **Type**: Standalone Python script
- **Purpose**: Load ML models and generate PT curve predictions
- **Dependencies**:
  - Standard library: `pickle`, `json`, `sys`, `os`
  - External: `numpy`, `plotly`
  - **NO imports from main project**
- **Usage**: Called via subprocess from backend API
- **Input**: NC用量1 value, models path
- **Output**: JSON with plot data and statistics

### 3. load_test_data.py
- **Type**: Standalone Python script
- **Purpose**: Read Excel files and return plot data
- **Dependencies**:
  - Standard library: `json`, `sys`, `os`
  - External: `pandas`, `plotly`
  - **NO imports from main project**
- **Usage**: Called via subprocess from backend API
- **Input**: Excel file path
- **Output**: JSON with time/pressure data
- **Special**: Skips first 4 rows, uses columns 1 & 2

## Backend API Integration (Optional)

The demo optionally uses two Flask API endpoints:

### /simulation/predict
- Located in: `app/routes/simulation.py`
- Marked as: "no authentication required"
- Purpose: Executes `run_simulation.py` via subprocess
- **Isolation**: Calls standalone script, no business logic dependency

### /simulation/load_test_data
- Located in: `app/routes/simulation.py`
- Marked as: "no authentication required"
- Purpose: Executes `load_test_data.py` via subprocess
- **Isolation**: Calls standalone script, no business logic dependency

## Key Isolation Points

1. **No Code Sharing**: Demo scripts don't import from `app/`, `models/`, or any main project modules
2. **No Database Access**: Demo doesn't use SQLAlchemy or main project database
3. **No Authentication Dependency**: Demo endpoints bypass main project auth
4. **Separate Data**: Demo uses `demo/data/` for files, not main project storage
5. **Independent Operation**: Demo can run even if main project is broken

## Data Flow

### Simulation Flow
```
User clicks "仿真"
  → demo.html JavaScript
  → Fetch API call to localhost:5001/simulation/predict
  → Flask endpoint (app/routes/simulation.py)
  → Subprocess call to demo/run_simulation.py
  → Script loads models from /models folder
  → Returns JSON to endpoint
  → Returns JSON to demo.html
  → Plotly renders chart
```

### Data Comparison Flow
```
User uploads .xlsx file
  → demo.html JavaScript (FormData)
  → Fetch API call to localhost:5001/simulation/load_test_data
  → Flask endpoint (app/routes/simulation.py)
  → Saves file to demo/temp/
  → Subprocess call to demo/load_test_data.py
  → Script reads Excel (skips 4 rows, uses cols 1&2)
  → Returns JSON to endpoint
  → Deletes temp file
  → Returns JSON to demo.html
  → Plotly renders comparison chart
```

## Operating Modes

### Mode 1: With Backend (Full Features)
- Start Flask server: `python -m flask --app app run --port 5001`
- Open demo.html in browser
- Full simulation and data loading features work

### Mode 2: Standalone (Mock Data)
- Open demo.html directly in browser
- No backend needed
- Uses mock/placeholder data
- Navigation and UI fully functional

## Maintenance Guidelines

### When Updating Demo:
1. ✅ Only modify files in `demo/` folder
2. ✅ Test demo independently
3. ✅ Keep scripts standalone (no main project imports)
4. ✅ Document changes in demo README files

### When Updating Main Project:
1. ✅ Demo should NOT be affected
2. ✅ If changing API structure, update demo endpoints separately
3. ✅ Test that demo still works after main project changes
4. ✅ Keep demo endpoints marked "no authentication required"

## Version Independence

- **Demo Version**: Standalone HTML + Python scripts
- **Main Project Version**: Flask application with database
- **Independence**: Demo version updates don't affect main project and vice versa

## Summary

The demo folder is a **completely independent mini-application** designed for quick demonstrations without the complexity of the full system. It must remain isolated to ensure stability and ease of use.
