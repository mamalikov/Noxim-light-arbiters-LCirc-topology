#!/bin/bash

# Script to run Noxim with several arbitration algorithms
# for all traffic patterns and two routing algorithms (LCirc & VirtualCoord).
# For each PIR, traffic profile and routing algorithm, results for all
# arbitration algorithms are saved to a separate file in arb_results/.
# Usage: ./run_arbitration_comparison.sh

# Get the directory where the script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BIN_DIR="${SCRIPT_DIR}/bin"
CONFIG_DIR="${SCRIPT_DIR}/config_examples"
NOXIM_BIN="${BIN_DIR}/noxim"

# Mesh-specific configurations and results directories
MESH4_CONFIG_FILE="${CONFIG_DIR}/default_configMeshNoHUB.yaml"
MESH8_CONFIG_FILE="${CONFIG_DIR}/default_configMeshNoHUB_8x8.yaml"
MESH16_CONFIG_FILE="${CONFIG_DIR}/default_configMeshNoHUB_16x16.yaml"
MESH4_RESULTS_ROOT="${SCRIPT_DIR}/results/mesh4x4"
MESH8_RESULTS_ROOT="${SCRIPT_DIR}/results/mesh8x8"
MESH16_RESULTS_ROOT="${SCRIPT_DIR}/results/mesh16x16"

# Check if noxim binary exists
if [ ! -f "$NOXIM_BIN" ]; then
    echo "Error: noxim binary not found at $NOXIM_BIN"
    echo "Please compile noxim first: cd bin && make"
    exit 1
fi

# Check mesh configs exist and create mesh results root directories
if [ ! -f "$MESH4_CONFIG_FILE" ]; then
    echo "Error: Mesh 4x4 config file not found: $MESH4_CONFIG_FILE"
    exit 1
fi
if [ ! -f "$MESH8_CONFIG_FILE" ]; then
    echo "Error: Mesh 8x8 config file not found: $MESH8_CONFIG_FILE"
    exit 1
fi
if [ ! -f "$MESH16_CONFIG_FILE" ]; then
    echo "Error: Mesh 16x16 config file not found: $MESH16_CONFIG_FILE"
    exit 1
fi
mkdir -p "$MESH4_RESULTS_ROOT"
mkdir -p "$MESH8_RESULTS_ROOT"
mkdir -p "$MESH16_RESULTS_ROOT"

# Arbitration strategies to test
# Format: "strategy_name:display_name"
ARBITRATION_STRATEGIES=(
    "RANDOM:Random"
    "HOPCOUNT_MAX:Hopcount Max"
    "HOPCOUNT_MIN:Hopcount Min"
    "DISTANCE_MIN:Distance Min"
    "DISTANCE_MAX:Distance Max"
)

# Function to parse statistics from noxim output
parse_stats() {
    local output="$1"
    
    # Extract statistics using grep and awk
    received_packets=$(echo "$output" | grep "^% Total received packets:" | awk '{print $NF}')
    received_flits=$(echo "$output" | grep "^% Total received flits:" | awk '{print $NF}')
    avg_delay=$(echo "$output" | grep "^% Global average delay" | awk '{print $NF}')
    max_delay=$(echo "$output" | grep "^% Max delay" | awk '{print $NF}')
    network_throughput=$(echo "$output" | grep "^% Network throughput" | awk '{print $NF}')
    ip_throughput=$(echo "$output" | grep "^% Average IP throughput" | awk '{print $NF}')
    total_energy=$(echo "$output" | grep "^% Total energy" | awk '{print $NF}')
    dynamic_energy=$(echo "$output" | grep "Dynamic energy" | awk '{print $NF}')
    static_energy=$(echo "$output" | grep "Static energy" | awk '{print $NF}')
    
    # Return as key=value pairs
    echo "received_packets=$received_packets"
    echo "received_flits=$received_flits"
    echo "avg_delay=$avg_delay"
    echo "max_delay=$max_delay"
    echo "network_throughput=$network_throughput"
    echo "ip_throughput=$ip_throughput"
    echo "total_energy=$total_energy"
    echo "dynamic_energy=$dynamic_energy"
    echo "static_energy=$static_energy"
}

