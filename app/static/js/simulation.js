// Tab switching
function switchTab(tabName) {
    // Hide all tabs
    document.querySelectorAll('.tab-content').forEach(tab => {
        tab.classList.remove('active');
    });

    // Remove active class from all buttons
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.classList.remove('active');
    });

    // Show selected tab
    document.getElementById(tabName).classList.add('active');
    event.target.classList.add('active');

    // When switching to comparison tab, auto-search for recipe test data
    if (tabName === 'comparison') {
        loadRecipeTestData();
    }

    // Resize Plotly charts after tab switch (needed because charts were hidden)
    setTimeout(function() {
        if (tabName === 'simulation') {
            const chartDiv = document.getElementById('chartDiv');
            if (chartDiv && chartDiv.data) {
                Plotly.Plots.resize(chartDiv);
            }
        } else if (tabName === 'comparison') {
            const comparisonChart = document.getElementById('comparisonChart');
            if (comparisonChart && comparisonChart.data) {
                Plotly.Plots.resize(comparisonChart);
            }
        }
    }, 50);
}

// Simulation data storage
let simulationData = null;       // {time: [...], pressure: [...]}
let simulationPlotData = null;   // Complete Plotly figure from backend
let testData = null;             // {time: [...], pressure: [...]}
let simulationId = null;         // ID of the last simulation run

// Run simulation
async function runSimulation() {
    const form = document.getElementById('simulationForm');
    const formData = new FormData(form);

    try {
        const response = await fetch('/simulation/run', {
            method: 'POST',
            headers: {'X-CSRFToken': getCsrfToken()},
            body: formData
        });

        const result = await response.json();

        if (result.success) {
            // Store simulation ID for linking uploaded test files
            simulationId = result.simulation_id;

            // Store complete Plotly figure from backend
            simulationPlotData = result.data.plot_data;

            // Extract arrays for comparison features
            if (simulationPlotData && simulationPlotData.data && simulationPlotData.data.length > 0) {
                const time = simulationPlotData.data[0].x;
                const pressure = simulationPlotData.data[0].y;
                simulationData = { time, pressure };
            }

            // Update statistics display
            updateSimulationInfo(result.data.statistics);

            // Render the simulation chart
            plotSimulationChart();

            alert('仿真计算完成！');
        } else {
            alert('仿真失败：' + result.message);
        }
    } catch (error) {
        console.error('Error:', error);
        alert('仿真过程中发生错误');
    }
}

// Update simulation info display
function updateSimulationInfo(statistics) {
    const chartInfo = document.querySelector('#simulation .chart-info');
    if (chartInfo && statistics) {
        const r2 = statistics.r_squared ? statistics.r_squared.toFixed(4) : '1.0000';
        const peak = statistics.peak_pressure ? statistics.peak_pressure.toFixed(1) : 'N/A';
        const numModels = statistics.num_models || 'N/A';

        chartInfo.innerHTML = `
            多项式拟合 (模型数: ${numModels}, R²=${r2})<br>
            峰值压力: ${peak} MPa
        `;
    }
}

// Plot simulation chart (for simulation tab)
function plotSimulationChart() {
    if (!simulationPlotData) {
        console.warn('No simulation data to plot');
        return;
    }

    const chartDiv = document.getElementById('chartDiv');

    // Use the complete Plotly figure from backend
    // The backend generates the figure using our plotter utility
    Plotly.newPlot(chartDiv, simulationPlotData.data, simulationPlotData.layout, {responsive: true});
}

// Pending file waiting for user confirmation
let pendingFile = null;

// --- PARAM VALIDATION (client-side) ---
function checkTestParams() {
    const form = document.getElementById('simulationForm');
    const formData = new FormData(form);
    const errors = [];

    const selectLabels = {
        ignition_model: '点火具型号', nc_type_1: 'NC类型1', nc_type_2: 'NC类型2',
        gp_type: 'GP类型', shell_model: '管壳高度', current: '电流',
        sensor_model: '传感器量程', body_model: '容积'
    };
    for (const [field, label] of Object.entries(selectLabels)) {
        const val = formData.get(field);
        if (!val || val === '__custom__') {
            errors.push(`${label} 未填写完整`);
        }
    }

    const nc1 = parseFloat(formData.get('nc_usage_1') || '0');
    if (nc1 <= 0) errors.push('NC用量1 必须大于 0');

    return errors;
}

