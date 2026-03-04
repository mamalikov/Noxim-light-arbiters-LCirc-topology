#!/bin/bash

# Script to run Noxim with 3 LCirculant routing algorithms
# For each PIR (0.01 to 0.1, step 0.01), runs 6 simulations per algorithm
# and saves averaged results to separate files
# Usage: ./run_lcirc_comparison.sh

# Get the directory where the script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BIN_DIR="${SCRIPT_DIR}/bin"
CONFIG_DIR="${SCRIPT_DIR}/config_examples"
NOXIM_BIN="${BIN_DIR}/noxim"
RESULTS_DIR="${SCRIPT_DIR}/results"

# Check if noxim binary exists
if [ ! -f "$NOXIM_BIN" ]; then
    echo "Error: noxim binary not found at $NOXIM_BIN"
    echo "Please compile noxim first: cd bin && make"
    exit 1
fi

# Create results directory if it doesn't exist
mkdir -p "$RESULTS_DIR"

# Traffic patterns to test
# Format: "traffic_param_value:display_name"
TRAFFIC_PATTERNS=(
    "random:TRAFFIC_RANDOM"
    "bitreversal:TRAFFIC_BIT_REVERSAL"
    "shuffle:TRAFFIC_SHUFFLE"
    "butterfly:TRAFFIC_BUTTERFLY"
)

# Configurations to test
# Format: "config_file:algorithm_name:file_suffix"
CONFIGS=(
    "default_configLCirc_Simple.yaml:LCIRC_SIMPLE:simple"
    "default_configLCirc.yaml:LCIRC:new_alg"
    "default_configLCirc_Dijkstra.yaml:LCIRC_DIJKSTRA:dijkstra"
    "default_configLCirc_VirtualCoord.yaml:LCIRC_VIRTUALCOORD:virtualcoord"
)

