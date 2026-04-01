// Work Order Query (工单查询) — frontend logic

let allWorkOrders = [];      // full list from server
let selectedWorkOrder = null; // currently selected work_order string
let currentSort = 'peak_pressure'; // 'default' | 'peak_pressure' | 'peak_time'

// Escape HTML special characters to prevent XSS when inserting user data into innerHTML
function _escapeHtml(str) {
    return String(str)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;');
}

// ── Initialisation ────────────────────────────────────────────────────────────

window.addEventListener('load', function () {
    Plotly.newPlot('woChartDiv', [], {
        plot_bgcolor: 'white',
        paper_bgcolor: 'white',
        margin: { l: 60, r: 30, t: 30, b: 50 },
        xaxis: { title: 'Time (ms)', gridcolor: '#e0e0e0', showgrid: true },
        yaxis: { title: 'Pressure (MPa)', gridcolor: '#e0e0e0', showgrid: true }
    }, { responsive: true });
    loadWorkOrders();
});

// ── Work Order List ───────────────────────────────────────────────────────────

async function loadWorkOrders() {
    try {
        const resp = await fetch('/work_order/list', {
            headers: { 'X-CSRFToken': getCsrfToken() }
        });
        const data = await resp.json();
        if (data.success) {
            allWorkOrders = data.work_orders;
            renderWorkOrderList(_applySortToList(allWorkOrders));
        } else {
            _showListError('加载工单列表失败');
        }
    } catch (e) {
        console.error('loadWorkOrders error:', e);
        _showListError('网络错误，请刷新重试');
    }
}

function filterWorkOrders(query) {
    const q = query.trim().toLowerCase();
    const filtered = q
        ? allWorkOrders.filter(wo =>
            wo.work_order.toLowerCase().includes(q) ||
            wo.recipe_summary.toLowerCase().includes(q))
        : allWorkOrders;
    renderWorkOrderList(_applySortToList(filtered));
}

// ── Sort ──────────────────────────────────────────────────────────────────────

/**
 * Apply the current sort key to a list of work order objects.
 * Returns a new sorted array; does not mutate the input.
 *
 * Sort keys:
 *   'peak_pressure' — descending mean peak pressure (highest first)
 *   'peak_time'     — ascending mean peak time (earliest arrival first)
 *   'default'       — server order (created_at desc), no change
 *
 * Entries with no test data (null values) always sink to the bottom.
 */
function _applySortToList(list) {
    if (currentSort === 'peak_pressure') {
        return [...list].sort((a, b) => {
            const pa = a.mean_peak_pressure ?? -Infinity;
            const pb = b.mean_peak_pressure ?? -Infinity;
            return pb - pa; // desc
        });
    }
    if (currentSort === 'peak_time') {
        return [...list].sort((a, b) => {
            const ta = a.mean_peak_time ?? Infinity;
            const tb = b.mean_peak_time ?? Infinity;
            return ta - tb; // asc — earliest arrival first
        });
    }
    return list; // default: preserve server-side created_at desc order
}

/** Called by the sort dropdown's onchange handler. */
function sortWorkOrders(key) {
    currentSort = key;
    const q = document.getElementById('woSearchInput').value.trim().toLowerCase();
    const filtered = q
        ? allWorkOrders.filter(wo =>
            wo.work_order.toLowerCase().includes(q) ||
            wo.recipe_summary.toLowerCase().includes(q))
        : allWorkOrders;
    renderWorkOrderList(_applySortToList(filtered));
}

