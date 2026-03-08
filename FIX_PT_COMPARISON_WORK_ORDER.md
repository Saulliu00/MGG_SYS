# Fix: PT曲线对比 Not Finding Saved Experimental Data

**Date:** 2026-03-05
**Issue:** Experimental data saved from "真实数据储存" was not appearing in "PT曲线对比" tab.

---

## Root Cause

When saving experimental data from "真实数据储存" (Real Data Storage):
1. Backend creates a **stub Simulation** record with `work_order` field populated
2. All **recipe fields are NULL** (ignition_model, nc_type_1, nc_usage_1, etc.)
3. TestResult is linked to this stub simulation

When searching for test data in "PT曲线对比" (PT Curve Comparison):
1. Backend searches for Simulations matching **recipe parameters**
2. Stub simulation has NULL recipe fields → **no match**
3. Test data not found

---

## Solution Implemented

### Backend Fix (simulation_service.py)

Enhanced `find_and_average_recipe_test_data()` with **two-phase search**:

```python
def find_and_average_recipe_test_data(self, user_id: int, params: Dict) -> Dict:
    # Phase 1: Match by recipe parameters (existing logic)
    matching_sims = self._build_recipe_query(params).all()
    sim_ids = [s.id for s in matching_sims]
    
    # Phase 2: ALSO match by work_order if provided (NEW!)
    work_order = params.get('work_order')
    if work_order:
        work_order_sims = Simulation.query.filter_by(work_order=work_order).all()
        # Add unique simulation IDs (avoid duplicates)
        sim_ids.extend([s.id for s in work_order_sims if s.id not in sim_ids])
    
    # Find test results from all matched simulations
    test_results = TestResult.query.filter(
        TestResult.simulation_id.in_(sim_ids)
    ).all()
    
    # ... rest of averaging logic
```

**Key improvement:** Now searches BOTH by:
- Recipe parameters (NC type, GP type, usage, shell, etc.)
- Work order number (if provided)

---

### Frontend Fix (index.html + simulation.js)

Added **work order search box** in PT曲线对比 tab:

```html
<div style="margin-bottom: 1rem; padding: 0.75rem; background: #f8f9fa; border-radius: 8px;">
    <label>
        <i class="fas fa-search"></i> 搜索工单号 (选填):
    </label>
    <div style="display: flex; gap: 0.5rem;">
        <input type="text" id="comparisonWorkOrderInput" 
               placeholder="输入工单号搜索实验数据，留空则仅按配方参数搜索">
        <button onclick="loadRecipeTestData()">
            <i class="fas fa-sync-alt"></i> 刷新数据
        </button>
    </div>
    <div style="font-size: 0.78rem; color: #7f8c8d; margin-top: 0.3rem;">
        💡 系统将查找匹配当前配方参数的实验数据。若指定工单号，还会包含该工单的所有实验数据。
    </div>
</div>
```

Updated `loadRecipeTestData()` JavaScript function to include work order:

```javascript
async function loadRecipeTestData() {
    // Collect recipe parameters from form
    const params = {};
    // ... collect form data ...
    
    // ALSO include work order from comparison tab search box
    const comparisonWorkOrderInput = document.getElementById('comparisonWorkOrderInput');
    if (comparisonWorkOrderInput && comparisonWorkOrderInput.value.trim()) {
        params['work_order'] = comparisonWorkOrderInput.value.trim();
    }
    
    // Send to backend
    // ...
}
```

---

## How to Use (User Guide)

### Scenario 1: Upload experimental data, then compare

**Step 1:** Upload experimental data in "真实数据储存"
- Enter work order number (e.g., `WO001`)
- Upload Excel file
- Click "确认上传"

**Step 2:** Run simulation in "正向仿真"  
- Fill in recipe parameters
- Click "计算" to run simulation

**Step 3:** Compare in "PT曲线对比"
- Switch to "PT曲线对比" tab
- Enter same work order (`WO001`) in the search box
- Click "刷新数据"
- Chart will show simulation vs experimental data overlay