# Function to parse statistics from noxim output
parse_stats() {
    local output="$1"
    
    # Extract statistics using grep and awk
    # Handle lines with and without tabs
    received_packets=$(echo "$output" | grep "^% Total received packets:" | awk '{print $NF}')
    received_flits=$(echo "$output" | grep "^% Total received flits:" | awk '{print $NF}')
    avg_delay=$(echo "$output" | grep "^% Global average delay" | awk '{print $NF}')
    max_delay=$(echo "$output" | grep "^% Max delay" | awk '{print $NF}')
    network_throughput=$(echo "$output" | grep "^% Network throughput" | awk '{print $NF}')
    ip_throughput=$(echo "$output" | grep "^% Average IP throughput" | awk '{print $NF}')
    # Energy values may have tabs, use more flexible matching
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

# Iterate over traffic patterns
for traffic_entry in "${TRAFFIC_PATTERNS[@]}"; do
    IFS=':' read -r traffic_param traffic_name <<< "$traffic_entry"
    traffic_results_dir="${RESULTS_DIR}/${traffic_name}"
    mkdir -p "$traffic_results_dir"
    
    echo "========================================="
    echo "Running simulations for: $traffic_name"
    echo "Results will be saved to: $traffic_results_dir"
    echo "========================================="
    echo ""
    
    # Iterate over PIR values from 0.01 to 0.1 with step 0.01
    # Using awk to generate floating point sequence
    pir_values=$(awk 'BEGIN {for(i=1; i<=10; i++) printf "%.2f ", i*0.01}')

    for pir in $pir_values; do
        # Format PIR for filename (replace . with _)
        pir_str=$(printf "%.2f" "$pir" | tr '.' '_')
        
        # Process each configuration separately and save to files with algorithm-specific suffix
        for config_entry in "${CONFIGS[@]}"; do
            IFS=':' read -r config_file config_name file_suffix <<< "$config_entry"
            config_path="${CONFIG_DIR}/${config_file}"
            
            if [ ! -f "$config_path" ]; then
                echo "Warning: Config file not found: $config_path"
                continue
            fi
            
            # Create output file with algorithm-specific suffix
            output_file="${traffic_results_dir}/lcirc_results_PIR_${pir_str}_${file_suffix}.txt"
            
            echo "=========================================" | tee "$output_file"
            echo "LCirculant Routing Algorithm: $config_name" | tee -a "$output_file"
            echo "Traffic Pattern: $traffic_name" | tee -a "$output_file"
            echo "PIR: $pir" | tee -a "$output_file"
            echo "Date: $(date)" | tee -a "$output_file"
            echo "=========================================" | tee -a "$output_file"
            echo "" | tee -a "$output_file"
            
            # Arrays to store statistics for averaging (using indexed arrays for compatibility)
            declare -a received_packets_array received_flits_array avg_delay_array max_delay_array
            declare -a network_throughput_array ip_throughput_array total_energy_array
            declare -a dynamic_energy_array static_energy_array
            
            echo "Running $config_name with PIR=$pir (6 successful runs)..." | tee -a "$output_file"
            
            # Run simulations until we have 6 successful ones (with received_packets > 0)
            successful_runs=0
            total_attempts=0
            max_attempts=30  # Safety limit to prevent infinite loops
            
            while [ $successful_runs -lt 6 ] && [ $total_attempts -lt $max_attempts ]; do
                total_attempts=$((total_attempts + 1))
                echo "  Attempt $total_attempts (successful: $successful_runs/6)..." | tee -a "$output_file"
                
                cd "$BIN_DIR"
                output=$("$NOXIM_BIN" -config "$config_path" -pir "$pir" poisson -traffic "$traffic_param" 2>&1)
                
                # Parse statistics
                stats=$(parse_stats "$output")
                
                # Extract values and store in appropriate array
                # Handle empty values by setting to 0, normalize numbers
                received_packets=$(echo "$stats" | grep "received_packets=" | cut -d'=' -f2 | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
                received_flits=$(echo "$stats" | grep "received_flits=" | cut -d'=' -f2 | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
                avg_delay=$(echo "$stats" | grep "avg_delay=" | cut -d'=' -f2 | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
                max_delay=$(echo "$stats" | grep "max_delay=" | cut -d'=' -f2 | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
                network_throughput=$(echo "$stats" | grep "network_throughput=" | cut -d'=' -f2 | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
                ip_throughput=$(echo "$stats" | grep "ip_throughput=" | cut -d'=' -f2 | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
                total_energy=$(echo "$stats" | grep "total_energy=" | cut -d'=' -f2 | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
                dynamic_energy=$(echo "$stats" | grep "dynamic_energy=" | cut -d'=' -f2 | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
                static_energy=$(echo "$stats" | grep "static_energy=" | cut -d'=' -f2 | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
                
                # Normalize scientific notation to decimal for energy values
                [ -n "$total_energy" ] && total_energy=$(normalize_number "$total_energy")
                [ -n "$dynamic_energy" ] && dynamic_energy=$(normalize_number "$dynamic_energy")
                [ -n "$static_energy" ] && static_energy=$(normalize_number "$static_energy")
                
                # Set default values if empty
                [ -z "$received_packets" ] && received_packets=0
                [ -z "$received_flits" ] && received_flits=0
                [ -z "$avg_delay" ] && avg_delay=0
                [ -z "$max_delay" ] && max_delay=0
                [ -z "$network_throughput" ] && network_throughput=0
                [ -z "$ip_throughput" ] && ip_throughput=0
                [ -z "$total_energy" ] && total_energy=0
                [ -z "$dynamic_energy" ] && dynamic_energy=0
                [ -z "$static_energy" ] && static_energy=0
                
                # Check if received_packets is 0 (failed run)
                # Convert to integer for comparison (handle floating point)
                received_packets_int=$(echo "$received_packets" | awk '{printf "%d", $1}')
                received_flits_int=$(echo "$received_flits" | awk '{printf "%d", $1}')
                
                # For simple algorithm, only check packets > 0
                # For other algorithms, check both packets > 0 AND flits >= 40000
                if [ "$received_packets_int" -eq 0 ]; then
                    echo "    Warning: Received 0 packets, skipping this run and retrying..." | tee -a "$output_file"
                    continue
                fi
                
                # For non-simple algorithms, also check flits >= 40000
                if [ "$file_suffix" != "simple" ]; then
                    if [ "$received_flits_int" -lt 40000 ]; then
                        echo "    Warning: Received only $received_flits flits (< 40000), skipping this run and retrying..." | tee -a "$output_file"
                        continue
                    fi
                fi
                
                # Valid run - store in arrays
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
                
                # Increment successful runs counter
                successful_runs=$((successful_runs + 1))
            done
            
            # Check if we got enough successful runs
            if [ $successful_runs -lt 6 ]; then
                echo "    Warning: Only $successful_runs successful runs out of $total_attempts attempts!" | tee -a "$output_file"
            else
                echo "    Completed: $successful_runs successful runs in $total_attempts attempts" | tee -a "$output_file"
            fi
            
            # Calculate and write averages
            echo "" | tee -a "$output_file"
            echo "=========================================" | tee -a "$output_file"
            echo "AVERAGED RESULTS (6 runs)" | tee -a "$output_file"
            echo "=========================================" | tee -a "$output_file"
            echo "" | tee -a "$output_file"
            
            echo "--- $config_name Algorithm ---" | tee -a "$output_file"
            avg_val=$(calculate_average "${received_packets_array[@]}")
            echo "Total received packets: $(format_number "$avg_val")" | tee -a "$output_file"
            avg_val=$(calculate_average "${received_flits_array[@]}")
            echo "Total received flits: $(format_number "$avg_val")" | tee -a "$output_file"
            avg_val=$(calculate_average "${avg_delay_array[@]}")
            echo "Global average delay (cycles): $(format_number "$avg_val")" | tee -a "$output_file"
            avg_val=$(calculate_average "${max_delay_array[@]}")
            echo "Max delay (cycles): $(format_number "$avg_val")" | tee -a "$output_file"
            avg_val=$(calculate_average "${network_throughput_array[@]}")
            echo "Network throughput (flits/cycle): $(format_number "$avg_val")" | tee -a "$output_file"
            avg_val=$(calculate_average "${ip_throughput_array[@]}")
            echo "Average IP throughput (flits/cycle/IP): $(format_number "$avg_val")" | tee -a "$output_file"
            avg_val=$(calculate_average "${total_energy_array[@]}")
            echo "Total energy (J): $(format_number "$avg_val")" | tee -a "$output_file"
            avg_val=$(calculate_average "${dynamic_energy_array[@]}")
            echo "Dynamic energy (J): $(format_number "$avg_val")" | tee -a "$output_file"
            avg_val=$(calculate_average "${static_energy_array[@]}")
            echo "Static energy (J): $(format_number "$avg_val")" | tee -a "$output_file"
            echo "" | tee -a "$output_file"
            
            echo "Results saved to: $output_file" | tee -a "$output_file"
            echo "" | tee -a "$output_file"
        done  # End of config loop
    done  # End of PIR loop
    
    echo "========================================="
    echo "Completed simulations for: $traffic_name"
    echo "Results saved in: $traffic_results_dir"
    echo "========================================="
    echo ""
done  # End of traffic pattern loop

echo "========================================="
echo "All simulations completed!"
echo "Results saved in: $RESULTS_DIR"
echo "Traffic patterns tested:"
for traffic_entry in "${TRAFFIC_PATTERNS[@]}"; do
    IFS=':' read -r traffic_param traffic_name <<< "$traffic_entry"
    echo "  - $traffic_name: ${RESULTS_DIR}/${traffic_name}/"
done
echo "========================================="
