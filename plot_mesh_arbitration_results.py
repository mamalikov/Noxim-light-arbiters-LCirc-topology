#!/usr/bin/env python3
"""
Script to plot Mesh arbitration algorithm comparison results.
Reads result files from results/mesh4x4/<ROUTING>/TRAFFIC_*/ or results/mesh8x8/<ROUTING>/TRAFFIC_*/
and plots selected parameter vs PIR for a chosen traffic pattern, mesh size and routing algorithm.
Each file corresponds to one PIR and contains averaged statistics for all arbitration strategies.
"""

import os
import re
import sys
import argparse
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import numpy as np
from pathlib import Path
from collections import defaultdict

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

# Arbitration strategy names and display names
ARBITRATION_STRATEGIES = {
    'RANDOM': 'Random',
    'HOPCOUNT_MAX': 'Hopcount Max',
    'HOPCOUNT_MIN': 'Hopcount Min',
    'DISTANCE_MIN': 'Distance Min',
    'DISTANCE_MAX': 'Distance Max'
}

# Colors and markers for each strategy
STRATEGY_STYLE = {
    'RANDOM': {'color': 'blue', 'marker': 'o', 'linestyle': '-'},
    'HOPCOUNT_MAX': {'color': 'green', 'marker': 's', 'linestyle': '--'},
    'HOPCOUNT_MIN': {'color': 'red', 'marker': '^', 'linestyle': '-.'},
    'DISTANCE_MIN': {'color': 'orange', 'marker': 'D', 'linestyle': ':'},
    'DISTANCE_MAX': {'color': 'purple', 'marker': 'v', 'linestyle': '-.'}
}


def parse_result_file(filepath):
    """Parse a Mesh result file and extract PIR and parameter values for all strategies."""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # Extract PIR from header
    pir_match = re.search(r'PIR:\s*([\d.]+)', content)
    if not pir_match:
        return None

    pir = float(pir_match.group(1))

    # Extract results for each strategy
    results_by_strategy = {}

    for strategy_name in ARBITRATION_STRATEGIES.keys():
        # Find AVERAGED RESULTS section for this strategy
        # Pattern: "AVERAGED RESULTS for Strategy Display (STRATEGY_NAME) (PIR=..., ...):"
        avg_results_pattern = rf'AVERAGED RESULTS for .*? \({re.escape(strategy_name)}\) \(PIR=.*?\):(.*?)(?=--- .*? ---|AVERAGED RESULTS for|Results saved to:|$)'
        avg_results_match = re.search(avg_results_pattern, content, re.DOTALL)

        if not avg_results_match:
            continue

        avg_section = avg_results_match.group(1)
        strategy_results = {}

        # Parse each parameter
        for param_key, (param_label_en, param_label_ru) in PARAMETERS.items():
            # Match parameter line: "  Parameter name: value"
            # Try both English and Russian labels
            pattern_en = rf'{re.escape(param_label_en)}:\s*([\d.eE+-]+)'
            pattern_ru = rf'{re.escape(param_label_ru)}:\s*([\d.eE+-]+)'

            match = re.search(pattern_en, avg_section) or re.search(pattern_ru, avg_section)
            if match:
                value_str = match.group(1).strip()
                try:
                    strategy_results[param_key] = float(value_str)
                except ValueError:
                    # Handle numbers with leading zeros
                    if '.' in value_str:
                        parts = value_str.split('.', 1)
                        integer_part = parts[0].lstrip('0') or '0'
                        value_str = f"{integer_part}.{parts[1]}"
                    else:
                        value_str = value_str.lstrip('0') or '0'
                    try:
                        strategy_results[param_key] = float(value_str)
                    except ValueError:
                        strategy_results[param_key] = 0.0
            else:
                strategy_results[param_key] = 0.0

        results_by_strategy[strategy_name] = strategy_results

    if not results_by_strategy:
        return None

    return {
        'PIR': pir,
        'strategies': results_by_strategy
    }


def get_available_routing_algorithms(mesh_root):
    """Get list of available routing subdirectories (XY, WEST_FIRST, etc.) in mesh root."""
    root = Path(mesh_root)
    algorithms = []
    if root.exists():
        for item in root.iterdir():
            if item.is_dir() and not item.name.startswith('.'):
                algorithms.append(item.name)
    return sorted(algorithms)


