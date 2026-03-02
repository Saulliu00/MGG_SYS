// Work Order Query (工单查询) — frontend logic

let allWorkOrders = [];      // full list from server
let selectedWorkOrder = null; // currently selected work_order string

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
    initEmptyChart();
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
            renderWorkOrderList(allWorkOrders);
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
    renderWorkOrderList(filtered);
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

    container.innerHTML = list.map(wo => `
        <div class="wo-item ${wo.work_order === selectedWorkOrder ? 'wo-item-active' : ''}"
             onclick="selectWorkOrder(${JSON.stringify(wo.work_order)})"
             style="padding:0.65rem 0.75rem; margin-bottom:0.4rem; border-radius:8px;
                    cursor:pointer; border:1px solid #e8ecf0;
                    background:${wo.work_order === selectedWorkOrder ? '#eef2ff' : '#fff'};
                    transition:background 0.15s;">
            <div style="font-weight:600; font-size:0.88rem; color:#2c3e50;
                        white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">
                <i class="fas fa-file-alt" style="color:#667eea; margin-right:0.4rem;"></i>
                ${_escapeHtml(wo.work_order)}
            </div>
            <div style="font-size:0.78rem; color:#7f8c8d; margin-top:0.2rem;
                        white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">
                ${_escapeHtml(wo.recipe_summary || '—')}
            </div>
            <div style="font-size:0.75rem; color:#aab2bd; margin-top:0.15rem;">
                ${_escapeHtml(wo.created_at)}
            </div>
        </div>
    `).join('');
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
    document.getElementById('chartSubtitle').textContent = '加载中...';
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

function initEmptyChart() {
    const layout = {
        xaxis: { title: 'Time (ms)', gridcolor: '#e0e0e0', showgrid: true },
        yaxis: { title: 'Pressure (MPa)', gridcolor: '#e0e0e0', showgrid: true },
        plot_bgcolor: 'white',
        paper_bgcolor: 'white',
        margin: { l: 60, r: 30, t: 30, b: 50 },
        annotations: [{
            text: '请在左侧选择工单',
            xref: 'paper', yref: 'paper',
            x: 0.5, y: 0.5,
            showarrow: false,
            font: { size: 16, color: '#7f8c8d' }
        }]
    };
    Plotly.newPlot('woChartDiv', [], layout, { responsive: true });
}

function renderChart(chartJson) {
    Plotly.newPlot('woChartDiv', chartJson.data, chartJson.layout, { responsive: true });
}

// ── Statistics ────────────────────────────────────────────────────────────────

