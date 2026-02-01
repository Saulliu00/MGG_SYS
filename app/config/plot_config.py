"""Plot configuration for Plotly charts in MGG_SYS"""

# Color scheme
COLORS = {
    'simulation': 'rgb(66, 126, 234)',  # Blue
    'test': 'rgb(231, 76, 60)',          # Red
    'grid': '#e0e0e0',
    'background': 'white',
    'text': '#2c3e50',
    'text_secondary': '#7f8c8d'
}

# Line styles
LINE_STYLES = {
    'simulation': {
        'color': COLORS['simulation'],
        'width': 3,
        'dash': None  # Solid line
    },
    'test': {
        'color': COLORS['test'],
        'width': 3,
        'dash': 'dot'  # Dotted line
    }
}

# Default layout configuration
DEFAULT_LAYOUT = {
    'plot_bgcolor': COLORS['background'],
    'paper_bgcolor': COLORS['background'],
    'margin': {
        'l': 60,
        'r': 30,
        't': 30,
        'b': 50
    },
    'hovermode': 'x unified',
    'font': {
        'family': 'Microsoft YaHei, Arial, sans-serif',
        'size': 12,
        'color': COLORS['text']
    }
}

# Axis configuration
AXIS_CONFIG = {
    'xaxis': {
        'title': 'Time (ms)',
        'gridcolor': COLORS['grid'],
        'showgrid': True,
        'zeroline': False,
        'showline': True,
        'linecolor': COLORS['grid']
    },
    'yaxis': {
        'title': 'Pressure (MPa)',
        'gridcolor': COLORS['grid'],
        'showgrid': True,
        'zeroline': False,
        'showline': True,
        'linecolor': COLORS['grid']
    }
}

# Legend configuration
LEGEND_CONFIG = {
    'x': 0.7,
    'y': 0.1,
    'bgcolor': 'rgba(255, 255, 255, 0.8)',
    'bordercolor': COLORS['grid'],
    'borderwidth': 1
}

# Chart dimensions
CHART_DIMENSIONS = {
    'min_height': 400,
    'default_height': 400,
    'default_width': None  # Auto-width
}

# Placeholder configuration
PLACEHOLDER_CONFIG = {
    'simulation': {
        'text': '点击"计算"按钮开始仿真',
        'font': {
            'size': 16,
            'color': COLORS['text_secondary']
        }
    },
    'comparison': {
        'text': '请先运行仿真或上传测试数据',
        'font': {
            'size': 16,
            'color': COLORS['text_secondary']
        }
    }
}

# Plot configuration presets
PLOT_PRESETS = {
    'simulation_chart': {
        'name': '仿真数据',
        'mode': 'lines',
        'line': LINE_STYLES['simulation']
    },
    'test_chart': {
        'name': '实际数据',
        'mode': 'lines',
        'line': LINE_STYLES['test']
    }
}