function renderWorkOrderList(list) {
    const container = document.getElementById('workOrderList');

    if (!list.length) {
        container.innerHTML =
            '<div style="color:#7f8c8d;text-align:center;padding:2rem;font-size:0.88rem;">' +
            '<i class="fas fa-inbox" style="font-size:1.8rem;display:block;margin-bottom:0.5rem;opacity:0.4;"></i>' +
            '暂无工单记录</div>';
        return;
    }

    container.innerHTML = list.map(wo => {
        const isActive = wo.work_order === selectedWorkOrder;
        const canDelete = CURRENT_USER_ROLE === 'admin' || wo.owner_id === CURRENT_USER_ID;
        const deleteBtn = canDelete
            ? `<button class="wo-delete-btn" data-work-order="${_escapeHtml(wo.work_order)}"
                       title="删除工单"
                       style="background:none;border:none;color:#aab2bd;cursor:pointer;
                              padding:0.15rem 0.3rem;border-radius:4px;font-size:0.8rem;
                              flex-shrink:0;line-height:1;"
                       onmouseover="this.style.color='#e74c3c'"
                       onmouseout="this.style.color='#aab2bd'">
                   <i class="fas fa-trash-alt"></i>
               </button>`
            : '';
        return `
        <div class="wo-item"
             data-work-order="${_escapeHtml(wo.work_order)}"
             style="padding:0.55rem 0.6rem; margin-bottom:0.4rem; border-radius:8px;
                    cursor:pointer; border:1px solid ${isActive ? '#667eea' : '#e8ecf0'};
                    background:${isActive ? '#eef2ff' : '#fff'};
                    transition:background 0.15s;">
            <div style="display:flex; align-items:center; gap:0.25rem;">
                <i class="fas fa-file-alt" style="color:#667eea; font-size:0.8rem; flex-shrink:0;"></i>
                <span style="font-weight:600; font-size:0.85rem; color:#2c3e50;
                             white-space:nowrap; overflow:hidden; text-overflow:ellipsis; flex:1;">
                    ${_escapeHtml(wo.work_order)}
                </span>
                ${deleteBtn}
            </div>
            <div style="font-size:0.76rem; color:#7f8c8d; margin-top:0.2rem;
                        white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">
                ${_escapeHtml(wo.recipe_summary || '—')}
            </div>
            <div style="font-size:0.73rem; color:#aab2bd; margin-top:0.1rem;">
                ${_escapeHtml(wo.created_at)}
            </div>
        </div>`;
    }).join('');

    // Single event delegation handler for both item click and delete button
    container.onclick = function(e) {
        const deleteBtn = e.target.closest('.wo-delete-btn');
        if (deleteBtn) {
            e.stopPropagation();
            deleteWorkOrder(deleteBtn.dataset.workOrder);
            return;
        }
        const item = e.target.closest('.wo-item');
        if (item) selectWorkOrder(item.dataset.workOrder);
    };
}

// ── Work Order Detail ─────────────────────────────────────────────────────────

async function selectWorkOrder(workOrder) {
    selectedWorkOrder = workOrder;
    renderWorkOrderList(
        document.getElementById('woSearchInput').value.trim()
            ? allWorkOrders.filter(w => w.work_order.toLowerCase().includes(
                document.getElementById('woSearchInput').value.trim().toLowerCase()))
            : allWorkOrders
    );

    // Show loading state
    const subtitle = document.getElementById('chartSubtitle');
    subtitle.style.display = '';
    subtitle.textContent = '加载中...';
    document.getElementById('statsPanel').innerHTML =
        '<div style="color:#7f8c8d;text-align:center;padding:3rem;">' +
        '<i class="fas fa-spinner fa-spin" style="font-size:1.5rem;"></i></div>';

    try {
        const resp = await fetch(`/work_order/${encodeURIComponent(workOrder)}/detail`, {
            headers: { 'X-CSRFToken': getCsrfToken() }
        });
        const data = await resp.json();

        if (!data.success) {
            _showDetailError(data.message || '加载失败');
            return;
        }

        document.getElementById('chartPanelTitle').textContent =
            `PT 曲线 — ${workOrder}`;
        document.getElementById('chartSubtitle').textContent =
            data.simulation.recipe_summary + ' · ' + data.simulation.created_at;

        renderChart(data.chart);
        renderStats(data.statistics, data.test_results);

    } catch (e) {
        console.error('selectWorkOrder error:', e);
        _showDetailError('网络错误，请重试');
    }
}

// ── Chart ─────────────────────────────────────────────────────────────────────

function renderChart(chartJson) {
    try {
        if (!chartJson || !chartJson.data || !chartJson.layout) {
            throw new Error('Invalid chart data structure');
        }
        Plotly.newPlot('woChartDiv', chartJson.data, chartJson.layout, { responsive: true });
    } catch (e) {
        console.error('Chart rendering failed:', e);
        document.getElementById('woChartDiv').innerHTML =
            '<div style="color:#e74c3c;text-align:center;padding:3rem;font-size:0.9rem;">' +
            '<i class="fas fa-exclamation-triangle" style="font-size:2rem;display:block;margin-bottom:0.5rem;"></i>' +
            '图表加载失败，请刷新重试</div>';
    }
}