// --- STEP 1: file selected → validate, then show preview + buttons ---
async function validateAndPreviewUpload(file) {
    const label = document.getElementById('uploadLabel');
    label.innerHTML = '<i class="fas fa-spinner fa-spin fa-2x"></i>'
        + '<p>正在检查文件...</p>';

    // Client-side param check
    const paramErrors = checkTestParams();
    if (paramErrors.length > 0) {
        _resetUploadLabel();
        _showUploadErrors(['测试参数检查未通过：', ...paramErrors]);
        return;
    }

    // Server-side file format check
    const formData = new FormData();
    formData.append('file', file);

    try {
        const response = await fetch('/simulation/validate_upload', {
            method: 'POST',
            headers: {'X-CSRFToken': getCsrfToken()},
            body: formData
        });
        const result = await response.json();

        if (result.valid) {
            pendingFile = file;
            _showUploadPreview(file.name, result.stats);
        } else {
            _resetUploadLabel();
            _showUploadErrors(result.errors || ['文件格式校验失败']);
        }
    } catch (error) {
        console.error('Error during validation:', error);
        _resetUploadLabel();
        _showUploadErrors(['文件检查过程中发生错误，请重试']);
    }
}

function _showUploadPreview(filename, stats) {
    const label = document.getElementById('uploadLabel');
    label.innerHTML = '<i class="fas fa-file-excel fa-2x" style="color:#27ae60"></i>'
        + `<p style="color:#27ae60;font-weight:bold;">${filename}</p>`
        + '<p style="font-size:0.85rem;color:#7f8c8d;">确认参数后点击「确认上传」</p>';

    const previewInfo = document.getElementById('uploadPreviewInfo');
    previewInfo.innerHTML =
        `<strong><i class="fas fa-check-circle" style="color:#27ae60"></i> 文件校验通过</strong><br>`
        + `数据行数：<strong>${stats.rows}</strong> 行&emsp;`
        + `时间范围：<strong>${stats.time_range[0]} ~ ${stats.time_range[1]} ms</strong>&emsp;`
        + `压力范围：<strong>${stats.pressure_range[0]} ~ ${stats.pressure_range[1]} MPa</strong>`;

    document.getElementById('uploadValidationErrors').style.display = 'none';
    document.getElementById('uploadPreviewArea').style.display = 'block';
    document.getElementById('confirmUploadBtn').disabled = false;
}

function _showUploadErrors(errors) {
    const errDiv = document.getElementById('uploadValidationErrors');
    errDiv.innerHTML = '<strong><i class="fas fa-times-circle"></i> 校验未通过</strong><br>'
        + errors.map(e => `• ${e}`).join('<br>');
    errDiv.style.display = 'block';
    document.getElementById('uploadPreviewInfo').innerHTML = '';
    document.getElementById('uploadPreviewArea').style.display = 'block';
    document.getElementById('confirmUploadBtn').disabled = true;
}

function _resetUploadLabel() {
    const label = document.getElementById('uploadLabel');
    label.innerHTML = '<i class="fas fa-cloud-upload-alt fa-3x"></i>'
        + '<p>点击上传测试数据文件 (.xlsx)</p>'
        + '<p style="font-size:0.9rem;color:#7f8c8d;">文件应包含时间和压力两列数据</p>';
}

// --- STEP 2a: cancel ---
function cancelUpload() {
    pendingFile = null;
    document.getElementById('testFileInput').value = '';
    document.getElementById('uploadPreviewArea').style.display = 'none';
    _resetUploadLabel();
}

// --- STEP 2b: confirm → persist to DB ---
async function confirmUpload() {
    if (!pendingFile) return;

    const btn = document.getElementById('confirmUploadBtn');
    btn.disabled = true;
    btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> 上传中...';

    const formData = new FormData();
    formData.append('file', pendingFile);
    // Add simulation_id if available (from current session)
    if (simulationId) {
        formData.append('simulation_id', simulationId);
    }
    
    // Add work_order if user specified it (for historical data)
    const workOrderInput = document.getElementById('uploadWorkOrderInput');
    if (workOrderInput && workOrderInput.value.trim()) {
        formData.append('work_order', workOrderInput.value.trim());
    }

    try {
        const response = await fetch('/simulation/upload', {
            method: 'POST',
            headers: {'X-CSRFToken': getCsrfToken()},
            body: formData
        });
        const result = await response.json();

        if (result.success) {
            testData = result.data;
            pendingFile = null;
            btn.disabled = false;
            btn.innerHTML = '<i class="fas fa-check"></i> 确认上传';
            document.getElementById('uploadPreviewArea').style.display = 'none';
            const label = document.getElementById('uploadLabel');
            label.innerHTML = '<i class="fas fa-check-circle fa-2x" style="color:#27ae60"></i>'
                + `<p style="color:#27ae60;font-weight:bold;">已存储：${result.filename || ''}</p>`
                + '<p style="font-size:0.85rem;color:#7f8c8d;">点击可重新上传</p>';
            plotComparisonChart();
        } else {
            btn.disabled = false;
            btn.innerHTML = '<i class="fas fa-check"></i> 确认上传';
            alert('上传失败：' + result.message);
        }
    } catch (error) {
        console.error('Error:', error);
        btn.disabled = false;
        btn.innerHTML = '<i class="fas fa-check"></i> 确认上传';
        alert('上传过程中发生错误');
    }
}