---

### Scenario 2: Compare historical data

**Given:** Experimental data was uploaded months ago with work order `WO-HISTORICAL-123`

**To compare:**
1. Run a new simulation with similar recipe parameters
2. Switch to "PT曲线对比" tab
3. Enter `WO-HISTORICAL-123` in the work order search box
4. Click "刷新数据"
5. Historical experimental data will appear

---

### Scenario 3: Auto-match by recipe only

**Given:** Multiple experimental datasets with various work orders, all with same recipe

**To compare:**
1. Run simulation with matching recipe parameters
2. Switch to "PT曲线对比" tab
3. **Leave work order search box empty**
4. System automatically finds all experimental data matching recipe parameters
5. Data from ALL matching work orders is averaged and displayed

---

## Search Behavior Summary

| Search Criteria | Finds |
|----------------|-------|
| Recipe params only (no work order) | All test data with matching recipe (any work order) |
| Recipe params + work order | Test data matching recipe **OR** matching work order |
| Work order only (no recipe) | Not recommended - requires recipe params |

---

## Technical Notes

### Database Schema (unchanged)

```sql
-- Simulation table (parent)
CREATE TABLE simulation (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL,
    work_order VARCHAR(50),  -- Can be NULL for stub simulations
    ignition_model VARCHAR(50),  -- Can be NULL
    nc_type_1 VARCHAR(50),  -- Can be NULL
    nc_usage_1 FLOAT,  -- Can be NULL
    -- ... other recipe fields ...
    FOREIGN KEY (user_id) REFERENCES user(id)
);

-- TestResult table (child)
CREATE TABLE test_result (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL,
    simulation_id INTEGER,  -- Links to simulation (can be stub)
    filename VARCHAR(255),
    file_path VARCHAR(500),
    data TEXT,  -- JSON: {time: [...], pressure: [...]}
    FOREIGN KEY (simulation_id) REFERENCES simulation(id)
);
```

**Key insight:** TestResult doesn't store `work_order` directly. It inherits it through `simulation_id` foreign key.

---

## Files Modified

1. **Backend:**
   - `app/services/simulation_service.py` - Enhanced search logic

2. **Frontend:**
   - `app/templates/simulation/index.html` - Added work order search box
   - `app/static/js/simulation.js` - Updated loadRecipeTestData() function

---

## Testing Checklist

- [x] Backend search logic (two-phase: recipe + work order)
- [x] Frontend UI (work order input field in comparison tab)
- [x] JavaScript integration (send work order to backend)
- [ ] End-to-end user flow testing
- [ ] Edge case: multiple work orders with same recipe
- [ ] Edge case: work order with no recipe parameters
- [ ] Cross-browser testing

---

## Future Enhancements

1. **Work order autocomplete:**
   - Add dropdown showing all available work orders
   - Populated from distinct `Simulation.work_order` values

2. **Better stub simulation:**
   - When uploading experimental data, optionally capture basic recipe info
   - Populate stub simulation with partial recipe parameters

3. **Direct TestResult search:**
   - Add `work_order` field directly to `TestResult` table
   - Avoid dependency on stub Simulation records

4. **Visual indicator:**
   - Show which work orders contributed data to the averaged curve
   - Display count: "Found 3 datasets from work orders: WO001, WO002, WO003"

---

## Commit Message

```
fix: PT curve comparison now finds experimental data by work order

Problem:
- Experimental data saved with work order in 真实数据储存 was not found
- Stub simulations had NULL recipe fields, so recipe-based search failed

Solution:
- Backend: Two-phase search (recipe params + work order)
- Frontend: Added work order search box in PT comparison tab
- Users can now search by work order to find historical experimental data

Closes: #[issue number if applicable]
```

---

**Status:** ✅ Fix complete and ready for testing
**Next Step:** End-to-end user acceptance testing
