# User Guide: Finding Experimental Data in PT曲线对比

## 🐛 Problem You Were Having

You saved experimental data in **真实数据储存** (Real Data Storage), but when you went to **PT曲线对比** (PT Curve Comparison), the system couldn't find it.

---

## ✅ What I Fixed

### Backend Fix
- The system now searches **BOTH** by:
  1. Recipe parameters (NC type, GP type, usage, etc.)
  2. **Work order number** (NEW!)

### Frontend Fix  
- Added a **work order search box** in the PT曲线对比 tab
- Added a **"刷新数据"** (Refresh Data) button

---

## 📖 How to Use the Fix

### Example Workflow

#### Step 1: Upload Experimental Data in "真实数据储存"

```
┌─────────────────────────────────────┐
│  真实数据储存 Tab                    │
├─────────────────────────────────────┤
│  📄 关联工单号 (选填):              │
│  ┌─────────────────────────────┐   │
│  │ WO001                       │   │  ← Enter work order here
│  └─────────────────────────────┘   │
│                                     │
│  [Upload Excel file button]        │
│  [确认上传]                         │
└─────────────────────────────────────┘
```

**Important:** Remember the work order number you enter (e.g., `WO001`)

---

#### Step 2: Run Simulation (Optional)

Go to **正向仿真** tab and run a simulation with similar recipe parameters.

---

#### Step 3: Compare in "PT曲线对比"

```
┌─────────────────────────────────────┐
│  PT曲线对比 Tab                      │
├─────────────────────────────────────┤
│  🔍 搜索工单号 (选填):              │
│  ┌─────────────────────┐            │
│  │ WO001              │ [刷新数据] │  ← Enter same work order
│  └─────────────────────┘            │
│  💡 系统将查找匹配当前配方参数的实验数据。│
│     若指定工单号，还会包含该工单的所有实验│
│     数据。                            │
│                                     │
│  ┌─ PT曲线对比 ──────────────────┐  │
│  │                               │  │
│  │  [Chart showing:              │  │
│  │   🔵 Blue line = Simulation   │  │
│  │   🔴 Red line = Experimental] │  │
│  │                               │  │
│  └───────────────────────────────┘  │
└─────────────────────────────────────┘
```

**Key Actions:**
1. Enter `WO001` in the search box
2. Click **刷新数据** (Refresh Data)
3. Chart appears with both simulation and experimental data

---

## 🎯 Three Usage Scenarios

### Scenario A: Search by Work Order Only

**Use when:** You know the work order number and want to see that specific experimental data

**Steps:**
1. Go to PT曲线对比 tab
2. Enter work order (e.g., `WO001`) in search box
3. Click 刷新数据
4. **Result:** Shows experimental data from that work order

---

### Scenario B: Search by Recipe Parameters Only

**Use when:** You want to find ANY experimental data matching the current recipe, regardless of work order

**Steps:**
1. Fill in recipe parameters in 正向仿真 form
2. Run simulation
3. Go to PT曲线对比 tab
4. **Leave work order search box EMPTY**
5. System auto-searches when tab opens
6. **Result:** Shows averaged data from all matching recipes (from any work order)

---

### Scenario C: Search by Recipe + Work Order (Best)

**Use when:** You want to find data matching recipe AND include a specific work order

**Steps:**
1. Fill in recipe parameters
2. Run simulation  
3. Go to PT曲线对比 tab
4. Enter work order in search box
5. Click 刷新数据
6. **Result:** Shows data matching recipe **OR** matching work order (broadest search)

---

## 🔍 Search Logic Explained

The system now uses **two-phase search**:

```
Phase 1: Match by Recipe Parameters
├─ ignition_model
├─ nc_type_1, nc_usage_1
├─ nc_type_2, nc_usage_2
├─ gp_type, gp_usage
├─ shell_model
├─ current
└─ sensor_model

Phase 2: ALSO Match by Work Order (if provided)
└─ work_order

Result: UNION of both searches (no duplicates)
```

**Example:**

```
Scenario: You enter work order "WO001" in search box

Backend finds:
✓ Simulations matching recipe parameters → TestResults A, B, C
✓ Simulations with work_order="WO001"  → TestResults D, E

Final result: A, B, C, D, E (averaged)
```

---

## 💡 Pro Tips

### Tip 1: Use Consistent Work Order Format

When uploading experimental data, use a consistent format:
- ✅ Good: `WO001`, `WO002`, `WO-2026-03-05`
- ❌ Bad: `wo001`, `Work Order 1`, `test`

Exact match is required for searching!

---

### Tip 2: Auto-Match Feature

When you switch to PT曲线对比 tab, the system **automatically** searches for matching experimental data based on recipe parameters.

If it doesn't find any, you'll see:

```
┌───────────────────────────────┐
│  ⚠️ 暂无匹配实验数据           │
│                               │
│  当前配方尚无匹配的实验数据。  │
│  请先在「实际数据储存」中上传  │
│  实验文件，再进行 PT 曲线对比。│
│                               │
│  [前往上传]  [关闭]           │
└───────────────────────────────┘
```

**Solution:** Enter the work order in the search box and click 刷新数据

---

### Tip 3: Multiple Work Orders → Averaged Data

If your recipe matches experimental data from multiple work orders, the system:
1. Finds ALL matching TestResults
2. **Averages them** into a single curve
3. Displays the averaged curve

This gives you a representative curve from all available data!

---

## 🛠️ Troubleshooting

### Problem: "暂无匹配实验数据" even after entering work order

**Possible causes:**
1. Work order typo (check exact spelling)
2. Experimental data was not successfully uploaded
3. Uploaded data has no linked simulation record

**Solutions:**
1. Verify work order in 工单查询 tab
2. Re-upload experimental data in 真实数据储存
3. Check database directly (for admins)

---

### Problem: Chart shows simulation but not experimental data

**Possible causes:**
1. Work order doesn't match
2. Search box is empty and recipe params don't match

**Solutions:**
1. Enter work order in search box
2. Click 刷新数据 button manually
3. Verify recipe parameters match the uploaded experimental data

---

### Problem: Wrong experimental data appears

**Possible causes:**
1. Multiple datasets match the recipe
2. Work order search is too broad

**Solutions:**
1. Be more specific with work order
2. Check which work orders' data you actually want
3. Adjust recipe parameters to be more specific

---

## 📊 What Changed (Technical)

### Before Fix

```
User uploads data → Stub Simulation (work_order="WO001", recipe=NULL)
                     ↓
                  TestResult (linked to stub)

Later, user searches → Find simulations by recipe params
                       ↓
                    ❌ Stub has NULL recipe → No match → Data not found
```

---

### After Fix

```
User uploads data → Stub Simulation (work_order="WO001", recipe=NULL)
                     ↓
                  TestResult (linked to stub)

Later, user searches with work_order="WO001"
                       ↓
                    Phase 1: Find by recipe params (might find nothing)
                    Phase 2: Find by work_order="WO001" ✅ (finds stub!)
                       ↓
                    Merge results → TestResults found → Data displayed
```

---

## 🎉 Summary

**What you can now do:**
- ✅ Find experimental data by work order number
- ✅ Find experimental data by recipe parameters  
- ✅ Combine both search methods
- ✅ Compare historical data from months ago

**Key Interface Change:**
- New search box in PT曲线对比 tab with "刷新数据" button

**No database changes required:**
- Existing data works with new search logic

---

## 📞 Questions?

If you encounter issues:
1. Check this guide first
2. Verify work order spelling
3. Try manual refresh with 刷新数据 button
4. Check CHANGELOG.md for updates

**Happy analyzing! 📈**