def get_available_traffic_patterns(mesh_root, routing):
    """Get list of available Mesh traffic pattern subdirectories (TRAFFIC_*) under mesh_root/routing."""
    root = Path(mesh_root) / routing
    patterns = []
    if root.exists():
        for item in root.iterdir():
            if item.is_dir() and item.name.startswith('TRAFFIC_'):
                patterns.append(item.name)
    return sorted(patterns)


def load_all_results(mesh_root, routing, traffic_pattern):
    """Load all Mesh arbitration result files for a given routing, traffic pattern and mesh size."""
    results_dir = Path(mesh_root) / routing / traffic_pattern

    # Files follow pattern: mesh_arbitration_PIR_0_01.txt
    pattern = re.compile(r'mesh_arbitration_PIR_(\d+)_(\d+)\.txt')

    # Organize results by strategy and PIR
    results_by_strategy = {strategy: {} for strategy in ARBITRATION_STRATEGIES.keys()}

    if not results_dir.exists():
        return results_by_strategy

    for filepath in sorted(results_dir.glob('mesh_arbitration_PIR_*.txt')):
        match = pattern.match(filepath.name)
        if match:
            pir_int_part = match.group(1)
            pir_frac_part = match.group(2)
            if pir_int_part == '0':
                pir = float(f"0.{pir_frac_part}")
            else:
                pir = float(f"{pir_int_part}.{pir_frac_part}")

            parsed = parse_result_file(filepath)
            if parsed:
                for strategy_name, strategy_results in parsed['strategies'].items():
                    if strategy_name in results_by_strategy:
                        results_by_strategy[strategy_name][pir] = strategy_results

    return results_by_strategy


def load_all_results_averaged_over_traffic(mesh_root, routing):
    """Load and average results across all traffic patterns for a given routing and mesh size."""
    routing_dir = Path(mesh_root) / routing
    
    if not routing_dir.exists():
        return {strategy: {} for strategy in ARBITRATION_STRATEGIES.keys()}
    
    # Get all traffic patterns
    traffic_patterns = get_available_traffic_patterns(mesh_root, routing)
    if not traffic_patterns:
        return {strategy: {} for strategy in ARBITRATION_STRATEGIES.keys()}
    
    # Collect data from all traffic patterns
    # Structure: strategy -> PIR -> [values from different traffics]
    all_data = {strategy: defaultdict(list) for strategy in ARBITRATION_STRATEGIES.keys()}
    
    for traffic_pattern in traffic_patterns:
        traffic_results = load_all_results(mesh_root, routing, traffic_pattern)
        for strategy_name, strategy_data in traffic_results.items():
            for pir, metrics_dict in strategy_data.items():
                # Store metrics_dict for this PIR
                all_data[strategy_name][pir].append(metrics_dict)
    
    # Average across traffic patterns for each (strategy, PIR)
    results_by_strategy = {strategy: {} for strategy in ARBITRATION_STRATEGIES.keys()}
    
    for strategy_name in ARBITRATION_STRATEGIES.keys():
        for pir, metrics_list in all_data[strategy_name].items():
            if not metrics_list:
                continue
            
            # Average metrics across all traffic patterns
            averaged_metrics = {}
            for metric_key in PARAMETERS.keys():
                values = [m.get(metric_key, 0.0) for m in metrics_list if metric_key in m]
                if values:
                    averaged_metrics[metric_key] = np.mean(values)
                else:
                    averaged_metrics[metric_key] = 0.0
            
            results_by_strategy[strategy_name][pir] = averaged_metrics
    
    return results_by_strategy


