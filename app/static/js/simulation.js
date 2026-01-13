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
}

// Simulation data storage
let simulationData = null;
let testData = null;

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
            simulationData = result.data;
            plotChart();
            alert('仿真计算完成！');
        } else {
            alert('仿真失败：' + result.message);
        }
    } catch (error) {
        console.error('Error:', error);
        alert('仿真过程中发生错误');
    }
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
            testData = result.data;
            plotChart();
            alert('测试数据上传成功！');
        } else {
            alert('上传失败：' + result.message);
        }
    } catch (error) {
        console.error('Error:', error);
        alert('上传过程中发生错误');
    }
}

// Plot chart using Plotly
function plotChart() {
    const chartDiv = document.getElementById('chartDiv');

    const traces = [];

    // Add simulation data if exists
    if (simulationData) {
        traces.push({
            x: simulationData.time,
            y: simulationData.pressure,
            mode: 'lines',
            name: '仿真数据',
            line: {
                color: 'blue',
                width: 2
            }
        });
    }

    // Add test data if exists
    if (testData) {
        traces.push({
            x: testData.time,
            y: testData.pressure,
            mode: 'lines',
            name: '实际数据',
            line: {
                color: 'red',
                width: 2,
                dash: 'dot'
            }
        });
    }

    const layout = {
        title: '',
        xaxis: {
            title: 'Time (ms)',
            gridcolor: '#e0e0e0'
        },
        yaxis: {
            title: 'Pressure (MPa)',
            gridcolor: '#e0e0e0'
        },
        plot_bgcolor: 'white',
        paper_bgcolor: 'white',
        margin: {
            l: 60,
            r: 30,
            t: 30,
            b: 50
        },
        legend: {
            x: 0.7,
            y: 0.1
        }
    };

    Plotly.newPlot(chartDiv, traces, layout, {responsive: true});
}

// Add model options
function addModelOption() {
    alert('加载模型功能待实现');
}

// File input trigger
function triggerFileInput() {
    document.getElementById('testFileInput').click();
}

// Display selected file name
document.addEventListener('DOMContentLoaded', function() {
    const fileInput = document.getElementById('testFileInput');
    if (fileInput) {
        fileInput.addEventListener('change', function(e) {
            const fileName = e.target.files[0]?.name;
            if (fileName) {
                const label = document.querySelector('.upload-label');
                label.innerHTML = `<i class="fas fa-file-excel"></i> ${fileName}`;
            }
        });
    }
});

// Initialize on page load
window.addEventListener('load', function() {
    // Set default active tab
    const firstTab = document.querySelector('.tab-btn');
    if (firstTab) {
        firstTab.click();
    }
});