// ── Statistics ────────────────────────────────────────────────────────────────

function renderStats(stats, testResults) {
    const panel = document.getElementById('statsPanel');
    const S = 'font-size:0.8rem;';  // shorthand

    if (!stats || stats.count === 0) {
        panel.innerHTML =
            '<div style="color:#7f8c8d;text-align:center;padding:3rem;font-size:0.9rem;">' +
            '<i class="fas fa-database" style="font-size:1.8rem;display:block;margin-bottom:0.5rem;opacity:0.4;"></i>' +
            '该工单暂无实验数据</div>';
        return;
    }

    // Helper: one labeled row
    function row(label, value, muted) {
        const c = muted ? '#7f8c8d' : '#2c3e50';
        return `<div style="display:flex;justify-content:space-between;align-items:baseline;
                             padding:0.2rem 0;${S}">
                    <span style="color:#95a5a6;">${label}</span>
                    <span style="color:${c};font-weight:${muted ? '400' : '600'};">${value}</span>
                </div>`;
    }

    // Per-run cards
    const runCards = testResults.map((tr, i) => {
        const peak = stats.peaks.find(p => p.filename === tr.filename);
        const peakP = peak ? peak.peak_pressure.toFixed(3) + ' MPa' : '—';
        const peakT = peak ? peak.peak_time.toFixed(3) + ' ms'  : '—';
        const canDelete = CURRENT_USER_ROLE === 'admin' || tr.user_id === CURRENT_USER_ID;
        const deleteBtn = canDelete
            ? `<button onclick="deleteRun(${tr.id}, ${JSON.stringify(selectedWorkOrder)})"
                       title="删除此记录"
                       style="background:none;border:none;color:#aab2bd;cursor:pointer;
                              padding:0.1rem 0.25rem;font-size:0.78rem;line-height:1;"
                       onmouseover="this.style.color='#e74c3c'"
                       onmouseout="this.style.color='#aab2bd'">
                   <i class="fas fa-times"></i>
               </button>`
            : '';

        return `
        <div style="padding:0.5rem 0.6rem; margin-bottom:0.4rem; border-radius:6px;
                    border:1px solid #e8ecf0; background:#fff;">
            <div style="display:flex;align-items:center;gap:0.2rem;margin-bottom:0.3rem;">
                <span style="font-size:0.7rem;background:#667eea;color:#fff;
                             padding:0.05rem 0.35rem;border-radius:10px;flex-shrink:0;">
                    R${i + 1}
                </span>
                <span style="${S}font-weight:600;color:#2c3e50;flex:1;
                             white-space:nowrap;overflow:hidden;text-overflow:ellipsis;"
                      title="${_escapeHtml(tr.filename)}">
                    ${_escapeHtml(tr.filename)}
                </span>
                ${deleteBtn}
            </div>
            ${row('峰值压力', peakP, false)}
            ${row('峰值时间', peakT, false)}
        </div>`;
    }).join('');

    // Aggregate section
    const aggSection = stats.count > 1 ? `
        <div style="margin-top:0.6rem; padding:0.5rem 0.6rem; border-radius:6px;
                    background:#f8f9fa; border:1px solid #dce1e7;">
            <div style="${S}font-weight:700;color:#2c3e50;margin-bottom:0.35rem;">综合统计</div>
            <div style="color:#bdc3c7;${S}margin-bottom:0.15rem;">均值</div>
            ${row('峰值压力', stats.mean_p.toFixed(3) + ' MPa', false)}
            ${row('峰值时间', stats.mean_t.toFixed(3) + ' ms',  false)}
            <div style="color:#bdc3c7;${S}margin-top:0.3rem;margin-bottom:0.15rem;">标准差</div>
            ${row('峰值压力', stats.std_p.toFixed(3) + ' MPa', true)}
            ${row('峰值时间', stats.std_t.toFixed(3) + ' ms',  true)}
            <div style="color:#bdc3c7;${S}margin-top:0.3rem;margin-bottom:0.15rem;">变异系数</div>
            ${row('峰值压力', stats.cv_p.toFixed(2) + '%', true)}
            ${row('峰值时间', stats.cv_t.toFixed(2) + '%', true)}
        </div>
        <div style="margin-top:0.5rem;padding:0.4rem 0.5rem;border-radius:6px;
                    background:${stats.cv_p < 5 ? '#f0f9f4' : stats.cv_p < 10 ? '#fffbeb' : '#fff5f5'};
                    border:1px solid ${stats.cv_p < 5 ? '#27ae60' : stats.cv_p < 10 ? '#f39c12' : '#e74c3c'};
                    font-size:0.76rem;color:#2c3e50;">
            ${stats.cv_p < 5 ? '✓ 重复性良好' : stats.cv_p < 10 ? '⚠ 重复性一般' : '✗ 重复性较差，请检查工况'}
        </div>` : '';

    panel.innerHTML = `
        <div style="font-size:0.78rem;color:#7f8c8d;margin-bottom:0.5rem;">
            实验次数：<strong style="color:#2c3e50;">${stats.count}</strong>
        </div>
        ${runCards}
        ${aggSection}
    `;
}

