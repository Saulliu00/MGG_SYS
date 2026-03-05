# Legend Position Diagnosis & Fix Plan

**Date:** 2026-03-04  
**Issue:** 正向 simulation figure legend appears on the right side instead of bottom-right corner  
**Status:** 🔍 Diagnosis Complete

---

## Issue Description

**Current Behavior:**
- Legend appears on the **right side** of the 正向 simulation chart
- User expects legend at **bottom-right corner** (like comparison charts)

**Expected Behavior:**
- Legend should be anchored to the **bottom-right corner inside** the plot area

---

## Root Cause Analysis

### ✅ Backend Configuration: CORRECT

**Test Results:**
```bash
$ python test_legend_position.py

✅ Legend configuration found:
{
  "x": 0.99,
  "y": 0.01,
  "xanchor": "right",
  "yanchor": "bottom"
}

✅ CORRECT: Legend is configured for bottom-right corner
```

**Files Checked:**

1. **`app/config/plot_config.py`** (commit 8fd3e20)
   ```python
   LEGEND_CONFIG = {
       'x': 0.99,        # 99% from left (far right)
       'y': 0.01,        # 1% from bottom (near bottom)
       'xanchor': 'right',   # Anchor RIGHT edge of legend box
       'yanchor': 'bottom',  # Anchor BOTTOM edge of legend box
       ...
   }
   ```

2. **`app/utils/plotter.py`**
   - `create_simulation_chart()` ✅ Uses `LEGEND_CONFIG`
   - `create_comparison_chart()` ✅ Uses `LEGEND_CONFIG`
   - `create_multi_run_chart()` ✅ Uses `LEGEND_CONFIG`

### ❌ Probable Root Causes

#### 1. **Browser Cache (Most Likely)**

**Symptoms:**
- Backend has correct configuration
- User sees old position
- Recent commits (8fd3e20) changed legend position

**Why:**
- Browser cached the chart JSON from previous page load
- Old chart had `x=0.7, y=0.1, no anchors` → appeared middle-right
- New configuration not loaded by browser

#### 2. **Plotly Rendering Issue**

**Possibility:**
- Plotly.js version 2.27.0 might have different rendering
- Legend box size calculation might push it outside desired area

#### 3. **Coordinate System Confusion**

**Plotly Coordinate System:**
- `x` and `y` are in "paper" coordinates (0 to 1)
- `x=0.99` = 99% from left edge
- `y=0.01` = 1% from bottom edge
- With `xanchor='right'`, the **right edge** of legend is at x=0.99
- With `yanchor='bottom'`, the **bottom edge** of legend is at y=0.01

**Visual:**
```
Plot Area (normalized coordinates)
┌─────────────────────────────┐ y=1 (top)
│                             │
│                             │
│                      ┌──────┤ ← Legend box
│                      │Legend│   Right edge at x=0.99
│                      │      │   Bottom edge at y=0.01
└──────────────────────┴──────┘ y=0 (bottom)
x=0                    x=0.99  x=1
```

This **IS** bottom-right corner positioning.

---

## Diagnosis Checklist

- [x] Backend configuration verified (CORRECT)
- [x] Plotter.py code verified (CORRECT)
- [x] Test chart generated successfully (CORRECT)
- [ ] Frontend browser cache issue suspected
- [ ] Visual positioning needs user verification

---

## Fix Plan

### Option 1: Hard Refresh (Quick Fix)

**User Action:**
```bash
1. Open MGG_SYS in browser
2. Navigate to 正向 (Forward Simulation) page
3. Hard refresh: Ctrl+F5 (Windows/Linux) or Cmd+Shift+R (Mac)
4. Run a simulation
5. Verify legend is at bottom-right
```

**Expected Result:**
- Legend appears at bottom-right corner of plot ✅
- If still wrong → proceed to Option 2

---

### Option 2: Clear Browser Cache

**Steps:**
1. **Chrome:**
   - Settings → Privacy and security → Clear browsing data
   - Select "Cached images and files"
   - Clear data

2. **Firefox:**
   - Settings → Privacy & Security → Clear Data
   - Select "Cached Web Content"
   - Clear

3. **Reload page and test**

---

### Option 3: Update Cache-Busting Version (Code Fix)

**If Options 1-2 don't work, this is a more permanent solution.**

**Problem:**
- HTML might be caching Plotly chart configurations
- Need to force browser to re-fetch chart data

**Solution:**
Add version parameter to API endpoints or force chart re-render.

**Files to Modify:**

**1. Update `app/templates/simulation/index.html`**

Add cache-busting to chart div:
```html
<!-- Add timestamp or version to force re-render -->
<div id="chartDiv" data-version="20260304"></div>
```

**2. Update `app/static/js/simulation.js`**

Force Plotly to use new layout:
```javascript
// After creating chart JSON
Plotly.newPlot('chartDiv', chartData.data, chartData.layout, {
    responsive: true,
    displayModeBar: true
});

// Force layout update
Plotly.relayout('chartDiv', {
    'legend.x': 0.99,
    'legend.y': 0.01,
    'legend.xanchor': 'right',
    'legend.yanchor': 'bottom'
});
```

