#!/usr/bin/env python3
"""
Script to plot LCirculant routing algorithm comparison results.
Reads result files from results/ directory and plots selected parameter vs PIR.
"""

import os
import re
import sys
import argparse
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import numpy as np
from pathlib import Path

# Available parameters to plot (English labels only)
PARAMETERS = {
    'packets': ('Total received packets', 'Total received packets'),
    'flits': ('Total received flits', 'Total received flits'),
    'avg_delay': ('Global average delay (cycles)', 'Global average delay (cycles)'),
    'max_delay': ('Max delay (cycles)', 'Max delay (cycles)'),
    'throughput': ('Network throughput (flits/cycle)', 'Network throughput (flits/cycle)'),
    'ip_throughput': ('Average IP throughput (flits/cycle/IP)', 'Average IP throughput (flits/cycle/IP)'),
    'total_energy': ('Total energy (J)', 'Total energy (J)'),
    'dynamic_energy': ('Dynamic energy (J)', 'Dynamic energy (J)'),
    'static_energy': ('Static energy (J)', 'Static energy (J)')
}

# Algorithm file suffixes and display names
ALGORITHM_SUFFIXES = {
    'new_alg': ('LCIRC', 'route-zero3 algorithm'),
    'dijkstra': ('LCIRC_DIJKSTRA', "Dijkstra's algorithm"),
    'virtualcoord': ('LCIRC_VIRTUALCOORD', 'Virtual coordinates'),
    'simple': ('LCIRC_SIMPLE', 'Clockwise traversal')
}

# Traffic pattern display names (convert TRAFFIC_XXX to readable English)
TRAFFIC_NAMES = {
    'TRAFFIC_RANDOM': 'random uniform',
    'TRAFFIC_BIT_REVERSAL': 'bit-reverse',
    'TRAFFIC_SHUFFLE': 'shuffle',
    'TRAFFIC_BUTTERFLY': 'butterfly'
}


def parse_result_file(filepath, algorithm_key):
    """Parse a result file and extract PIR, traffic pattern, and parameter values for one algorithm."""
    with open(filepath, 'r') as f:
        content = f.read()
    
    # Extract PIR from header
    pir_match = re.search(r'PIR:\s*([\d.]+)', content)
    if not pir_match:
        return None
    
    pir = float(pir_match.group(1))
    
    # Extract traffic pattern from header if present
    traffic_match = re.search(r'Traffic Pattern:\s*(\S+)', content)
    traffic_pattern = traffic_match.group(1) if traffic_match else None
    
    # Extract algorithm name from header
    alg_match = re.search(r'LCirculant Routing Algorithm:\s*(\S+)', content)
    alg_name = alg_match.group(1) if alg_match else algorithm_key
    
    # Find algorithm section (now there's only one algorithm per file)
    alg_section_match = re.search(
        rf'--- {alg_name} Algorithm ---(.*?)(?=Results saved to:|$)',
        content,
        re.DOTALL
    )
    
    if not alg_section_match:
        return None
    
    alg_section = alg_section_match.group(1)
    alg_results = {}
    
    # Parse each parameter
    for param_key, (param_label_en, param_label_ru) in PARAMETERS.items():
        # Match parameter line: "Parameter name: value"
        pattern = rf'{re.escape(param_label_en)}:\s*([\d.eE+-]+)'
        match = re.search(pattern, alg_section)
        if match:
            value_str = match.group(1).strip()
            # Handle numbers with leading zeros like "00.000016" or "00.080187"
            try:
                alg_results[param_key] = float(value_str)
            except ValueError:
                # If conversion fails, try to clean up the string
                if '.' in value_str:
                    parts = value_str.split('.', 1)
                    integer_part = parts[0].lstrip('0') or '0'
                    value_str = f"{integer_part}.{parts[1]}"
                else:
                    value_str = value_str.lstrip('0') or '0'
                try:
                    alg_results[param_key] = float(value_str)
                except ValueError:
                    alg_results[param_key] = 0.0
        else:
            alg_results[param_key] = 0.0
    
    results = {
        'PIR': pir,
        'algorithm': algorithm_key,
        'values': alg_results
    }
    if traffic_pattern:
        results['traffic_pattern'] = traffic_pattern
    
    return results


