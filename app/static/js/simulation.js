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

// Run simulation
async function runSimulation() {
    const form = document.getElementById('simulationForm');
    const formData = new FormData(form);

    try {
        const response = await fetch('/simulation/run', {
            method: 'POST',
            body: formData
        });

        const result = await response.json();

        if (result.success) {
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

// Upload test result
async function uploadTestResult() {
    const fileInput = document.getElementById('testFileInput');
    const file = fileInput.files[0];

    if (!file) {
        alert('请选择要上传的文件');
        return;
    }

    const formData = new FormData();
    formData.append('file', file);

    try {
        const response = await fetch('/simulation/upload', {
            method: 'POST',
            body: formData
        });

        const result = await response.json();

        if (result.success) {
            // Store test data arrays
            testData = result.data;

            // Refresh comparison chart
            plotComparisonChart();

            alert('测试数据上传成功！');
        } else {
            alert('上传失败：' + result.message);
        }
    } catch (error) {
        console.error('Error:', error);
        alert('上传过程中发生错误');
    }
}

// Plot comparison chart by requesting from backend
async function plotComparisonChart() {
    const comparisonChartDiv = document.getElementById('comparisonChart');

    try {
        // Request backend to generate comparison chart
        const response = await fetch('/simulation/generate_comparison_chart', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
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

// Add model options
function addModelOption() {
    alert('加载模型功能待实现');
}

// File input trigger
function triggerFileInput() {
    document.getElementById('testFileInput').click();
}

// Refresh comparison chart (called by button)
function refreshComparison() {
    plotComparisonChart();
}

// Handle custom option in dropdowns
function handleCustomOption(selectElement) {
    const customInput = selectElement.nextElementSibling;

    if (selectElement.value === '__custom__') {
        // Show custom input field
        customInput.style.display = 'block';
        customInput.focus();

        // Listen for input changes to update the form value
        customInput.oninput = function() {
            // Store custom value in a data attribute
            selectElement.dataset.customValue = this.value;
        };

        // When leaving the input, add the custom value as an option
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
                selectElement.value = this.value;
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
}

// Display selected file name
document.addEventListener('DOMContentLoaded', function() {
    const fileInput = document.getElementById('testFileInput');
    if (fileInput) {
        fileInput.addEventListener('change', function(e) {
            const fileName = e.target.files[0]?.name;
            if (fileName) {
                const label = document.querySelector('.upload-label');
                if (label) {
                    label.innerHTML = `<i class="fas fa-file-excel"></i> ${fileName}`;
                }
            }
        });
    }
});

// Initialize on page load
window.addEventListener('load', function() {
    // Initialize empty charts
    initializeCharts();

    // Set default active tab
    const firstTab = document.querySelector('.tab-btn');
    if (firstTab) {
        firstTab.click();
    }
});