# Function to normalize number (convert scientific notation to decimal)
normalize_number() {
    local num="$1"
    if [[ "$num" =~ [eE] ]]; then
        # Convert scientific notation using awk
        echo "$num" | awk '{printf "%.10f", $1}'
    else
        echo "$num"
    fi
}

# Function to format number (add leading zero if needed)
format_number() {
    local num="$1"
    # Remove leading/trailing whitespace
    num=$(echo "$num" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
    # Add leading zero if starts with dot
    if [[ "$num" =~ ^\. ]]; then
        echo "0$num"
    else
        echo "$num"
    fi
}

# Traffic patterns to test (same as in LCirc experiments)
# Format: "traffic_param_value:display_name"
TRAFFIC_PATTERNS=(
    "random:TRAFFIC_RANDOM"
    "transpose1:TRAFFIC_TRANSPOSE1"
    "bitreversal:TRAFFIC_BIT_REVERSAL"
    "shuffle:TRAFFIC_SHUFFLE"
    "butterfly:TRAFFIC_BUTTERFLY"
)

# Routing algorithms to test (results saved in subfolders: WEST_FIRST, ...)
ROUTING_ALGORITHMS=( "WEST_FIRST" "NORTH_LAST" "NEGATIVE_FIRST" "ODD_EVEN" )

# Function to calculate average from array of values
calculate_average() {
    local values=("$@")
    local count=${#values[@]}
    
    if [ $count -eq 0 ]; then
        echo "0.000000"
        return
    fi
    
    # Use awk for all calculations (handles scientific notation better)
    printf '%s\n' "${values[@]}" | awk '{
        if ($0 != "" && $0 != " ") {
            sum += $0
            count++
        }
    }
    END {
        if (count > 0) {
            result = sum / count
            # Format with leading zero if needed
            if (result < 1 && result > 0) {
                printf "0%.6f", result
            } else {
                printf "%.6f", result
            }
        } else {
            printf "0.000000"
        }
    }'
}

# Generate PIR values:
#  - from 0.01 to 0.09 with step 0.01
pir_values=$(awk 'BEGIN {for(i=1; i<=10; i++) printf "%.2f ", i*0.01}')

# =========================================
# MESH 4x4 RUNS (ACTIVE) — all routing algorithms
# =========================================
echo "========================================="
echo "Starting Mesh 4x4 arbitration comparison (all routing algorithms)..."
echo "Mesh 4x4 config: $MESH4_CONFIG_FILE"
echo "Mesh 4x4 results root: $MESH4_RESULTS_ROOT"
echo "Routing: WEST_FIRST, NORTH_LAST, NEGATIVE_FIRST, ODD_EVEN"
echo "Traffic patterns: random, transpose1, bitreversal, shuffle, butterfly"
echo "========================================="

for routing_algorithm in "${ROUTING_ALGORITHMS[@]}"; do
    echo ""
    echo "========== [4x4] Routing: $routing_algorithm =========="

    for traffic_entry in "${TRAFFIC_PATTERNS[@]}"; do
        IFS=':' read -r traffic_param traffic_name <<< "$traffic_entry"
        traffic_results_dir="${MESH4_RESULTS_ROOT}/${routing_algorithm}/${traffic_name}"
        mkdir -p "$traffic_results_dir"

        echo "-----------------------------------------"
        echo "[4x4] Routing: $routing_algorithm, Traffic: $traffic_name (param=$traffic_param)"
        echo "Results dir: $traffic_results_dir"
        echo "-----------------------------------------"

        for pir in $pir_values; do
            pir_str=$(printf "%.2f" "$pir" | tr '.' '_')
            OUTPUT_FILE_PIR="${traffic_results_dir}/mesh_arbitration_PIR_${pir_str}.txt"

            {
                echo "========================================="
                echo "Mesh Arbitration Algorithms Comparison"
                echo "Topology: MESH (No HUB)"
                echo "Config: $(basename "$MESH4_CONFIG_FILE")"
                echo "Routing: $routing_algorithm"
                echo "Traffic pattern: $traffic_name (param=$traffic_param)"
                echo "PIR: $pir"
                echo "Mesh size: 4x4"
                echo "Date: $(date)"
                echo "========================================="
                echo ""
            } > "$OUTPUT_FILE_PIR"

            echo "[4x4]  $routing_algorithm / $traffic_name  PIR: $pir -> $OUTPUT_FILE_PIR"

            for strategy_entry in "${ARBITRATION_STRATEGIES[@]}"; do
                IFS=':' read -r strategy_name strategy_display <<< "$strategy_entry"

                echo "--- $strategy_display ($strategy_name) ---" | tee -a "$OUTPUT_FILE_PIR"

                declare -a received_packets_array received_flits_array avg_delay_array max_delay_array
                declare -a network_throughput_array ip_throughput_array total_energy_array
                declare -a dynamic_energy_array static_energy_array

                echo "Running $strategy_display with PIR=$pir on Mesh 4x4, routing=$routing_algorithm (10 successful runs)..." | tee -a "$OUTPUT_FILE_PIR"

                successful_runs=0
                total_attempts=0
                max_attempts=30

                while [ $successful_runs -lt 10 ] && [ $total_attempts -lt $max_attempts ]; do
                    total_attempts=$((total_attempts + 1))
                    echo "  Attempt $total_attempts (successful: $successful_runs/10)..." | tee -a "$OUTPUT_FILE_PIR"

                    cd "$BIN_DIR"
                    output=$("$NOXIM_BIN" -config "$MESH4_CONFIG_FILE" -routing "$routing_algorithm" -sel "$strategy_name" -pir "$pir" poisson -traffic "$traffic_param" 2>&1)

                    stats=$(parse_stats "$output")

                    received_packets=$(echo "$stats" | grep "received_packets=" | cut -d'=' -f2 | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
                    received_flits=$(echo "$stats" | grep "received_flits=" | cut -d'=' -f2 | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
                    avg_delay=$(echo "$stats" | grep "avg_delay=" | cut -d'=' -f2 | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
                    max_delay=$(echo "$stats" | grep "max_delay=" | cut -d'=' -f2 | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
                    network_throughput=$(echo "$stats" | grep "network_throughput=" | cut -d'=' -f2 | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
                    ip_throughput=$(echo "$stats" | grep "ip_throughput=" | cut -d'=' -f2 | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
                    total_energy=$(echo "$stats" | grep "total_energy=" | cut -d'=' -f2 | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
                    dynamic_energy=$(echo "$stats" | grep "dynamic_energy=" | cut -d'=' -f2 | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
                    static_energy=$(echo "$stats" | grep "static_energy=" | cut -d'=' -f2 | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')

                    [ -n "$total_energy" ] && total_energy=$(normalize_number "$total_energy")
                    [ -n "$dynamic_energy" ] && dynamic_energy=$(normalize_number "$dynamic_energy")
                    [ -n "$static_energy" ] && static_energy=$(normalize_number "$static_energy")

                    [ -z "$received_packets" ] && received_packets=0
                    [ -z "$received_flits" ] && received_flits=0
                    [ -z "$avg_delay" ] && avg_delay=0
                    [ -z "$max_delay" ] && max_delay=0
                    [ -z "$network_throughput" ] && network_throughput=0
                    [ -z "$ip_throughput" ] && ip_throughput=0
                    [ -z "$total_energy" ] && total_energy=0
                    [ -z "$dynamic_energy" ] && dynamic_energy=0
                    [ -z "$static_energy" ] && static_energy=0

                    received_packets_int=$(echo "$received_packets" | awk '{printf "%d", $1}')

                    if [ "$received_packets_int" -eq 0 ]; then
                        echo "    Warning: Received 0 packets, skipping this run and retrying..." | tee -a "$OUTPUT_FILE_PIR"
                        continue
                    fi

                    idx=$successful_runs
                    received_packets_array[$idx]=$received_packets
                    received_flits_array[$idx]=$received_flits
                    avg_delay_array[$idx]=$avg_delay
                    max_delay_array[$idx]=$max_delay
                    network_throughput_array[$idx]=$network_throughput
                    ip_throughput_array[$idx]=$ip_throughput
                    total_energy_array[$idx]=$total_energy
                    dynamic_energy_array[$idx]=$dynamic_energy
                    static_energy_array[$idx]=$static_energy

                    successful_runs=$((successful_runs + 1))
                done

                if [ $successful_runs -lt 10 ]; then
                    echo "    Warning: Only $successful_runs successful runs out of $total_attempts attempts!" | tee -a "$OUTPUT_FILE_PIR"
                else
                    echo "    Completed: $successful_runs successful runs in $total_attempts attempts" | tee -a "$OUTPUT_FILE_PIR"
                fi

                echo "" | tee -a "$OUTPUT_FILE_PIR"
                echo "AVERAGED RESULTS for $strategy_display ($strategy_name) (PIR=$pir, $successful_runs runs):" | tee -a "$OUTPUT_FILE_PIR"
                avg_val=$(calculate_average "${received_packets_array[@]}")
                echo "  Total received packets: $(format_number "$avg_val")" | tee -a "$OUTPUT_FILE_PIR"
                avg_val=$(calculate_average "${received_flits_array[@]}")
                echo "  Total received flits: $(format_number "$avg_val")" | tee -a "$OUTPUT_FILE_PIR"
                avg_val=$(calculate_average "${avg_delay_array[@]}")
                echo "  Global average delay (cycles): $(format_number "$avg_val")" | tee -a "$OUTPUT_FILE_PIR"
                avg_val=$(calculate_average "${max_delay_array[@]}")
                echo "  Max delay (cycles): $(format_number "$avg_val")" | tee -a "$OUTPUT_FILE_PIR"
                avg_val=$(calculate_average "${network_throughput_array[@]}")
                echo "  Network throughput (flits/cycle): $(format_number "$avg_val")" | tee -a "$OUTPUT_FILE_PIR"
                avg_val=$(calculate_average "${ip_throughput_array[@]}")
                echo "  Average IP throughput (flits/cycle/IP): $(format_number "$avg_val")" | tee -a "$OUTPUT_FILE_PIR"
                avg_val=$(calculate_average "${total_energy_array[@]}")
                echo "  Total energy (J): $(format_number "$avg_val")" | tee -a "$OUTPUT_FILE_PIR"
                avg_val=$(calculate_average "${dynamic_energy_array[@]}")
                echo "  Dynamic energy (J): $(format_number "$avg_val")" | tee -a "$OUTPUT_FILE_PIR"
                avg_val=$(calculate_average "${static_energy_array[@]}")
                echo "  Static energy (J): $(format_number "$avg_val")" | tee -a "$OUTPUT_FILE_PIR"
                echo "" | tee -a "$OUTPUT_FILE_PIR"
            done

            echo "[4x4]  Mesh results for PIR=$pir (routing=$routing_algorithm, traffic=$traffic_name) saved to: $OUTPUT_FILE_PIR"
            echo ""
        done

        echo "[4x4] Finished simulations for routing=$routing_algorithm, traffic: $traffic_name"
        echo ""
    done
done

echo "========================================="
echo "All Mesh 4x4 simulations completed!"
echo "Results saved in: $MESH4_RESULTS_ROOT"
echo "Directory structure: results/mesh4x4/<ROUTING>/TRAFFIC_*/mesh_arbitration_PIR_*.txt"
echo "========================================="

# =========================================
# MESH 8x8 RUNS (ACTIVE) — all routing algorithms
# =========================================
echo ""
echo "========================================="
echo "Starting Mesh 8x8 arbitration comparison (all routing algorithms)..."
echo "Mesh 8x8 config: $MESH8_CONFIG_FILE"
echo "Mesh 8x8 results root: $MESH8_RESULTS_ROOT"
echo "Routing: XY, WEST_FIRST, NORTH_LAST, NEGATIVE_FIRST, ODD_EVEN"
echo "Traffic patterns: random, transpose1, bitreversal, shuffle, butterfly"
echo "========================================="

for routing_algorithm in "${ROUTING_ALGORITHMS[@]}"; do
    echo ""
    echo "========== [8x8] Routing: $routing_algorithm =========="

    for traffic_entry in "${TRAFFIC_PATTERNS[@]}"; do
        IFS=':' read -r traffic_param traffic_name <<< "$traffic_entry"
        traffic_results_dir="${MESH8_RESULTS_ROOT}/${routing_algorithm}/${traffic_name}"
        mkdir -p "$traffic_results_dir"

        echo "-----------------------------------------"
        echo "[8x8] Routing: $routing_algorithm, Traffic: $traffic_name (param=$traffic_param)"
        echo "Results dir: $traffic_results_dir"
        echo "-----------------------------------------"

        for pir in $pir_values; do
            pir_str=$(printf "%.2f" "$pir" | tr '.' '_')
            OUTPUT_FILE_PIR="${traffic_results_dir}/mesh_arbitration_PIR_${pir_str}.txt"

            {
                echo "========================================="
                echo "Mesh Arbitration Algorithms Comparison"
                echo "Topology: MESH (No HUB)"
                echo "Config: $(basename "$MESH8_CONFIG_FILE")"
                echo "Routing: $routing_algorithm"
                echo "Traffic pattern: $traffic_name (param=$traffic_param)"
                echo "PIR: $pir"
                echo "Mesh size: 8x8"
                echo "Date: $(date)"
                echo "========================================="
                echo ""
            } > "$OUTPUT_FILE_PIR"

            echo "[8x8]  $routing_algorithm / $traffic_name  PIR: $pir -> $OUTPUT_FILE_PIR"

            for strategy_entry in "${ARBITRATION_STRATEGIES[@]}"; do
                IFS=':' read -r strategy_name strategy_display <<< "$strategy_entry"

                echo "--- $strategy_display ($strategy_name) ---" | tee -a "$OUTPUT_FILE_PIR"

                declare -a received_packets_array received_flits_array avg_delay_array max_delay_array
                declare -a network_throughput_array ip_throughput_array total_energy_array
                declare -a dynamic_energy_array static_energy_array

                echo "Running $strategy_display with PIR=$pir on Mesh 8x8, routing=$routing_algorithm (10 successful runs)..." | tee -a "$OUTPUT_FILE_PIR"

                successful_runs=0
                total_attempts=0
                max_attempts=30

                while [ $successful_runs -lt 10 ] && [ $total_attempts -lt $max_attempts ]; do
                    total_attempts=$((total_attempts + 1))
                    echo "  Attempt $total_attempts (successful: $successful_runs/10)..." | tee -a "$OUTPUT_FILE_PIR"

                    cd "$BIN_DIR"
                    output=$("$NOXIM_BIN" -config "$MESH8_CONFIG_FILE" -routing "$routing_algorithm" -sel "$strategy_name" -pir "$pir" poisson -traffic "$traffic_param" 2>&1)

                    stats=$(parse_stats "$output")

                    received_packets=$(echo "$stats" | grep "received_packets=" | cut -d'=' -f2 | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
                    received_flits=$(echo "$stats" | grep "received_flits=" | cut -d'=' -f2 | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
                    avg_delay=$(echo "$stats" | grep "avg_delay=" | cut -d'=' -f2 | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
                    max_delay=$(echo "$stats" | grep "max_delay=" | cut -d'=' -f2 | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
                    network_throughput=$(echo "$stats" | grep "network_throughput=" | cut -d'=' -f2 | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
                    ip_throughput=$(echo "$stats" | grep "ip_throughput=" | cut -d'=' -f2 | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
                    total_energy=$(echo "$stats" | grep "total_energy=" | cut -d'=' -f2 | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
                    dynamic_energy=$(echo "$stats" | grep "dynamic_energy=" | cut -d'=' -f2 | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
                    static_energy=$(echo "$stats" | grep "static_energy=" | cut -d'=' -f2 | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')

                    [ -n "$total_energy" ] && total_energy=$(normalize_number "$total_energy")
                    [ -n "$dynamic_energy" ] && dynamic_energy=$(normalize_number "$dynamic_energy")
                    [ -n "$static_energy" ] && static_energy=$(normalize_number "$static_energy")

                    [ -z "$received_packets" ] && received_packets=0
                    [ -z "$received_flits" ] && received_flits=0
                    [ -z "$avg_delay" ] && avg_delay=0
                    [ -z "$max_delay" ] && max_delay=0
                    [ -z "$network_throughput" ] && network_throughput=0
                    [ -z "$ip_throughput" ] && ip_throughput=0
                    [ -z "$total_energy" ] && total_energy=0
                    [ -z "$dynamic_energy" ] && dynamic_energy=0
                    [ -z "$static_energy" ] && static_energy=0

                    received_packets_int=$(echo "$received_packets" | awk '{printf "%d", $1}')

                    if [ "$received_packets_int" -eq 0 ]; then
                        echo "    Warning: Received 0 packets, skipping this run and retrying..." | tee -a "$OUTPUT_FILE_PIR"
                        continue
                    fi

                    idx=$successful_runs
                    received_packets_array[$idx]=$received_packets
                    received_flits_array[$idx]=$received_flits
                    avg_delay_array[$idx]=$avg_delay
                    max_delay_array[$idx]=$max_delay
                    network_throughput_array[$idx]=$network_throughput
                    ip_throughput_array[$idx]=$ip_throughput
                    total_energy_array[$idx]=$total_energy
                    dynamic_energy_array[$idx]=$dynamic_energy
                    static_energy_array[$idx]=$static_energy

                    successful_runs=$((successful_runs + 1))
                done

                if [ $successful_runs -lt 10 ]; then
                    echo "    Warning: Only $successful_runs successful runs out of $total_attempts attempts!" | tee -a "$OUTPUT_FILE_PIR"
                else
                    echo "    Completed: $successful_runs successful runs in $total_attempts attempts" | tee -a "$OUTPUT_FILE_PIR"
                fi

                echo "" | tee -a "$OUTPUT_FILE_PIR"
                echo "AVERAGED RESULTS for $strategy_display ($strategy_name) (PIR=$pir, $successful_runs runs):" | tee -a "$OUTPUT_FILE_PIR"
                avg_val=$(calculate_average "${received_packets_array[@]}")
                echo "  Total received packets: $(format_number "$avg_val")" | tee -a "$OUTPUT_FILE_PIR"
                avg_val=$(calculate_average "${received_flits_array[@]}")
                echo "  Total received flits: $(format_number "$avg_val")" | tee -a "$OUTPUT_FILE_PIR"
                avg_val=$(calculate_average "${avg_delay_array[@]}")
                echo "  Global average delay (cycles): $(format_number "$avg_val")" | tee -a "$OUTPUT_FILE_PIR"
                avg_val=$(calculate_average "${max_delay_array[@]}")
                echo "  Max delay (cycles): $(format_number "$avg_val")" | tee -a "$OUTPUT_FILE_PIR"
                avg_val=$(calculate_average "${network_throughput_array[@]}")
                echo "  Network throughput (flits/cycle): $(format_number "$avg_val")" | tee -a "$OUTPUT_FILE_PIR"
                avg_val=$(calculate_average "${ip_throughput_array[@]}")
                echo "  Average IP throughput (flits/cycle/IP): $(format_number "$avg_val")" | tee -a "$OUTPUT_FILE_PIR"
                avg_val=$(calculate_average "${total_energy_array[@]}")
                echo "  Total energy (J): $(format_number "$avg_val")" | tee -a "$OUTPUT_FILE_PIR"
                avg_val=$(calculate_average "${dynamic_energy_array[@]}")
                echo "  Dynamic energy (J): $(format_number "$avg_val")" | tee -a "$OUTPUT_FILE_PIR"
                avg_val=$(calculate_average "${static_energy_array[@]}")
                echo "  Static energy (J): $(format_number "$avg_val")" | tee -a "$OUTPUT_FILE_PIR"
                echo "" | tee -a "$OUTPUT_FILE_PIR"
            done

            echo "[8x8]  Mesh results for PIR=$pir (routing=$routing_algorithm, traffic=$traffic_name) saved to: $OUTPUT_FILE_PIR"
            echo ""
        done

        echo "[8x8] Finished simulations for routing=$routing_algorithm, traffic: $traffic_name"
        echo ""
    done
done

echo "========================================="
echo "All Mesh 8x8 simulations completed!"
echo "Results saved in: $MESH8_RESULTS_ROOT"
echo "Directory structure: results/mesh8x8/<ROUTING>/TRAFFIC_*/mesh_arbitration_PIR_*.txt"
echo "========================================="

# =========================================
# MESH 16x16 RUNS (COMMENTED OUT)
# =========================================
: '
echo ""
echo "========================================="
echo "Starting Mesh 16x16 (default routing) arbitration comparison..."
echo "Mesh 16x16 config: $MESH16_CONFIG_FILE"
echo "Mesh 16x16 results root directory: $MESH16_RESULTS_ROOT"
echo "Traffic patterns: random, transpose1, bitreversal, shuffle, butterfly"
echo "========================================="

for traffic_entry in "${TRAFFIC_PATTERNS[@]}"; do
    IFS=':' read -r traffic_param traffic_name <<< "$traffic_entry"
    traffic_results_dir="${MESH16_RESULTS_ROOT}/${traffic_name}"
    mkdir -p "$traffic_results_dir"

    echo "-----------------------------------------"
    echo "[16x16] Traffic: $traffic_name (param=$traffic_param)"
    echo "Results dir: $traffic_results_dir"
    echo "-----------------------------------------"

    for pir in $pir_values; do
        pir_str=$(printf "%.2f" "$pir" | tr '.' '_')
        OUTPUT_FILE_PIR="${traffic_results_dir}/mesh_arbitration_PIR_${pir_str}.txt"

        {
            echo "========================================="
            echo "Mesh Arbitration Algorithms Comparison"
            echo "Topology: MESH (No HUB)"
            echo "Config: $(basename "$MESH16_CONFIG_FILE")"
            echo "Routing: default (from config)"
            echo "Traffic pattern: $traffic_name (param=$traffic_param)"
            echo "PIR: $pir"
            echo "Mesh size: 16x16"
            echo "Date: $(date)"
            echo "========================================="
            echo ""
        } > "$OUTPUT_FILE_PIR"

        echo "[16x16]  PIR: $pir -> $OUTPUT_FILE_PIR"

        for strategy_entry in "${ARBITRATION_STRATEGIES[@]}"; do
            IFS=':' read -r strategy_name strategy_display <<< "$strategy_entry"

            echo "--- $strategy_display ($strategy_name) ---" | tee -a "$OUTPUT_FILE_PIR"

            declare -a received_packets_array received_flits_array avg_delay_array max_delay_array
            declare -a network_throughput_array ip_throughput_array total_energy_array
            declare -a dynamic_energy_array static_energy_array

            echo "Running $strategy_display with PIR=$pir on Mesh 16x16 (6 successful runs)..." | tee -a "$OUTPUT_FILE_PIR"

            successful_runs=0
            total_attempts=0
            max_attempts=20

            while [ $successful_runs -lt 6 ] && [ $total_attempts -lt $max_attempts ]; do
                total_attempts=$((total_attempts + 1))
                echo "  Attempt $total_attempts (successful: $successful_runs/6)..." | tee -a "$OUTPUT_FILE_PIR"

                cd "$BIN_DIR"
                output=$("$NOXIM_BIN" -config "$MESH16_CONFIG_FILE" -sel "$strategy_name" -pir "$pir" poisson -traffic "$traffic_param" 2>&1)

                stats=$(parse_stats "$output")

                received_packets=$(echo "$stats" | grep "received_packets=" | cut -d'=' -f2 | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
                received_flits=$(echo "$stats" | grep "received_flits=" | cut -d'=' -f2 | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
                avg_delay=$(echo "$stats" | grep "avg_delay=" | cut -d'=' -f2 | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
                max_delay=$(echo "$stats" | grep "max_delay=" | cut -d'=' -f2 | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
                network_throughput=$(echo "$stats" | grep "network_throughput=" | cut -d'=' -f2 | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
                ip_throughput=$(echo "$stats" | grep "ip_throughput=" | cut -d'=' -f2 | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
                total_energy=$(echo "$stats" | grep "total_energy=" | cut -d'=' -f2 | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
                dynamic_energy=$(echo "$stats" | grep "dynamic_energy=" | cut -d'=' -f2 | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
                static_energy=$(echo "$stats" | grep "static_energy=" | cut -d'=' -f2 | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')

                [ -n "$total_energy" ] && total_energy=$(normalize_number "$total_energy")
                [ -n "$dynamic_energy" ] && dynamic_energy=$(normalize_number "$dynamic_energy")
                [ -n "$static_energy" ] && static_energy=$(normalize_number "$static_energy")

                [ -z "$received_packets" ] && received_packets=0
                [ -z "$received_flits" ] && received_flits=0
                [ -z "$avg_delay" ] && avg_delay=0
                [ -z "$max_delay" ] && max_delay=0
                [ -z "$network_throughput" ] && network_throughput=0
                [ -z "$ip_throughput" ] && ip_throughput=0
                [ -z "$total_energy" ] && total_energy=0
                [ -z "$dynamic_energy" ] && dynamic_energy=0
                [ -z "$static_energy" ] && static_energy=0

                received_packets_int=$(echo "$received_packets" | awk '{printf "%d", $1}')

                if [ "$received_packets_int" -eq 0 ]; then
                    echo "    Warning: Received 0 packets, skipping this run and retrying..." | tee -a "$OUTPUT_FILE_PIR"
                    continue
                fi

                idx=$successful_runs
                received_packets_array[$idx]=$received_packets
                received_flits_array[$idx]=$received_flits
                avg_delay_array[$idx]=$avg_delay
                max_delay_array[$idx]=$max_delay
                network_throughput_array[$idx]=$network_throughput
                ip_throughput_array[$idx]=$ip_throughput
                total_energy_array[$idx]=$total_energy
                dynamic_energy_array[$idx]=$dynamic_energy
                static_energy_array[$idx]=$static_energy

                successful_runs=$((successful_runs + 1))
            done

            if [ $successful_runs -lt 6 ]; then
                echo "    Warning: Only $successful_runs successful runs out of $total_attempts attempts!" | tee -a "$OUTPUT_FILE_PIR"
            else
                echo "    Completed: $successful_runs successful runs in $total_attempts attempts" | tee -a "$OUTPUT_FILE_PIR"
            fi

            echo "" | tee -a "$OUTPUT_FILE_PIR"
            echo "AVERAGED RESULTS for $strategy_display ($strategy_name) (PIR=$pir, $successful_runs runs):" | tee -a "$OUTPUT_FILE_PIR"
            avg_val=$(calculate_average "${received_packets_array[@]}")
            echo "  Total received packets: $(format_number "$avg_val")" | tee -a "$OUTPUT_FILE_PIR"
            avg_val=$(calculate_average "${received_flits_array[@]}")
            echo "  Total received flits: $(format_number "$avg_val")" | tee -a "$OUTPUT_FILE_PIR"
            avg_val=$(calculate_average "${avg_delay_array[@]}")
            echo "  Global average delay (cycles): $(format_number "$avg_val")" | tee -a "$OUTPUT_FILE_PIR"
            avg_val=$(calculate_average "${max_delay_array[@]}")
            echo "  Max delay (cycles): $(format_number "$avg_val")" | tee -a "$OUTPUT_FILE_PIR"
            avg_val=$(calculate_average "${network_throughput_array[@]}")
            echo "  Network throughput (flits/cycle): $(format_number "$avg_val")" | tee -a "$OUTPUT_FILE_PIR"
            avg_val=$(calculate_average "${ip_throughput_array[@]}")
            echo "  Average IP throughput (flits/cycle/IP): $(format_number "$avg_val")" | tee -a "$OUTPUT_FILE_PIR"
            avg_val=$(calculate_average "${total_energy_array[@]}")
            echo "  Total energy (J): $(format_number "$avg_val")" | tee -a "$OUTPUT_FILE_PIR"
            avg_val=$(calculate_average "${dynamic_energy_array[@]}")
            echo "  Dynamic energy (J): $(format_number "$avg_val")" | tee -a "$OUTPUT_FILE_PIR"
            avg_val=$(calculate_average "${static_energy_array[@]}")
            echo "  Static energy (J): $(format_number "$avg_val")" | tee -a "$OUTPUT_FILE_PIR"
            echo "" | tee -a "$OUTPUT_FILE_PIR"
        done

        echo "[16x16]  Mesh results for PIR=$pir (traffic=$traffic_name) saved to: $OUTPUT_FILE_PIR"
        echo ""
    done

    echo "[16x16] Finished simulations for traffic: $traffic_name"
    echo ""
done

echo "========================================="
echo "All Mesh 16x16 simulations completed!"
echo "Results saved in: $MESH16_RESULTS_ROOT"
echo "Directory structure: results/mesh16x16/TRAFFIC_*/mesh_arbitration_PIR_*.txt"
echo "========================================="
'
