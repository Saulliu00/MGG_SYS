#!/usr/bin/env python3
"""Test legend position in simulation chart"""

import os
import sys
import json

os.environ['SECRET_KEY'] = 'test'
sys.path.insert(0, os.path.dirname(__file__))

from app.utils.plotter import Plotter

# Create a sample simulation chart
time_data = [0, 1, 2, 3, 4, 5]
pressure_data = [0, 2, 3.5, 3, 2, 1]

chart = Plotter.create_simulation_chart(time_data, pressure_data)

print("=" * 80)
print("SIMULATION CHART LEGEND CONFIGURATION")
print("=" * 80)

# Check if legend exists in layout
if 'layout' in chart and 'legend' in chart['layout']:
    legend = chart['layout']['legend']
    print("\n✅ Legend configuration found:")
    print(json.dumps(legend, indent=2))
    
    print("\n📍 Legend Position Analysis:")
    print(f"  x: {legend.get('x')} (0=left, 1=right)")
    print(f"  y: {legend.get('y')} (0=bottom, 1=top)")
    print(f"  xanchor: {legend.get('xanchor', 'NOT SET')} (should be 'right')")
    print(f"  yanchor: {legend.get('yanchor', 'NOT SET')} (should be 'bottom')")
    
    # Verify correct position
    if (legend.get('x') == 0.99 and 
        legend.get('y') == 0.01 and 
        legend.get('xanchor') == 'right' and 
        legend.get('yanchor') == 'bottom'):
        print("\n✅ CORRECT: Legend is configured for bottom-right corner")
    else:
        print("\n❌ INCORRECT: Legend is NOT in bottom-right corner")
        print("\nExpected:")
        print("  x=0.99, y=0.01, xanchor='right', yanchor='bottom'")
else:
    print("\n❌ No legend configuration found in chart!")

print("\n" + "=" * 80)
print("COMPARISON CHART LEGEND TEST")
print("=" * 80)

# Test comparison chart
sim_data = {'time': [0, 1, 2], 'pressure': [0, 2, 1]}
test_data = {'time': [0, 1, 2], 'pressure': [0, 2.5, 1.2]}

comparison_chart = Plotter.create_comparison_chart(sim_data, test_data)

if 'layout' in comparison_chart and 'legend' in comparison_chart['layout']:
    legend = comparison_chart['layout']['legend']
    print("\n✅ Comparison chart legend:")
    print(json.dumps(legend, indent=2))
else:
    print("\n❌ No legend in comparison chart")

print("\n" + "=" * 80)