function renderStats(stats, testResults) {
    const panel = document.getElementById('statsPanel');

    if (!stats || stats.count === 0) {
        panel.innerHTML =
            '<div style="color:#7f8c8d;text-align:center;padding:3rem;font-size:0.9rem;">' +
            '<i class="fas fa-database" style="font-size:1.8rem;display:block;margin-bottom:0.5rem;opacity:0.4;"></i>' +
            '该工单暂无实验数据</div>';
        return;
    }

    // Build per-run rows
    const runRows = testResults.map(tr => {
        const peak = stats.peaks.find(p => p.filename === tr.filename);
        const peakP = peak ? peak.peak_pressure.toFixed(3) : '—';
        const peakT = peak ? peak.peak_time.toFixed(3) : '—';
        const isOwner = tr.user_id === CURRENT_USER_ID;
        const deleteBtn = isOwner
            ? `<button onclick="deleteRun(${tr.id}, ${JSON.stringify(selectedWorkOrder)})"
                       title="删除此记录"
                       style="background:none;border:none;color:#e74c3c;cursor:pointer;
                              padding:0.1rem 0.3rem;border-radius:4px;font-size:0.85rem;"
                       onmouseover="this.style.background='#fdecea'"
                       onmouseout="this.style.background='none'">
                   <i class="fas fa-times"></i>
               </button>`
            : '';

        return `
            <tr style="font-size:0.83rem;">
                <td style="padding:0.4rem 0.5rem; max-width:120px;
                            white-space:nowrap; overflow:hidden; text-overflow:ellipsis;"
                    title="${_escapeHtml(tr.filename)}">${_escapeHtml(tr.filename)}</td>
                <td style="padding:0.4rem 0.5rem; text-align:right;">${peakP}</td>
                <td style="padding:0.4rem 0.5rem; text-align:right;">${peakT}</td>
                <td style="padding:0.4rem 0.3rem; text-align:center;">${deleteBtn}</td>
            </tr>`;
    }).join('');

    // Aggregate row (only meaningful when > 1 run)
    const aggSection = stats.count > 1 ? `
        <tr style="border-top:2px solid #dce1e7; font-size:0.83rem; background:#f8f9fa;">
            <td style="padding:0.4rem 0.5rem; font-weight:600; color:#2c3e50;">均值</td>
            <td style="padding:0.4rem 0.5rem; text-align:right; font-weight:600;">${stats.mean_p.toFixed(3)}</td>
            <td style="padding:0.4rem 0.5rem; text-align:right; font-weight:600;">${stats.mean_t.toFixed(3)}</td>
            <td></td>
        </tr>
        <tr style="font-size:0.83rem; background:#f8f9fa;">
            <td style="padding:0.4rem 0.5rem; color:#7f8c8d;">标准差</td>
            <td style="padding:0.4rem 0.5rem; text-align:right; color:#7f8c8d;">${stats.std_p.toFixed(3)}</td>
            <td style="padding:0.4rem 0.5rem; text-align:right; color:#7f8c8d;">${stats.std_t.toFixed(3)}</td>
            <td></td>
        </tr>
        <tr style="font-size:0.83rem; background:#f8f9fa;">
            <td style="padding:0.4rem 0.5rem; color:#7f8c8d;">变异系数</td>
            <td style="padding:0.4rem 0.5rem; text-align:right; color:#7f8c8d;">${stats.cv_p.toFixed(2)}%</td>
            <td style="padding:0.4rem 0.5rem; text-align:right; color:#7f8c8d;">${stats.cv_t.toFixed(2)}%</td>
            <td></td>
        </tr>` : '';

    panel.innerHTML = `
        <div style="margin-bottom:1rem;">
            <div style="font-size:0.82rem; color:#7f8c8d; margin-bottom:0.5rem;">
                实验次数：<strong style="color:#2c3e50;">${stats.count}</strong>
            </div>
        </div>

        <div style="overflow-x:auto;">
            <table style="width:100%; border-collapse:collapse;">
                <thead>
                    <tr style="background:#f0f3ff; font-size:0.8rem; color:#4a5568;">
                        <th style="padding:0.45rem 0.5rem; text-align:left; font-weight:600;">文件名</th>
                        <th style="padding:0.45rem 0.5rem; text-align:right; font-weight:600;">峰值压力<br><span style="font-weight:400;">(MPa)</span></th>
                        <th style="padding:0.45rem 0.5rem; text-align:right; font-weight:600;">峰值时间<br><span style="font-weight:400;">(ms)</span></th>
                        <th style="padding:0.45rem 0.3rem; text-align:center; font-weight:600;"></th>
                    </tr>
                </thead>
                <tbody>
                    ${runRows}
                    ${aggSection}
                </tbody>
            </table>
        </div>

        ${stats.count > 1 ? `
        <div style="margin-top:1.25rem; padding:0.75rem; background:#f0f9f4;
                    border:1px solid #27ae60; border-radius:8px; font-size:0.82rem; color:#2c3e50;">
            <i class="fas fa-info-circle" style="color:#27ae60; margin-right:0.4rem;"></i>
            峰值压力变异系数 <strong>${stats.cv_p.toFixed(2)}%</strong>，
            峰值时间变异系数 <strong>${stats.cv_t.toFixed(2)}%</strong>
            ${stats.cv_p < 5 ? '— 实验重复性良好 ✓' : stats.cv_p < 10 ? '— 实验重复性一般' : '— 实验重复性较差，请检查工况'}
        </div>` : ''}
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

// ── Error helpers ─────────────────────────────────────────────────────────────

function _showListError(msg) {
    document.getElementById('workOrderList').innerHTML =
        `<div style="color:#e74c3c;text-align:center;padding:2rem;font-size:0.88rem;">
            <i class="fas fa-exclamation-circle"></i> ${msg}
        </div>`;
}

function _showDetailError(msg) {
    document.getElementById('chartSubtitle').textContent = '加载失败';
    document.getElementById('statsPanel').innerHTML =
        `<div style="color:#e74c3c;text-align:center;padding:3rem;font-size:0.88rem;">
            <i class="fas fa-exclamation-circle"></i> ${msg}
        </div>`;
    initEmptyChart();
}
