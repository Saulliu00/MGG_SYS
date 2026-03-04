# Work Order Query Feature Testing Report

**Date:** 2026-03-03  
**Feature:** 工单查询 (Work Order Query)  
**Status:** ⚠️ **Frontend Bug Confirmed**

## Issue Description

When users click on a work order in the left column, the PT curves should display in the middle column and statistics should appear in the right column. Currently, **nothing happens** when clicking a work order.

## Backend Status: ✅ WORKING

Tested the backend API directly with Python:

```python
detail = app.work_order_service.get_work_order_detail('WO-2026-001')
```

**Results:**
- ✅ Backend service returns correct data structure
- ✅ Chart has `data` and `layout` keys (Plotly format)
- ✅ 3 PT curve traces with 700 points each
- ✅ Statistics calculated correctly (mean, std, CV)
- ✅ No Python errors or exceptions

## Frontend Status: ❌ **BROKEN**

### Symptoms:
1. Work orders display correctly in left column
2. Clicking a work order does NOT trigger any action
3. No API call to `/work_order/<work_order>/detail` in Flask logs
4. No JavaScript errors in browser console
5. Chart remains empty, statistics panel shows "请在左侧选择一个工单"

### Root Cause Investigation

#### File: `app/static/js/work_order.js`

The `selectWorkOrder()` function is defined and should be called `onclick`:

```javascript
async function selectWorkOrder(workOrder) {
    selectedWorkOrder = workOrder;
    // ... rest of function
}
```

#### File: `app/templates/work_order/index.html`

The HTML template generates work order items with:

```javascript
onclick="selectWorkOrder(${JSON.stringify(wo.work_order)})"
```

###  Suspected Issues:

1. **CSRFToken Function Missing**: The JavaScript calls `getCsrfToken()` but this function may not be defined
2. **Plotly Not Loaded**: The `Plotly.newPlot()` calls may fail if Plotly.js is not loaded
3. **Event Handler Not Binding**: The `onclick` attribute may not be triggering the function

## Test Data Created

Successfully populated database with 3 work orders:

| Work Order | Ignition | NC Type | Test Results | Peak Pressure (Mean) | CV |
|------------|----------|---------|--------------|---------------------|------|
| WO-2026-001 | 115 | E (450mg) | 3 runs | 3.688 MPa | 5.42% |
| WO-2026-002 | 116 | F (500mg) | 5 runs | 2.959 MPa | 1.28% |
| WO-2026-003 | 117 | D (400mg) | 2 runs | 3.617 MPa | 4.83% |

## Next Steps to Fix

### 1. Check CSRF Token Function

Look in `app/templates/base.html` or JavaScript files for:
```javascript
function getCsrfToken() {
    // ...
}
```

### 2. Verify Plotly.js is Loaded

Check `app/templates/base.html` or `work_order/index.html` for:
```html
<script src="https://cdn.plotly.com/plotly-latest.min.js"></script>
```

### 3. Test Manual API Call

Open browser console and manually call:
```javascript
fetch('/work_order/WO-2026-001/detail')
    .then(r => r.json())
    .then(data => console.log(data));
```

### 4. Add Debug Logging

Add to `selectWorkOrder()`:
```javascript
async function selectWorkOrder(workOrder) {
    console.log('selectWorkOrder called with:', workOrder);
    // ... rest
}
```

## Expected Behavior

After clicking "WO-2026-001":

1. **Left column**: Work order item highlights in blue
2. **Middle column**: Displays 3 overlaid PT curves (blue, red, green)
3. **Right column**: Shows table with:
   ```
   实验次数: 3
   
   文件名                      峰值压力(MPa)  峰值时间(ms)
   WO-2026-001_run_01.xlsx     3.465         2.070
   WO-2026-001_run_02.xlsx     3.868         2.076
   WO-2026-001_run_03.xlsx     3.671         1.946
   
   均值                        3.688         2.031
   标准差                      0.200         0.075
   变异系数                    5.42%         3.69%
   ```

## Files to Check

1. ✅ `/app/routes/work_order.py` - Backend routes WORKING
2. ✅ `/app/services/work_order_service.py` - Service layer WORKING
3. ✅ `/app/utils/plotter.py` - Chart generation WORKING
4. ❌ `/app/static/js/work_order.js` - **NEEDS INVESTIGATION**
5. ❌ `/app/templates/work_order/index.html` - **CHECK FOR PLOTLY SCRIPT TAG**
6. ❌ `/app/templates/base.html` - **CHECK FOR CSRF FUNCTION**

## Testing Environment

- Server: http://127.0.0.1:5001
- Admin Login: `admin` / `gseieSzQbnfF_Een`
- Database: SQLite (instance/simulation_system.db)
- Flask Debug Mode: ON

---

**Next Action:** Check `base.html` and `work_order/index.html` for missing dependencies.