def load_all_results(results_dir, traffic_pattern=None):
    """Load all result files from the results directory or specific traffic pattern subdirectory."""
    results_dir = Path(results_dir)
    
    # If traffic_pattern is specified, look in that subdirectory
    if traffic_pattern:
        search_dir = results_dir / traffic_pattern
        if not search_dir.exists():
            print(f"Warning: Traffic pattern directory not found: {search_dir}")
            return {}
    else:
        search_dir = results_dir
    
    # Find all result files with algorithm suffixes
    # Pattern: lcirc_results_PIR_0_01_simple.txt, lcirc_results_PIR_0_01_new_alg.txt, etc.
    pattern = re.compile(r'lcirc_results_PIR_(\d+)_(\d+)_(\w+)\.txt')
    
    # Organize results by algorithm and PIR
    results_by_algorithm = {suffix: {} for suffix in ALGORITHM_SUFFIXES.keys()}
    
    for filepath in sorted(search_dir.glob('lcirc_results_PIR_*_*.txt')):
        match = pattern.match(filepath.name)
        if match:
            suffix = match.group(3)
            if suffix in ALGORITHM_SUFFIXES:
                parsed = parse_result_file(filepath, suffix)
                if parsed:
                    pir = parsed['PIR']
                    results_by_algorithm[suffix][pir] = parsed
    
    return results_by_algorithm


