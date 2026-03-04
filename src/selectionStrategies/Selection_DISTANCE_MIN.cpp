#include "Selection_DISTANCE_MIN.h"
#include "../GlobalParams.h"
#include <cmath>
#include <climits>
#include <vector>

SelectionStrategiesRegister Selection_DISTANCE_MIN::selectionStrategiesRegister("DISTANCE_MIN", getInstance());

Selection_DISTANCE_MIN * Selection_DISTANCE_MIN::selection_DISTANCE_MIN = 0;

Selection_DISTANCE_MIN * Selection_DISTANCE_MIN::getInstance() {
	if ( selection_DISTANCE_MIN == 0 )
		selection_DISTANCE_MIN = new Selection_DISTANCE_MIN();
    
	return selection_DISTANCE_MIN;
}

int Selection_DISTANCE_MIN::apply(Router * router, const vector < int >&directions, const RouteData & route_data){
    assert(directions.size()!=0);
    // For direction selection, use random (same as RANDOM)
    return directions[rand() % directions.size()];
}

void Selection_DISTANCE_MIN::perCycleUpdate(Router * router){ }

int Selection_DISTANCE_MIN::calculateRemainingDistance(int current_id, int dst_id) {
    if (current_id == dst_id)
        return 0;
    
    // For LCirculant topology, calculate distance using the routing algorithm logic
    if (GlobalParams::topology == TOPOLOGY_LCIRCULANT) {
        const int N = GlobalParams::lcirc_N;
        const int a = GlobalParams::lcirc_a;
        const int b = GlobalParams::lcirc_b;
        const int d = GlobalParams::lcirc_d;
        
        // Reduce to path from 0 to v, where v = (dst - current) mod N
        int v = dst_id - current_id;
        v %= N;
        if (v < 0) v += N;
        
        if (v == 0) return 0;
        
        // Calculate coefficients using LCIRC algorithm
        int xv = v % a;
        if (xv < 0) xv += a;
        
        int q = v / a;
        if (v < 0 && (v % a != 0)) q--;
        
        int ceil_b2 = (b + 1) / 2;
        int yv = ceil_b2 * q - b * (q / 2);
        
        int p1, p2;
        if ((yv < ceil_b2) && ((xv + yv) <= d)) {
            p1 = xv;
            p2 = yv;
        } else if ((yv >= ceil_b2) && ((yv - xv) >= (b - d))) {
            p1 = xv;
            p2 = yv - b;
        } else {
            p1 = xv - a;
            p2 = yv - ceil_b2;
        }
        
        // Distance is Manhattan distance in LCirc coefficient space: |p1| + |p2|
        return std::abs(p1) + std::abs(p2);
    }
    
    // For MESH topology, use Manhattan distance in (X,Y) coordinates:
    // |Xdst - Xsrc| + |Ydst - Ysrc|
    if (GlobalParams::topology == TOPOLOGY_MESH) {
        static bool mesh_cache_initialized = false;
        static int cached_mesh_dim_x = 0;
        static int cached_mesh_dim_y = 0;
        static std::vector<std::vector<int> > mesh_dist;

        int dim_x = GlobalParams::mesh_dim_x;
        int dim_y = GlobalParams::mesh_dim_y;
        int N = dim_x * dim_y;

        if (!mesh_cache_initialized || cached_mesh_dim_x != dim_x || cached_mesh_dim_y != dim_y) {
            cached_mesh_dim_x = dim_x;
            cached_mesh_dim_y = dim_y;
            mesh_dist.assign(N, std::vector<int>(N, 0));

            for (int src = 0; src < N; ++src) {
                int xs = src % dim_x;
                int ys = src / dim_x;
                for (int dst = 0; dst < N; ++dst) {
                    int xd = dst % dim_x;
                    int yd = dst / dim_x;
                    mesh_dist[src][dst] = std::abs(xd - xs) + std::abs(yd - ys);
                }
            }
            mesh_cache_initialized = true;
        }

        if (current_id >= 0 && current_id < N && dst_id >= 0 && dst_id < N) {
            return mesh_dist[current_id][dst_id];
        }
    }
    
    // For other topologies, fallback to simple absolute id difference
    return std::abs(dst_id - current_id);
}

int Selection_DISTANCE_MIN::arbitrate(Router * router, const vector<pair<int,int> >& reservations) {
    assert(reservations.size() != 0);
    
    int min_distance = INT_MAX;
    vector<int> best_indices;
    
    // Find flits with minimum remaining distance
    for (size_t i = 0; i < reservations.size(); i++) {
        int input_port = reservations[i].first;
        int vc = reservations[i].second;
        
        if (!router->buffer[input_port][vc].IsEmpty()) {
            Flit flit = router->buffer[input_port][vc].Front();
            int distance = calculateRemainingDistance(router->local_id, flit.dst_id);
            
            if (distance < min_distance) {
                min_distance = distance;
                best_indices.clear();
                best_indices.push_back(i);
            } else if (distance == min_distance) {
                best_indices.push_back(i);
            }
        }
    }
    
    // If no valid flits found, return random
    if (best_indices.size() == 0) {
        return rand() % reservations.size();
    }
    
    // Return random among best (minimum distance)
    return best_indices[rand() % best_indices.size()];
}