def load_all_results_averaged_over_routing(mesh_root, traffic_pattern):
    """Load and average results across all routing algorithms for a given traffic pattern and mesh size."""
    mesh_path = Path(mesh_root)
    if not mesh_path.exists():
        return {strategy: {} for strategy in ARBITRATION_STRATEGIES.keys()}

    # Discover all routing algorithms available under this mesh
    routing_algos = get_available_routing_algorithms(mesh_root)
    if not routing_algos:
        return {strategy: {} for strategy in ARBITRATION_STRATEGIES.keys()}

    # Collect data from all routings for the given traffic
    # Structure: strategy -> PIR -> [metrics_dict from different routings]
    all_data = {strategy: defaultdict(list) for strategy in ARBITRATION_STRATEGIES.keys()}

    for routing in routing_algos:
        traffic_dir = mesh_path / routing / traffic_pattern
        if not traffic_dir.exists():
            continue
        traffic_results = load_all_results(mesh_root, routing, traffic_pattern)
        for strategy_name, strategy_data in traffic_results.items():
            for pir, metrics_dict in strategy_data.items():
                all_data[strategy_name][pir].append(metrics_dict)

    # Average across routing algorithms for each (strategy, PIR)
    results_by_strategy = {strategy: {} for strategy in ARBITRATION_STRATEGIES.keys()}

    for strategy_name in ARBITRATION_STRATEGIES.keys():
        for pir, metrics_list in all_data[strategy_name].items():
            if not metrics_list:
                continue

            averaged_metrics = {}
            for metric_key in PARAMETERS.keys():
                values = [m.get(metric_key, 0.0) for m in metrics_list if metric_key in m]
                if values:
                    averaged_metrics[metric_key] = np.mean(values)
                else:
                    averaged_metrics[metric_key] = 0.0

            results_by_strategy[strategy_name][pir] = averaged_metrics

    return results_by_strategy


def load_all_results_global(results_root):
    """
    Load and average results across all routing algorithms and traffic patterns
    for both mesh4x4 and mesh8x8.
    """
    root_path = Path(results_root)
    # Collect data: strategy -> PIR -> [metrics_dict across all meshes, routing & traffic]
    all_data = {strategy: defaultdict(list) for strategy in ARBITRATION_STRATEGIES.keys()}

    for mesh_subdir in ["mesh4x4", "mesh8x8"]:
        mesh_root = root_path / mesh_subdir
        if not mesh_root.exists():
            continue

        routing_algos = get_available_routing_algorithms(str(mesh_root))
        if not routing_algos:
            continue

        for routing in routing_algos:
            traffic_patterns = get_available_traffic_patterns(str(mesh_root), routing)
            for traffic_pattern in traffic_patterns:
                traffic_results = load_all_results(str(mesh_root), routing, traffic_pattern)
                for strategy_name, strategy_data in traffic_results.items():
                    for pir, metrics_dict in strategy_data.items():
                        all_data[strategy_name][pir].append(metrics_dict)

    results_by_strategy = {strategy: {} for strategy in ARBITRATION_STRATEGIES.keys()}

    for strategy_name in ARBITRATION_STRATEGIES.keys():
        for pir, metrics_list in all_data[strategy_name].items():
            if not metrics_list:
                continue

            averaged_metrics = {}
            for metric_key in PARAMETERS.keys():
                values = [m.get(metric_key, 0.0) for m in metrics_list if metric_key in m]
                if values:
                    averaged_metrics[metric_key] = np.mean(values)
                else:
                    averaged_metrics[metric_key] = 0.0

            results_by_strategy[strategy_name][pir] = averaged_metrics

    return results_by_strategy