// ── Delete ────────────────────────────────────────────────────────────────────

async function deleteRun(resultId, workOrder) {
    if (!confirm('确定要删除该实验记录吗？此操作不可撤销。')) return;

    try {
        const resp = await fetch(`/work_order/test_result/${resultId}`, {
            method: 'DELETE',
            headers: { 'X-CSRFToken': getCsrfToken() }
        });
        const data = await resp.json();
        if (data.success) {
            // Refresh the detail panel
            selectWorkOrder(workOrder);
        } else {
            alert('删除失败：' + (data.message || '未知错误'));
        }
    } catch (e) {
        console.error('deleteRun error:', e);
        alert('网络错误，请重试');
    }
}

async function deleteWorkOrder(workOrder) {
    if (!confirm(`确定要删除工单「${workOrder}」及其所有实验记录吗？此操作不可撤销。`)) return;

    try {
        const resp = await fetch(`/work_order/${encodeURIComponent(workOrder)}`, {
            method: 'DELETE',
            headers: { 'X-CSRFToken': getCsrfToken() }
        });
        const data = await resp.json();
        if (data.success) {
            // If the deleted work order was selected, clear the panels
            if (selectedWorkOrder === workOrder) {
                selectedWorkOrder = null;
                document.getElementById('chartPanelTitle').textContent = 'PT 曲线';
                document.getElementById('chartSubtitle').style.display = 'none';
                Plotly.react('woChartDiv', [], {
                    plot_bgcolor: 'white', paper_bgcolor: 'white',
                    margin: { l: 60, r: 30, t: 30, b: 50 },
                    xaxis: { title: 'Time (ms)', gridcolor: '#e0e0e0', showgrid: true },
                    yaxis: { title: 'Pressure (MPa)', gridcolor: '#e0e0e0', showgrid: true }
                });
                document.getElementById('statsPanel').innerHTML =
                    '<div style="color:#7f8c8d;text-align:center;padding:3rem;font-size:0.9rem;">' +
                    '<i class="fas fa-chart-bar" style="font-size:2rem;display:block;margin-bottom:0.75rem;opacity:0.4;"></i>' +
                    '请在左侧选择一个工单</div>';
            }
            await loadWorkOrders();
        } else {
            alert('删除失败：' + (data.message || '未知错误'));
        }
    } catch (e) {
        console.error('deleteWorkOrder error:', e);
        alert('网络错误，请重试');
    }
}

// ── Error helpers ─────────────────────────────────────────────────────────────

function _showListError(msg) {
    document.getElementById('workOrderList').innerHTML =
        `<div style="color:#e74c3c;text-align:center;padding:2rem;font-size:0.88rem;">
            <i class="fas fa-exclamation-circle"></i> ${msg}
        </div>`;
}

function _showDetailError(msg) {
    const subtitle = document.getElementById('chartSubtitle');
    subtitle.style.display = '';
    subtitle.textContent = '加载失败';
    document.getElementById('statsPanel').innerHTML =
        `<div style="color:#e74c3c;text-align:center;padding:3rem;font-size:0.88rem;">
            <i class="fas fa-exclamation-circle"></i> ${msg}
        </div>`;
    Plotly.react('woChartDiv', [], {
        plot_bgcolor: 'white',
        paper_bgcolor: 'white',
        margin: { l: 60, r: 30, t: 30, b: 50 },
        xaxis: { title: 'Time (ms)', gridcolor: '#e0e0e0', showgrid: true },
        yaxis: { title: 'Pressure (MPa)', gridcolor: '#e0e0e0', showgrid: true }
    });
}
