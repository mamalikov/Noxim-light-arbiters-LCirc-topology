#!/usr/bin/env python3
"""
Offline analysis of Mesh arbitration results

Collects arbitration statistics:
- which arbiter is better/worse on average over all PIR;
- which arbiter is better/worse in PIR ranges (low/medium/high);
- per traffic profile and per routing algorithm.

Metrics:
- throughput (higher is better)
- avg_delay, max_delay (lower is better)
"""

from pathlib import Path
from collections import defaultdict
import statistics

# Reuse parser and dictionaries from the plotting script
from plot_mesh_arbitration_results import (
    PARAMETERS,
    ARBITRATION_STRATEGIES,
    parse_result_file,
)

METRICS = ["throughput", "avg_delay", "max_delay"]

# True = higher is better, False = lower is better
BEST_IS_MAX = {
    "throughput": True,
    "avg_delay": False,
    "max_delay": False,
}


def pir_range_label(pir: float) -> str:
    """
    Split PIR into ranges:
    - low:   0.01–0.03
    - medium:0.04–0.07
    - high:  0.08–1.00
    """
    if pir < 0.04:
        return "low"
    elif pir <= 0.07:
        return "medium"
    else:
        return "high"


def main():
    root = Path("results")
    meshes = ["mesh4x4", "mesh8x8"]  # analyze only 4x4 and 8x8

    # data[(mesh, routing, traffic, strategy, metric, range)] -> [values...]
    data = defaultdict(list)

    # For comparing routing / traffic for RANDOM:
    # random_raw[(mesh, routing, traffic, metric)] -> [values over all PIR]
    random_raw = defaultdict(list)

    for mesh in meshes:
        mesh_root = root / mesh
        if not mesh_root.exists():
            continue

        # routing subdirectories: XY, WEST_FIRST, ...
        for routing_dir in sorted(d for d in mesh_root.iterdir() if d.is_dir()):
            routing = routing_dir.name

            # traffic profiles under given routing: TRAFFIC_*
            for traffic_dir in sorted(
                d for d in routing_dir.iterdir() if d.is_dir() and d.name.startswith("TRAFFIC_")
            ):
                traffic = traffic_dir.name

                for result_file in sorted(traffic_dir.glob("mesh_arbitration_PIR_*.txt")):
                    parsed = parse_result_file(result_file)
                    if not parsed:
                        continue

                    pir = parsed["PIR"]
                    rng = pir_range_label(pir)

                    for strategy_name, strat_results in parsed["strategies"].items():
                        for metric in METRICS:
                            val = strat_results.get(metric)
                            if val is None:
                                continue
                            key = (mesh, routing, traffic, strategy_name, metric, rng)
                            data[key].append(val)

                        # Additionally store raw values for RANDOM
                        if strategy_name == "RANDOM":
                            for metric in METRICS:
                                val = strat_results.get(metric)
                                if val is None:
                                    continue
                                random_raw[(mesh, routing, traffic, metric)].append(val)

    # Compute averages for each key
    avg_data = {}
    for key, values in data.items():
        if not values:
            continue
        avg_data[key] = statistics.mean(values)

    # Count wins/losses per strategy
    # wins[(mesh, routing, traffic, metric, range)] -> best_strategy_name
    wins = {}
    # and also global win frequency statistics per metric
    win_counts_overall = defaultdict(int)  # (strategy, metric) -> count
    win_counts_range = defaultdict(int)    # (strategy, metric, range) -> count

    # Numerical improvements relative to RANDOM:
    # rel_improvements[(strategy, metric)] -> [percent values...]
    # rel_improvements_range[(strategy, metric, range)] -> [percent values...]
    rel_improvements = defaultdict(list)
    rel_improvements_range = defaultdict(list)

    for mesh in meshes:
        for routing in sorted(
            d.name for d in (root / mesh).iterdir() if (root / mesh / d.name).is_dir()
        ) if (root / mesh).exists() else []:
            mesh_root = root / mesh / routing
            if not mesh_root.exists():
                continue

            traffics = sorted(
                d.name for d in mesh_root.iterdir() if d.is_dir() and d.name.startswith("TRAFFIC_")
            )
            for traffic in traffics:
                for metric in METRICS:
                    for rng in ["low", "medium", "high"]:
                        # Collect averages for all strategies for this (mesh,routing,traffic,metric,range)
                        strat_vals = []
                        for strategy_name in ARBITRATION_STRATEGIES.keys():
                            key = (mesh, routing, traffic, strategy_name, metric, rng)
                            if key in avg_data:
                                strat_vals.append((strategy_name, avg_data[key]))

                        if not strat_vals:
                            continue

                        # Determine the best strategy
                        if BEST_IS_MAX[metric]:
                            best = max(strat_vals, key=lambda x: x[1])
                        else:
                            best = min(strat_vals, key=lambda x: x[1])

                        wins[(mesh, routing, traffic, metric, rng)] = best[0]
                        win_counts_overall[(best[0], metric)] += 1
                        win_counts_range[(best[0], metric, rng)] += 1

                        # At the same time accumulate relative improvements vs RANDOM
                        # based on averaged values in the same PIR range.
                        for strategy_name in ARBITRATION_STRATEGIES.keys():
                            if strategy_name == "RANDOM":
                                continue
                            key_s = (mesh, routing, traffic, strategy_name, metric, rng)
                            key_r = (mesh, routing, traffic, "RANDOM", metric, rng)
                            if key_s not in avg_data or key_r not in avg_data:
                                continue
                            val_s = avg_data[key_s]
                            val_r = avg_data[key_r]
                            if val_r <= 0:
                                continue

                            if BEST_IS_MAX[metric]:
                                # throughput: (S - R)/R * 100, positive = improvement
                                rel = (val_s - val_r) / val_r * 100.0
                            else:
                                # delays: (R - S)/R * 100, positive = lower delay (better)
                                rel = (val_r - val_s) / val_r * 100.0

                            rel_improvements[(strategy_name, metric)].append(rel)
                            rel_improvements_range[(strategy_name, metric, rng)].append(rel)

    # Print aggregated statistics
    print("========== SUMMARY BY STRATEGY / METRIC (ALL PIR RANGES, ALL MESHES, ROUTING, TRAFFIC) ==========")
    for metric in METRICS:
        print(f"\nMetric: {metric}")
        for strategy_name in ARBITRATION_STRATEGIES.keys():
            count = win_counts_overall.get((strategy_name, metric), 0)
            print(f"  {strategy_name:15s}: wins = {count}")

    print("\n========== SUMMARY BY STRATEGY / METRIC / PIR RANGE ==========")
    for metric in METRICS:
        print(f"\nMetric: {metric}")
        for rng in ["low", "medium", "high"]:
            print(f"  PIR range: {rng}")
            for strategy_name in ARBITRATION_STRATEGIES.keys():
                count = win_counts_range.get((strategy_name, metric, rng), 0)
                print(f"    {strategy_name:15s}: wins = {count}")

    # Additionally: numerical average improvements relative to RANDOM
    print("\n========== AVERAGE RELATIVE IMPROVEMENT vs RANDOM (%, + is better) ==========")
    for metric in METRICS:
        print(f"\nMetric: {metric}")
        for strategy_name in ARBITRATION_STRATEGIES.keys():
            if strategy_name == "RANDOM":
                continue
            vals = rel_improvements.get((strategy_name, metric))
            if not vals:
                continue
            avg_rel = statistics.mean(vals)
            print(f"  {strategy_name:15s}: {avg_rel:7.2f} %")

    print("\n========== AVERAGE RELATIVE IMPROVEMENT vs RANDOM BY PIR RANGE (%, + is better) ==========")
    for metric in METRICS:
        print(f"\nMetric: {metric}")
        for rng in ["low", "medium", "high"]:
            print(f"  PIR range: {rng}")
            for strategy_name in ARBITRATION_STRATEGIES.keys():
                if strategy_name == "RANDOM":
                    continue
                vals = rel_improvements_range.get((strategy_name, metric, rng))
                if not vals:
                    continue
                avg_rel = statistics.mean(vals)
                print(f"    {strategy_name:15s}: {avg_rel:7.2f} %")

    # For each mesh and routing compute which strategy wins most often per metric
    print("\n========== PER MESH & ROUTING: MOST FREQUENT WINNER PER METRIC ==========")
    per_mr_counts = defaultdict(lambda: defaultdict(int))  # (mesh, routing, metric) -> strategy -> count
    for (mesh, routing, traffic, metric, rng), strat in wins.items():
        per_mr_counts[(mesh, routing, metric)][strat] += 1

    for (mesh, routing, metric), strat_counter in sorted(per_mr_counts.items()):
        if not strat_counter:
            continue
        best_strat, best_count = max(strat_counter.items(), key=lambda x: x[1])
        print(f"{mesh:7s} / {routing:15s} / {metric:10s} -> best overall: {best_strat} (wins={best_count})")

    # ======================================================================
    # Compare strategies within each traffic profile (aggregated across all meshes)
    # ======================================================================
    print("\n========== PER TRAFFIC PROFILE (ALL MESHES): MOST FREQUENT WINNER PER METRIC ==========")
    traffic_win_counts = defaultdict(lambda: defaultdict(int))  # (traffic, metric) -> strategy -> count
    for (mesh, routing, traffic, metric, rng), strat in wins.items():
        traffic_win_counts[(traffic, metric)][strat] += 1

    for (traffic, metric), strat_counter in sorted(traffic_win_counts.items()):
        if not strat_counter:
            continue
        best_strat, best_count = max(strat_counter.items(), key=lambda x: x[1])
        print(f"{traffic:25s} / {metric:10s} -> best overall: {best_strat} (wins={best_count})")

    # ======================================================================
    # Compare strategies within traffic profiles separately for 4x4 and 8x8
    # ======================================================================
    print("\n========== PER TRAFFIC PROFILE AND MESH: MOST FREQUENT WINNER PER METRIC ==========")
    traffic_mesh_win_counts = defaultdict(lambda: defaultdict(int))  # (mesh, traffic, metric) -> strategy -> count
    for (mesh, routing, traffic, metric, rng), strat in wins.items():
        traffic_mesh_win_counts[(mesh, traffic, metric)][strat] += 1

    for (mesh, traffic, metric), strat_counter in sorted(traffic_mesh_win_counts.items()):
        if not strat_counter:
            continue
        best_strat, best_count = max(strat_counter.items(), key=lambda x: x[1])
        print(f"{mesh:7s} / {traffic:25s} / {metric:10s} -> best overall: {best_strat} (wins={best_count})")

    # ======================================================================
    # Compare routing algorithms and traffic profiles (based on RANDOM)
    # ======================================================================
    print("\n========== ROUTING COMPARISON (RANDOM only, averaged over all PIR & traffic) ==========")
    for mesh in meshes:
        print(f"\nMesh: {mesh}")
        # Collect averages per routing, averaging over traffic
        routing_metrics = defaultdict(lambda: defaultdict(list))  # routing -> metric -> [vals]
        for (m, routing, traffic, metric), vals in random_raw.items():
            if m != mesh:
                continue
            if not vals:
                continue
            avg_val = statistics.mean(vals)
            routing_metrics[routing][metric].append(avg_val)

        # Print averaged values for each routing
        for routing, mvals in sorted(routing_metrics.items()):
            print(f"  Routing: {routing}")
            for metric in METRICS:
                vals = mvals.get(metric)
                if not vals:
                    continue
                avg_over_traffic = statistics.mean(vals)
                print(f"    {metric:10s}: {avg_over_traffic:10.4f}")

    print("\n========== TRAFFIC PROFILE COMPARISON (RANDOM only, averaged over all PIR & routing) ==========")
    for mesh in meshes:
        print(f"\nMesh: {mesh}")
        traffic_metrics = defaultdict(lambda: defaultdict(list))  # traffic -> metric -> [vals]
        for (m, routing, traffic, metric), vals in random_raw.items():
            if m != mesh:
                continue
            if not vals:
                continue
            avg_val = statistics.mean(vals)
            traffic_metrics[traffic][metric].append(avg_val)

        for traffic, mvals in sorted(traffic_metrics.items()):
            print(f"  Traffic: {traffic}")
            for metric in METRICS:
                vals = mvals.get(metric)
                if not vals:
                    continue
                avg_over_routing = statistics.mean(vals)
                print(f"    {metric:10s}: {avg_over_routing:10.4f}")


if __name__ == "__main__":
    main()