---

### Option 4: Verify Plotly Version Compatibility

**Check if issue is version-specific:**

**File:** `app/templates/base.html`
```html
<!-- Current version -->
<script src="https://cdn.plot.ly/plotly-2.27.0.min.js"></script>

<!-- Try latest version (if needed) -->
<script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
```

---

### Option 5: Alternative Legend Positioning

**If user wants legend OUTSIDE the plot (external bottom-right):**

**Modify `app/config/plot_config.py`:**

```python
# Current (inside plot area)
LEGEND_CONFIG = {
    'x': 0.99,
    'y': 0.01,
    'xanchor': 'right',
    'yanchor': 'bottom',
    ...
}

# Alternative (outside plot, below chart)
LEGEND_CONFIG = {
    'orientation': 'h',  # Horizontal legend
    'x': 0.5,            # Centered
    'y': -0.15,          # Below plot area
    'xanchor': 'center',
    'yanchor': 'top',
    ...
}
```

**Visual:**
```
┌─────────────────────────────┐
│         Plot Area           │
│                             │
│                             │
└─────────────────────────────┘
    [仿真数据] Legend Below    ← Alternative
```

---

## Testing Steps

### Step 1: Verify Current Configuration

```bash
cd /home/saul/.openclaw/workspace/MGG_SYS
source venv/bin/activate
python test_legend_position.py
```

**Expected Output:**
```
✅ CORRECT: Legend is configured for bottom-right corner
```

### Step 2: Clear Browser Cache & Test

1. Hard refresh browser (Ctrl+F5)
2. Navigate to 正向 page
3. Run a simulation with any parameters
4. Observe legend position

**Verify:**
- [ ] Legend is at bottom-right corner of plot
- [ ] Legend does not overlap with data lines
- [ ] Legend is readable with white/transparent background

### Step 3: Visual Comparison

**正向 Chart:**
- Legend should be: ✅ Bottom-right corner inside plot

**对比图 Chart:**
- Legend should be: ✅ Bottom-right corner inside plot (same position)

**工单查询 Chart:**
- Legend should be: ✅ Bottom-right corner inside plot (same position)

---

## Expected vs Actual

### What the Code Says (Backend)

```python
# LEGEND_CONFIG in plot_config.py
x = 0.99       # Right side (99% from left)
y = 0.01       # Bottom (1% from bottom)
xanchor = 'right'    # Right edge of legend box
yanchor = 'bottom'   # Bottom edge of legend box
```

**Expected Rendering:**
```
Plot Area
┌─────────────────────────────┐
│                             │
│                             │
│                      ┌─────┐│ ← Legend here
│                      │仿真数据││   (bottom-right)
└──────────────────────┴─────┴┘
```

### What User Sees (Frontend - Suspected)

If user sees legend "on the right" (middle-right):
```
Plot Area
┌─────────────────────────────┐
│                      ┌─────┐│ ← Legend here
│                      │仿真数据││   (middle-right)
│                      └─────┘│
│                             │
└─────────────────────────────┘
```

**This would indicate browser cache showing OLD configuration:**
```python
# OLD LEGEND_CONFIG (before commit 8fd3e20)
x = 0.7        # Middle-ish right
y = 0.1        # Lower-middle
# No xanchor/yanchor → defaults to legend center at (x,y)
```

---

## Recommended Action Plan

### Immediate (User Side)

1. ✅ **Hard refresh browser** (Ctrl+F5 or Cmd+Shift+R)
2. ✅ **Clear browser cache** if hard refresh doesn't work
3. ✅ **Test on different browser** to rule out browser-specific issue

### Verification

```bash
# After clearing cache, verify in browser console:
1. Open Developer Tools (F12)
2. Go to Network tab
3. Clear network log
4. Run simulation
5. Check chart JSON response for legend config
```

### Code Fix (If Browser Cache Not the Issue)

**If hard refresh doesn't fix it, implement Option 3:**

1. Add explicit `Plotly.relayout()` call in JavaScript
2. Force legend configuration on every chart render
3. Add cache-busting version to chart div

---

## Success Criteria

- [ ] Legend appears at **bottom-right corner** of plot area
- [ ] Legend is **inside** the plot (not floating outside)
- [ ] Legend **does not overlap** critical data
- [ ] Consistent across all chart types (正向, 对比图, 工单查询)
- [ ] Works after browser refresh

---

## Notes

**Commit History:**
- `8fd3e20` - Fixed legend anchors to bottom-right
- `7cf8a7b` - Added legend to simulation chart
- Earlier - Legend was at (0.7, 0.1) without anchors

**Plotly Version:**
- Current: 2.27.0
- Compatible with legend anchor properties

**Browser Cache Issue Precedent:**
- Similar issue occurred with work_order.js (fixed with cache-busting)
- Browser cache is a known issue after git pull

---

**Created:** 2026-03-04  
**Updated:** 2026-03-04  
**Status:** Awaiting user verification after hard refresh

