# Demo Folder Isolation Policy

## ⚠️ CRITICAL RULE: COMPLETE ISOLATION

The `demo/` folder is **COMPLETELY ISOLATED** from the main project and must remain independent at all times.

## Isolation Principles

### 1. **Demo is Self-Contained**
- All demo files exist only in the `demo/` folder
- Demo has its own standalone HTML, CSS, JavaScript, and Python scripts
- Demo does NOT import or use any code from `app/`, `models/`, or other project folders
- Demo operates independently with its own data and logic

### 2. **No Dependencies on Main Project**
- Demo does NOT rely on:
  - Flask application (`app/`)
  - Database models (`app/models.py`)
  - Main project routes (`app/routes/`)
  - Main project configuration (`config.py`)
  - Main project requirements (except for demo-specific scripts)

### 3. **Main Project Changes Don't Affect Demo**
- Changes to the main Flask application should NOT impact demo functionality
- Changes to database schema should NOT affect demo
- Changes to API endpoints in `app/routes/` should NOT break demo
- Demo continues to work even if main project is broken

### 4. **Demo-Specific Backend (Optional)**
- If demo needs backend functionality, it uses:
  - Standalone Python scripts in `demo/` folder (e.g., `run_simulation.py`, `load_test_data.py`)
  - Optional simple Flask endpoints created ONLY for demo purposes
  - These are clearly marked and isolated

## Current Demo Architecture

```
demo/
├── demo.html              # Standalone HTML interface (no dependencies)
├── run_simulation.py      # Standalone simulation script
├── load_test_data.py      # Standalone data loading script
├── data/                  # Demo data files
├── temp/                  # Temporary files (auto-created)
└── README files           # Demo documentation
```

## Backend API for Demo

The demo currently uses two API endpoints:
- `/simulation/predict` - For running simulations
- `/simulation/load_test_data` - For loading test data

**Important Notes:**
1. These endpoints **require authentication** (`@login_required`) - user must be logged in
2. They call standalone Python scripts in `demo/` folder
3. They do NOT depend on main project business logic
4. The main project uses three roles: admin, lab_engineer, research_engineer

## Development Guidelines

### ✅ DO:
- Keep all demo code in `demo/` folder
- Use standalone scripts for demo functionality
- Document demo-specific features clearly
- Test demo independently from main project
- Use `demo/data/` for demo data files

### ❌ DON'T:
- Import from `app/` or other main project modules in demo scripts
- Share database connections between demo and main project
- Use main project models or business logic in demo
- Make demo depend on main project configuration
- Break demo when refactoring main project

## Quick Start (Demo Only)

To run the demo:
1. Open `demo/demo.html` in a browser
2. (Optional) Start Flask server for backend features: `python -m flask --app app run --port 5001`
3. Demo works with mock data even without backend

## Testing Isolation

Before any main project changes:
1. Test that demo still works
2. Verify demo has no imports from main project folders
3. Ensure demo can run standalone

## Summary

**The demo folder is a completely separate, standalone demonstration system that must remain independent and not break regardless of any changes made to the main project.**