// Auto-search for matching recipe test data when switching to PT曲线对比 tab
async function loadRecipeTestData() {
    // Need a simulation to know the recipe
    if (!simulationData) {
        return;
    }

    // Collect current recipe parameters from the form
    const form = document.getElementById('simulationForm');
    const formData = new FormData(form);
    const params = {};
    for (const [key, value] of formData.entries()) {
        params[key] = value;
    }

    try {
        const response = await fetch('/simulation/fetch_recipe_test_data', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCsrfToken()
            },
            body: JSON.stringify(params)
        });

        const result = await response.json();

        if (result.found) {
            // Use averaged recipe data as testData and render comparison chart
            testData = result.data;
            plotComparisonChart();
        } else {
            // No matching test data – prompt user to upload
            showNoTestDataModal();
        }
    } catch (error) {
        console.error('Error fetching recipe test data:', error);
    }
}

// Modal: no matching test data found
function showNoTestDataModal() {
    // Remove any existing modal first
    const existing = document.getElementById('noTestDataModal');
    if (existing) existing.remove();

    const overlay = document.createElement('div');
    overlay.id = 'noTestDataModal';
    overlay.style.cssText = [
        'position:fixed', 'top:0', 'left:0', 'width:100%', 'height:100%',
        'background:rgba(0,0,0,0.55)', 'z-index:9999',
        'display:flex', 'align-items:center', 'justify-content:center'
    ].join(';');

    overlay.innerHTML = `
        <div style="background:white;padding:2rem 2.5rem;border-radius:14px;max-width:420px;
                    width:90%;text-align:center;box-shadow:0 6px 32px rgba(0,0,0,0.25);">
            <i class="fas fa-exclamation-triangle"
               style="font-size:2.8rem;color:#e67e22;margin-bottom:1rem;display:block;"></i>
            <h5 style="color:#2c3e50;font-weight:bold;margin-bottom:0.6rem;">暂无匹配实验数据</h5>
            <p style="color:#7f8c8d;font-size:0.9rem;margin-bottom:1.5rem;line-height:1.6;">
                当前配方尚无匹配的实验数据。<br>
                请先在「实际数据储存」中上传实验文件，再进行 PT 曲线对比。
            </p>
            <div style="display:flex;gap:0.75rem;justify-content:center;">
                <button onclick="document.getElementById('noTestDataModal').remove(); switchTabDirect('actual');"
                        style="background:#667eea;color:white;border:none;padding:0.55rem 1.4rem;
                               border-radius:8px;cursor:pointer;font-size:0.9rem;font-weight:bold;">
                    <i class="fas fa-upload"></i> 前往上传
                </button>
                <button onclick="document.getElementById('noTestDataModal').remove(); initializeChart('comparisonChart', 'comparison');"
                        style="background:#ecf0f1;color:#2c3e50;border:none;padding:0.55rem 1.4rem;
                               border-radius:8px;cursor:pointer;font-size:0.9rem;">
                    关闭
                </button>
            </div>
        </div>
    `;

    document.body.appendChild(overlay);

    // Close when clicking the overlay background
    overlay.addEventListener('click', function(e) {
        if (e.target === overlay) {
            overlay.remove();
            initializeChart('comparisonChart', 'comparison');
        }
    });
}

// Switch tab without triggering recipe search (used from modal)
function switchTabDirect(tabName) {
    document.querySelectorAll('.tab-content').forEach(tab => tab.classList.remove('active'));
    document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));
    document.getElementById(tabName).classList.add('active');
    // Highlight the matching tab button
    document.querySelectorAll('.tab-btn').forEach(btn => {
        if (btn.textContent.includes('实际数据')) btn.classList.add('active');
    });
}