def smooth_data(values, window_size=3):
    """Apply moving average smoothing to data using numpy."""
    if len(values) < window_size:
        return values
    
    # Convert to numpy array for efficient processing
    arr = np.array(values, dtype=float)
    
    # Use convolution for moving average
    kernel = np.ones(window_size) / window_size
    
    # Pad array to handle boundaries
    padded = np.pad(arr, (window_size // 2, window_size // 2), mode='edge')
    
    # Apply convolution
    smoothed = np.convolve(padded, kernel, mode='valid')
    
    return smoothed.tolist()


def plot_parameter(results_by_algorithm, parameter, traffic_pattern=None, output_file=None, show_plot=True, smooth=True):
    """Plot a specific parameter for all algorithms."""
    if parameter not in PARAMETERS:
        print(f"Error: Unknown parameter '{parameter}'")
        print(f"Available parameters: {', '.join(PARAMETERS.keys())}")
        return
    
    param_label_en, param_label_ru = PARAMETERS[parameter]
    
    # Collect all PIR values from all algorithms
    all_pirs = set()
    for alg_data in results_by_algorithm.values():
        all_pirs.update(alg_data.keys())
    pirs = sorted(all_pirs)
    
    if not pirs:
        print("Error: No data found for plotting")
        return
    
    # Multiply PIR values by 63 (number of nodes) to get packets/cycle
    pirs_packets_per_cycle = [pir * 63.0 for pir in pirs]
    
    # Extract data for each algorithm
    data = {}
    for suffix, alg_data in results_by_algorithm.items():
        alg_values = []
        for pir in pirs:
            if pir in alg_data:
                value = alg_data[pir]['values'].get(parameter, 0.0)
                # For throughput, convert from flits/cycle to packets/cycle (divide by 8)
                if parameter == 'throughput':
                    value = value / 8.0
                alg_values.append(value)
            else:
                alg_values.append(0.0)
        if any(alg_values):  # Only include if there's data
            # Apply smoothing if requested
            if smooth and len(alg_values) > 2:
                data[suffix] = smooth_data(alg_values, window_size=3)
            else:
                data[suffix] = alg_values
    
    if not data:
        print("Error: No data found for any algorithm")
        return
    
    # Create plot
    plt.figure(figsize=(10, 6))
    
    # Plot lines for each algorithm
    colors = {'new_alg': 'blue', 'dijkstra': 'green', 'simple': 'red', 'virtualcoord': 'orange'}
    markers = {'new_alg': 'o', 'dijkstra': 's', 'simple': '^', 'virtualcoord': 'D'}
    linestyles = {'new_alg': '-', 'dijkstra': '--', 'simple': '-.', 'virtualcoord': ':'}
    
    for suffix, values in data.items():
        alg_name = ALGORITHM_SUFFIXES[suffix][1]  # Display name
        plt.plot(
            pirs_packets_per_cycle,
            values,
            label=alg_name,
            color=colors[suffix],
            marker=markers[suffix],
            linestyle=linestyles[suffix],
            linewidth=2,
            markersize=6
        )
    
    plt.xlabel('PIR (packet injection rate per node)', fontsize=12)
    plt.ylabel(param_label_ru, fontsize=12)
    
    # Set X-axis ticks to match actual data points with 1 decimal place formatting
    ax = plt.gca()
    ax.set_xticks(pirs_packets_per_cycle)
    ax.xaxis.set_major_formatter(ticker.FuncFormatter(lambda x, p: f'{x:.1f}'))
    
    # Create title with traffic pattern name
    if traffic_pattern:
        traffic_name = TRAFFIC_NAMES.get(traffic_pattern, traffic_pattern.lower().replace('traffic_', ''))
        title = f'Traffic: {traffic_name}'
    else:
        title = 'Routing algorithms comparison'
    plt.title(title, fontsize=14)
    plt.grid(True, alpha=0.3)
    plt.legend(fontsize=10)
    plt.tight_layout()
    
    # Save plot if output file specified
    if output_file:
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        print(f"Plot saved to: {output_file}")
    
    # Show plot
    if show_plot:
        plt.show()
    else:
        plt.close()


def get_available_traffic_patterns(results_dir):
    """Get list of available traffic pattern subdirectories."""
    results_dir = Path(results_dir)
    patterns = []
    
    if results_dir.exists():
        for item in results_dir.iterdir():
            if item.is_dir() and item.name.startswith('TRAFFIC_'):
                patterns.append(item.name)
    
    return sorted(patterns)


def main():
    parser = argparse.ArgumentParser(
        description='Plot LCirculant routing algorithm comparison results',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f'''
Available parameters:
  {chr(10).join(f"  {k:15} - {v}" for k, v in PARAMETERS.items())}

Examples:
  python plot_results.py packets --traffic TRAFFIC_BIT_REVERSAL
  python plot_results.py avg_delay --traffic TRAFFIC_SHUFFLE --output delay_plot.png
  python plot_results.py total_energy --traffic TRAFFIC_BUTTERFLY --no-show
  python plot_results.py throughput  # Will list available traffic patterns if not specified
        '''
    )
    
    parser.add_argument(
        'parameter',
        choices=list(PARAMETERS.keys()),
        help='Parameter to plot'
    )
    
    parser.add_argument(
        '--results-dir',
        default='results',
        help='Directory containing result files (default: results)'
    )
    
    parser.add_argument(
        '--traffic', '-t',
        help='Traffic pattern to plot (e.g., TRAFFIC_BIT_REVERSAL). If not specified, will list available patterns.'
    )
    
    parser.add_argument(
        '--output', '-o',
        help='Output file for the plot (e.g., plot.png)'
    )
    
    parser.add_argument(
        '--no-show',
        action='store_true',
        help='Do not display the plot (useful when saving to file)'
    )
    
    parser.add_argument(
        '--no-smooth',
        action='store_true',
        help='Disable data smoothing (show raw data)'
    )
    
    args = parser.parse_args()
    
    # Get available traffic patterns
    available_patterns = get_available_traffic_patterns(args.results_dir)
    
    if not available_patterns:
        print(f"Error: No traffic pattern directories found in {args.results_dir}")
        print("Make sure you have run the simulation script first.")
        sys.exit(1)
    
    # If traffic pattern not specified, list available and exit
    if not args.traffic:
        print(f"Available traffic patterns in {args.results_dir}:")
        for pattern in available_patterns:
            print(f"  - {pattern}")
        print(f"\nUsage: python plot_results.py {args.parameter} --traffic <PATTERN>")
        print(f"Example: python plot_results.py {args.parameter} --traffic {available_patterns[0]}")
        sys.exit(0)
    
    # Check if specified traffic pattern exists
    if args.traffic not in available_patterns:
        print(f"Error: Traffic pattern '{args.traffic}' not found.")
        print(f"Available patterns: {', '.join(available_patterns)}")
        sys.exit(1)
    
    # Load results
    print(f"Loading results from {args.results_dir}/{args.traffic}...")
    results_by_algorithm = load_all_results(args.results_dir, traffic_pattern=args.traffic)
    
    if not results_by_algorithm or not any(results_by_algorithm.values()):
        print(f"Error: No result files found in {args.results_dir}/{args.traffic}")
        sys.exit(1)
    
    # Count loaded files
    total_files = sum(len(alg_data) for alg_data in results_by_algorithm.values())
    print(f"Loaded {total_files} result files")
    
    # Get PIR range
    all_pirs = set()
    for alg_data in results_by_algorithm.values():
        all_pirs.update(alg_data.keys())
    if all_pirs:
        print(f"PIR range: {min(all_pirs):.2f} - {max(all_pirs):.2f}")
    
    # Plot
    plot_parameter(
        results_by_algorithm,
        args.parameter,
        traffic_pattern=args.traffic,
        output_file=args.output,
        show_plot=not args.no_show,
        smooth=not args.no_smooth
    )


if __name__ == '__main__':
    main()
