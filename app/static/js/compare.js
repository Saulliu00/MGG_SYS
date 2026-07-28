// 工单对比 (Work Order Comparison) — frontend logic

let selectedValues = new Set();

function _escapeHtml(str) {
    return String(str)
        .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;').replace(/'/g, '&#039;');
}

// ── Init ─────────────────────────────────────────────────────────────────────

window.addEventListener('load', function () {
    Plotly.newPlot('compareChartDiv', [], {
        plot_bgcolor: 'white', paper_bgcolor: 'white',
        margin: { l: 60, r: 30, t: 30, b: 50 },
        xaxis: { title: 'Time (ms)', gridcolor: '#e0e0e0', showgrid: true },
        yaxis: { title: 'Pressure (MPa)', gridcolor: '#e0e0e0', showgrid: true },
        annotations: [{
            text: '请在左侧选择对比项后点击「运行对比」',
            xref: 'paper', yref: 'paper', x: 0.5, y: 0.5,
            showarrow: false, font: { size: 15, color: '#7f8c8d' }
        }]
    }, { responsive: true });

    loadOptions();
});

// ── Options ───────────────────────────────────────────────────────────────────

function onDimChange() {
    selectedValues.clear();
    updateRunButton();
    loadOptions();
}

async function loadOptions() {
    const dim = document.getElementById('dimSelect').value;
    document.getElementById('optionsList').innerHTML =
        '<div style="color:#7f8c8d;text-align:center;padding:2rem;font-size:0.88rem;">' +
        '<i class="fas fa-spinner fa-spin"></i> 加载中...</div>';

    try {
        const resp = await fetch(`/work_order/compare/options?dim=${encodeURIComponent(dim)}`, {
            headers: { 'X-CSRFToken': getCsrfToken() }
        });
        const data = await resp.json();
        if (data.success) {
            renderOptions(data.options);
        } else {
            document.getElementById('optionsList').innerHTML =
                '<div style="color:#e74c3c;text-align:center;padding:2rem;font-size:0.88rem;">' +
                '<i class="fas fa-exclamation-circle"></i> 加载失败</div>';
        }
    } catch (e) {
        console.error('loadOptions error:', e);
        document.getElementById('optionsList').innerHTML =
            '<div style="color:#e74c3c;text-align:center;padding:2rem;font-size:0.88rem;">' +
            '<i class="fas fa-exclamation-circle"></i> 网络错误</div>';
    }
}

function renderOptions(options) {
    const container = document.getElementById('optionsList');
    if (!options.length) {
        container.innerHTML =
            '<div style="color:#7f8c8d;text-align:center;padding:2rem;font-size:0.85rem;">' +
            '<i class="fas fa-inbox" style="font-size:1.6rem;display:block;margin-bottom:0.5rem;opacity:0.35;"></i>' +
            '暂无可对比的数据</div>';
        return;
    }

    container.innerHTML = options.map(opt => {
        const checked = selectedValues.has(opt.value);
        return `
        <label style="display:flex; align-items:center; gap:0.5rem; padding:0.45rem 0.5rem;
                       margin-bottom:0.3rem; border-radius:7px; cursor:pointer;
                       border:1px solid ${checked ? '#667eea' : '#e8ecf0'};
                       background:${checked ? '#eef2ff' : '#fff'};
                       transition:background 0.12s; user-select:none;">
            <input type="checkbox" value="${_escapeHtml(opt.value)}"
                   ${checked ? 'checked' : ''}
                   onchange="toggleValue(this)"
                   style="accent-color:#667eea; flex-shrink:0;">
            <span style="flex:1; min-width:0;">
                <span style="font-size:0.88rem; font-weight:600; color:#2c3e50;
                             white-space:nowrap; overflow:hidden; text-overflow:ellipsis; display:block;">
                    ${_escapeHtml(opt.value)}
                </span>
                <span style="font-size:0.73rem; color:#aab2bd;">${opt.count} 个仿真</span>
            </span>
        </label>`;
    }).join('');
}

function toggleValue(checkbox) {
    if (checkbox.checked) {
        selectedValues.add(checkbox.value);
    } else {
        selectedValues.delete(checkbox.value);
    }
    // Re-render to update border/background without a full reload
    const dim = document.getElementById('dimSelect').value;
    document.querySelectorAll('#optionsList label').forEach(lbl => {
        const cb = lbl.querySelector('input[type=checkbox]');
        const sel = selectedValues.has(cb.value);
        lbl.style.border = `1px solid ${sel ? '#667eea' : '#e8ecf0'}`;
        lbl.style.background = sel ? '#eef2ff' : '#fff';
    });
    updateRunButton();
}