// Plot comparison chart by requesting from backend
async function plotComparisonChart() {
    const comparisonChartDiv = document.getElementById('comparisonChart');

    try {
        // Request backend to generate comparison chart
        const response = await fetch('/simulation/generate_comparison_chart', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCsrfToken()
            },
            body: JSON.stringify({
                simulation_data: simulationData,
                test_data: testData
            })
        });

        const result = await response.json();

        if (result.success) {
            // Render the backend-generated chart
            const chartFigure = result.chart;
            Plotly.newPlot(comparisonChartDiv, chartFigure.data, chartFigure.layout, {responsive: true});
        } else {
            console.error('Error generating comparison chart:', result.error);
            // Show placeholder if error
            initializeChart('comparisonChart', 'comparison');
        }
    } catch (error) {
        console.error('Error:', error);
        // Show placeholder if error
        initializeChart('comparisonChart', 'comparison');
    }
}

// Initialize empty chart with placeholder
function initializeChart(chartId, chartType) {
    const placeholderText = chartType === 'simulation'
        ? '点击"计算"按钮开始仿真'
        : '请先运行仿真或上传测试数据';

    const layout = {
        xaxis: { title: 'Time (ms)', gridcolor: '#e0e0e0', showgrid: true },
        yaxis: { title: 'Pressure (MPa)', gridcolor: '#e0e0e0', showgrid: true },
        plot_bgcolor: 'white',
        paper_bgcolor: 'white',
        margin: { l: 60, r: 30, t: 30, b: 50 },
        annotations: [{
            text: placeholderText,
            xref: 'paper',
            yref: 'paper',
            x: 0.5,
            y: 0.5,
            showarrow: false,
            font: { size: 16, color: '#7f8c8d' }
        }]
    };

    Plotly.newPlot(chartId, [], layout, {responsive: true});
}

// Initialize all charts on page load
function initializeCharts() {
    initializeChart('chartDiv', 'simulation');
    initializeChart('comparisonChart', 'comparison');
}

// File input trigger
function triggerFileInput() {
    document.getElementById('testFileInput').click();
}

// Handle custom option in dropdowns
function handleCustomOption(selectElement) {
    const customInput = selectElement.nextElementSibling;

    if (selectElement.value === '__custom__') {
        // Show custom input field
        customInput.style.display = 'block';
        customInput.focus();

        // When leaving the input, add the custom value as a permanent option and select it
        customInput.onblur = function() {
            if (this.value.trim()) {
                // Check if custom option already exists
                let customOption = selectElement.querySelector('option[data-custom="true"]');
                if (customOption) {
                    customOption.value = this.value;
                    customOption.textContent = this.value;
                } else {
                    // Insert new option before "自定义..."
                    customOption = document.createElement('option');
                    customOption.value = this.value;
                    customOption.textContent = this.value;
                    customOption.dataset.custom = 'true';
                    const customPlaceholder = selectElement.querySelector('option[value="__custom__"]');
                    selectElement.insertBefore(customOption, customPlaceholder);
                }
                // Set the select to the custom value so FormData captures it
                selectElement.value = this.value;
                customInput.style.display = 'none';
            }
        };

        // Allow pressing Enter to confirm
        customInput.onkeydown = function(e) {
            if (e.key === 'Enter') {
                this.blur();
            }
        };
    } else {
        // Hide custom input field
        customInput.style.display = 'none';
        customInput.value = '';
    }
}

// Generate work order number
function generateWorkOrder() {
    const now = new Date();
    const year = now.getFullYear();
    const month = String(now.getMonth() + 1).padStart(2, '0');
    const day = String(now.getDate()).padStart(2, '0');
    const hours = String(now.getHours()).padStart(2, '0');
    const minutes = String(now.getMinutes()).padStart(2, '0');
    const seconds = String(now.getSeconds()).padStart(2, '0');
    const random = String(Math.floor(Math.random() * 10000)).padStart(4, '0');

    const workOrderNumber = `WO${year}${month}${day}${hours}${minutes}${seconds}${random}`;

    document.getElementById('workOrderNumber').textContent = workOrderNumber;
    // Store in hidden field so it's submitted with the form
    const hiddenInput = document.getElementById('workOrderInput');
    if (hiddenInput) {
        hiddenInput.value = workOrderNumber;
    }
}

// Handle file selection and trigger upload
document.addEventListener('DOMContentLoaded', function() {
    const fileInput = document.getElementById('testFileInput');
    if (fileInput) {
        fileInput.addEventListener('change', function(e) {
            const file = e.target.files[0];
            if (file) {
                validateAndPreviewUpload(file);
            }
        });
    }
});

// Initialize on page load
window.addEventListener('load', function() {
    initializeCharts();
});