def smooth_data(values, window_size=3):
    """Apply moving average smoothing to data using numpy."""
    if len(values) < window_size:
        return values

    arr = np.array(values, dtype=float)
    kernel = np.ones(window_size) / window_size
    padded = np.pad(arr, (window_size // 2, window_size // 2), mode='edge')
    smoothed = np.convolve(padded, kernel, mode='valid')
    return smoothed.tolist()


def plot_parameter(results_by_strategy, parameter, traffic_pattern=None,
                   output_file=None, show_plot=True, smooth=True,
                   pir_min=None, pir_max=None, absolute=False):
    """
    Plot Mesh arbitration results.

    - If absolute=False: plot relative difference (RR - Arb)/RR*100%.
    - If absolute=True: plot absolute metric values (including RR).
    """
    if parameter not in PARAMETERS:
        print(f"Error: Unknown parameter '{parameter}'")
        print(f"Available parameters: {', '.join(PARAMETERS.keys())}")
        return

    param_label_en, param_label_ru = PARAMETERS[parameter]

    # Collect all PIR values from all strategies
    all_pirs = set()
    for strategy_data in results_by_strategy.values():
        all_pirs.update(strategy_data.keys())
    pirs = sorted(all_pirs)

    # Apply optional PIR range filtering
    if pir_min is not None or pir_max is not None:
        pirs = [
            pir for pir in pirs
            if (pir_min is None or pir >= pir_min) and (pir_max is None or pir <= pir_max)
        ]

    if not pirs:
        print("Error: No data found for plotting (after applying PIR range filter)")
        return

    # For Mesh you can optionally scale PIR (e.g., by number of nodes).
    # Here we plot raw PIR (packets/cycle per node).
    pirs_for_x = pirs

    # Pre-compute baseline (RR) values for each PIR (only needed for relative plots)
    rr_baseline = {}
    if not absolute:
        rr_data = results_by_strategy.get('RANDOM', {})
        for pir in pirs:
            base_val = 0.0
            if pir in rr_data:
                base_val = rr_data[pir].get(parameter, 0.0)
                # For throughput, convert from flits/cycle to packets/cycle (divide by 8)
                if parameter == 'throughput':
                    base_val = base_val / 8.0
            rr_baseline[pir] = base_val

    # Extract data for each strategy
    data = {}
    for strategy_name, strategy_data in results_by_strategy.items():
        strategy_values = []
        for pir in pirs:
            if pir in strategy_data:
                value = strategy_data[pir].get(parameter, 0.0)
                # For throughput, convert from flits/cycle to packets/cycle (divide by 8)
                if parameter == 'throughput':
                    value = value / 8.0
                if absolute:
                    # Absolute metric values (value is already in correct units)
                    strategy_values.append(value)
                else:
                    base = rr_baseline.get(pir, 0.0)
                    # Relative difference in percent.
                    # For most metrics: (RR - Arb)/RR * 100  (smaller is better -> positive is good)
                    # For throughput (larger is better) we invert the sign so that
                    # improvements give negative values (negative is good).
                    if base != 0:
                        if parameter == 'throughput':
                            rel = (value - base) / base * 100.0  # inverted sign compared to delay/energy case
                        else:
                            rel = (base - value) / base * 100.0
                    else:
                        rel = 0.0
                    strategy_values.append(rel)
            else:
                strategy_values.append(0.0)
        if any(strategy_values):
            if smooth and len(strategy_values) > 2:
                data[strategy_name] = smooth_data(strategy_values, window_size=3)
            else:
                data[strategy_name] = strategy_values

    if not data:
        print("Error: No data found for any strategy")
        return

    plt.figure(figsize=(10, 6))

    for strategy_name, values in data.items():
        strategy_display = ARBITRATION_STRATEGIES[strategy_name]
        style = STRATEGY_STYLE.get(strategy_name, {'color': 'black', 'marker': 'o', 'linestyle': '-'})
        plt.plot(
            pirs_for_x,
            values,
            label=strategy_display,
            color=style['color'],
            marker=style['marker'],
            linestyle=style['linestyle'],
            linewidth=2,
            markersize=6
        )

    plt.xlabel('PIR (packet injection rate per node)', fontsize=12)
    # Y label: either absolute metric value or relative difference
    if absolute:
        plt.ylabel(f"{param_label_en}", fontsize=12)
    else:
        plt.ylabel(f"{param_label_en}, (RR-ARB), %", fontsize=12)

    ax = plt.gca()
    ax.set_xticks(pirs_for_x)
    ax.xaxis.set_major_formatter(ticker.FuncFormatter(lambda x, p: f'{x:.2f}'))
    # Highlight y = 0 baseline (RR reference) only for relative plots
    if not absolute:
        ax.axhline(0.0, color='black', linewidth=1.5, linestyle='--', alpha=0.7)

    # Title: remove traffic info if traffic is averaged
    if traffic_pattern and 'averaged' in traffic_pattern.lower():
        # Extract mesh and routing from traffic_pattern
        # Format: "averaged over N traffic patterns (mesh, routing)"
        match = re.search(r'\(([^,]+),\s*([^)]+)\)', traffic_pattern)
        if match:
            mesh_info = match.group(1)
            routing_info = match.group(2)
            title = f'Mesh Arbitration Comparison ({mesh_info}, {routing_info})'
        else:
            title = 'Mesh Arbitration Comparison'
    elif traffic_pattern:
        title = f'Mesh Arbitration Comparison, Traffic: {traffic_pattern}'
    else:
        title = 'Mesh Arbitration Comparison'
    plt.title(title, fontsize=14)
    plt.grid(True, alpha=0.3)
    plt.legend(fontsize=10)
    plt.tight_layout()

    if output_file:
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        print(f"Plot saved to: {output_file}")

    if show_plot:
        plt.show()
    else:
        plt.close()


def main():
    parser = argparse.ArgumentParser(
        description='Plot Mesh arbitration algorithm comparison results (4x4/8x8/16x16, by routing: XY, WEST_FIRST, etc.)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f'''
Available parameters:
  {chr(10).join(f"  {k:15} - {v[1]}" for k, v in PARAMETERS.items())}

Examples:
  python plot_mesh_arbitration_results.py packets --routing XY --traffic TRAFFIC_RANDOM
  python plot_mesh_arbitration_results.py avg_delay --mesh 8x8 --routing WEST_FIRST --traffic TRAFFIC_SHUFFLE --output mesh_delay.png
  python plot_mesh_arbitration_results.py throughput --routing XY  # averages over all traffic patterns
  python plot_mesh_arbitration_results.py total_energy --routing XY --traffic TRAFFIC_BUTTERFLY --no-show
  python plot_mesh_arbitration_results.py throughput  # will list available routing algorithms
        '''
    )

    parser.add_argument(
        'parameter',
        choices=list(PARAMETERS.keys()),
        help='Parameter to plot'
    )

    parser.add_argument(
        '--results-dir',
        type=str,
        default='results',
        help='Root directory containing Mesh result subdirectories (mesh4x4, mesh8x8, etc., each with routing subfolders XY, WEST_FIRST, ...). Default: results'
    )

    parser.add_argument(
        '--mesh',
        type=str,
        choices=['4x4', '8x8', '16x16'],
        default='4x4',
        help='Mesh size to plot: 4x4, 8x8 or 16x16 (default: 4x4)'
    )

    parser.add_argument(
        '--routing', '-r',
        type=str,
        help='Routing algorithm subfolder (e.g., XY, WEST_FIRST, NORTH_LAST, NEGATIVE_FIRST, ODD_EVEN). '
             'If omitted but traffic is specified, results will be averaged over all routing algorithms.'
    )

    parser.add_argument(
        '--traffic', '-t',
        type=str,
        help='Traffic pattern to plot (e.g., TRAFFIC_RANDOM). '
             'If not specified, results will be averaged over all available traffic patterns.'
    )

    parser.add_argument(
        '--output',
        type=str,
        help='Output file for the plot (e.g., plot.png). If not specified, shows interactive plot.'
    )

    parser.add_argument(
        '--no-show',
        action='store_true',
        help='Do not display the plot (useful when saving to file)'
    )

    parser.add_argument(
        '--no-smooth',
        action='store_true',
        help='Disable data smoothing (moving average)'
    )

    parser.add_argument(
        '--pir-min',
        type=float,
        help='Lower bound for PIR to include in the plot (e.g., 0.40)'
    )

    parser.add_argument(
        '--pir-max',
        type=float,
        help='Upper bound for PIR to include in the plot (e.g., 0.70)'
    )

    parser.add_argument(
        '--absolute',
        action='store_true',
        help='Plot absolute metric values instead of relative (RR-ARB)/RR*100%. RANDOM (RR) is plotted as a separate curve.'
    )

    args = parser.parse_args()

    # Determine mesh root directory based on selected mesh size
    mesh_subdir = f"mesh{args.mesh}"
    mesh_root = os.path.join(args.results_dir, mesh_subdir)

    # Discover available routing algorithms (subfolders: XY, WEST_FIRST, ...)
    available_routing = get_available_routing_algorithms(mesh_root)
    if not available_routing:
        print(f"Error: No routing subdirectories found in {mesh_root}")
        print("Expected structure: results/mesh4x4/XY/, results/mesh4x4/WEST_FIRST/, ...")
        sys.exit(1)

    aggregated_over_traffic = False
    aggregated_over_routing = False
    aggregated_over_global = False

    # Case 1: routing specified (possibly aggregate over traffic)
    if args.routing:
        if args.routing not in available_routing:
            print(f"Error: Routing '{args.routing}' not found for mesh {args.mesh}.")
            print(f"Available routings: {', '.join(available_routing)}")
            sys.exit(1)

        # Discover available traffic patterns under mesh_root/routing
        available_traffic = get_available_traffic_patterns(mesh_root, args.routing)
        if not available_traffic:
            print(f"Error: No traffic pattern directories found in {mesh_root}/{args.routing}")
            sys.exit(1)

        if not args.traffic:
            # If traffic not specified, average over all traffic patterns
            print(f"Traffic pattern not specified. Averaging over all traffic patterns for routing={args.routing}.")
            print(f"Available traffic patterns: {', '.join(available_traffic)}")
            print("Loading and averaging results from all traffic patterns...")
            results_by_strategy = load_all_results_averaged_over_traffic(mesh_root, args.routing)
            traffic_label = f"averaged over {len(available_traffic)} traffic patterns"
            aggregated_over_traffic = True
        else:
            if args.traffic not in available_traffic:
                print(f"Error: Traffic pattern '{args.traffic}' not found for mesh {args.mesh}, routing {args.routing}.")
                print(f"Available patterns: {', '.join(available_traffic)}")
                sys.exit(1)

            print(f"Loading Mesh arbitration results from: {mesh_root}/{args.routing}/{args.traffic}")
            results_by_strategy = load_all_results(mesh_root, args.routing, args.traffic)
            traffic_label = args.traffic

    # Case 2: routing not specified, but traffic is specified -> average over all routing algorithms
    elif args.traffic:
        print(f"Routing algorithm not specified. Averaging over all routing algorithms for traffic={args.traffic}.")
        print(f"Available routing algorithms: {', '.join(available_routing)}")
        print("Loading and averaging results from all routing algorithms...")
        results_by_strategy = load_all_results_averaged_over_routing(mesh_root, args.traffic)
        traffic_label = f"{args.traffic} (all routings)"
        aggregated_over_routing = True

    # Case 3: neither routing nor traffic specified -> average over all routings and all traffic patterns for 4x4 and 8x8
    else:
        print(f"Routing algorithm and traffic pattern not specified.")
        print(f"Averaging over all routing algorithms and all traffic patterns in {args.results_dir} for mesh4x4 and mesh8x8.")
        results_by_strategy = load_all_results_global(args.results_dir)
        traffic_label = "all traffic & all routings (4x4+8x8)"
        aggregated_over_global = True

    total_strategies = sum(1 for strategy_data in results_by_strategy.values() if strategy_data)
    if total_strategies == 0:
        if aggregated_over_global:
            print(f"Error: No result files found under {args.results_dir} for any routing/traffic in mesh4x4 or mesh8x8.")
        elif aggregated_over_routing:
            print(f"Error: No result files found for traffic {args.traffic} in any routing under {mesh_root}")
        elif aggregated_over_traffic:
            print(f"Error: No result files found for any traffic under {mesh_root}/{args.routing}")
        else:
            print(f"Error: No result files found in {mesh_root}/{args.routing}/{args.traffic}")
        print("Expected files: mesh_arbitration_PIR_*.txt")
        sys.exit(1)

    print(f"Found data for {total_strategies} arbitration strategies")

    # Build traffic_pattern label for the plot
    # For fully global aggregation (all meshes, all routing, all traffic) we suppress the title
    if aggregated_over_global:
        traffic_pattern_label = None
    elif aggregated_over_routing:
        traffic_pattern_label = f"{traffic_label} ({args.mesh})"
    else:
        traffic_pattern_label = f"{traffic_label} ({args.mesh}, {args.routing})"

    plot_parameter(
        results_by_strategy,
        args.parameter,
        traffic_pattern=traffic_pattern_label,
        output_file=args.output,
        show_plot=not args.no_show,
        smooth=not args.no_smooth,
        pir_min=args.pir_min,
        pir_max=args.pir_max,
        absolute=args.absolute
    )


if __name__ == '__main__':
    main()