function updateRunButton() {
    const n = selectedValues.size;
    const btn = document.getElementById('runCompareBtn');
    const hint = document.getElementById('selHint');
    const cntEl = document.getElementById('selCount');
    cntEl.textContent = n ? `(已选 ${n})` : '';
    if (n >= 2) {
        btn.disabled = false;
        btn.style.opacity = '1';
        hint.textContent = `已选 ${n} 项，点击运行对比`;
        hint.style.color = '#667eea';
    } else {
        btn.disabled = true;
        btn.style.opacity = '0.5';
        hint.textContent = '请选择至少 2 项';
        hint.style.color = '#aab2bd';
    }
}

// ── Run Comparison ────────────────────────────────────────────────────────────

async function runComparison() {
    if (selectedValues.size < 2) return;

    const btn = document.getElementById('runCompareBtn');
    btn.disabled = true;
    btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> 计算中...';

    const dim = document.getElementById('dimSelect').value;
    const values = Array.from(selectedValues);

    try {
        const resp = await fetch('/work_order/compare/run', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCsrfToken() },
            body: JSON.stringify({ dimension: dim, values })
        });
        const data = await resp.json();

        if (data.success) {
            renderChart(data.chart, dim, values);
            renderStats(data.table);
        } else {
            alert(data.message || '对比失败，请稍后重试');
        }
    } catch (e) {
        console.error('runComparison error:', e);
        alert('网络错误，请重试');
    } finally {
        btn.disabled = false;
        btn.innerHTML = '<i class="fas fa-chart-line"></i> 运行对比';
        btn.style.opacity = selectedValues.size >= 2 ? '1' : '0.5';
    }
}

// ── Chart ─────────────────────────────────────────────────────────────────────

const DIM_LABELS = {
    work_order:     '工单号',
    nc_usage_1:     'NC用量1',
    gp_usage:       'GP用量',
    shell_model:    '管壳高度',
    ignition_model: '点火具型号',
};

function renderChart(chartJson, dim, values) {
    if (!chartJson || !chartJson.data) return;
    Plotly.newPlot('compareChartDiv', chartJson.data, chartJson.layout, { responsive: true });

    const dimLabel = DIM_LABELS[dim] || dim;
    document.getElementById('chartTitle').textContent = `PT 曲线对比 — ${dimLabel}`;
    document.getElementById('chartSubtitle').textContent =
        `对比项：${values.join(' / ')}`;
}

// ── Statistics ────────────────────────────────────────────────────────────────

function renderStats(table) {
    const panel = document.getElementById('statsPanel');
    if (!table || !table.length) {
        panel.innerHTML =
            '<div style="color:#7f8c8d;text-align:center;padding:3rem;font-size:0.9rem;">' +
            '所选项暂无实验数据可对比</div>';
        return;
    }

    // Find best (highest peak pressure) to highlight
    const maxP = Math.max(...table.map(r => r.peak_pressure));

    const rows = table.map(row => {
        const isBest = row.peak_pressure === maxP;
        return `
        <div style="padding:0.55rem 0.6rem; margin-bottom:0.45rem; border-radius:7px;
                    border:1px solid ${isBest ? '#667eea' : '#e8ecf0'};
                    background:${isBest ? '#eef2ff' : '#fff'};">
            <div style="font-size:0.82rem; font-weight:700; color:#2c3e50; margin-bottom:0.3rem;
                        white-space:nowrap; overflow:hidden; text-overflow:ellipsis;"
                 title="${_escapeHtml(row.label)}">
                ${isBest ? '<i class="fas fa-trophy" style="color:#f39c12;font-size:0.78rem;"></i> ' : ''}
                ${_escapeHtml(row.label)}
            </div>
            <div style="display:flex;justify-content:space-between;font-size:0.77rem;">
                <span style="color:#95a5a6;">峰值压力</span>
                <span style="color:#2c3e50;font-weight:600;">${row.peak_pressure.toFixed(3)} MPa</span>
            </div>
            <div style="display:flex;justify-content:space-between;font-size:0.77rem;margin-top:0.1rem;">
                <span style="color:#95a5a6;">峰值时间</span>
                <span style="color:#2c3e50;font-weight:600;">${row.peak_time.toFixed(3)} ms</span>
            </div>
            <div style="display:flex;justify-content:space-between;font-size:0.73rem;margin-top:0.1rem;">
                <span style="color:#bdc3c7;">实验次数</span>
                <span style="color:#7f8c8d;">${row.count} 次</span>
            </div>
        </div>`;
    }).join('');

    panel.innerHTML = `
        <div style="font-size:0.78rem;color:#7f8c8d;margin-bottom:0.6rem;">
            共 <strong style="color:#2c3e50;">${table.length}</strong> 项参与对比
        </div>
        ${rows}`;
}
