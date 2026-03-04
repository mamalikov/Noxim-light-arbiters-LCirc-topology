#include "Routing_LCIRC_SIMPLE.h"
#include <cmath>

RoutingAlgorithmsRegister Routing_LCIRC_SIMPLE::routingAlgorithmsRegister("LCIRC_SIMPLE", getInstance());

Routing_LCIRC_SIMPLE *Routing_LCIRC_SIMPLE::routing_LCIRC_SIMPLE = 0;

Routing_LCIRC_SIMPLE *Routing_LCIRC_SIMPLE::getInstance() {
    if (routing_LCIRC_SIMPLE == 0)
        routing_LCIRC_SIMPLE = new Routing_LCIRC_SIMPLE();
    return routing_LCIRC_SIMPLE;
}

std::vector<int> Routing_LCIRC_SIMPLE::route(Router *router, const RouteData &routeData)
{
    std::vector<int> dirs;

    const int N  = GlobalParams::lcirc_N;
    int start = routeData.current_id;  // current vertex
    int end   = routeData.dst_id;      // destination vertex
    const int s1 = GlobalParams::lcirc_s1;
    const int s2 = GlobalParams::lcirc_s2;

    // Safety checks
    if (N <= 0 || s1 <= 0 || s2 <= 0) {
        dirs.push_back(DIRECTION_LOCAL);
        return dirs;
    }

    // Ensure start and end are in valid range
    if (start < 0 || start >= N || end < 0 || end >= N) {
        dirs.push_back(DIRECTION_LOCAL);
        return dirs;
    }

    // Algorithm implementation according to exact specification
    int S = end - start;
    
    // if s=0 then return start (already at destination)
    if (S == 0) {
        dirs.push_back(DIRECTION_LOCAL);
        return dirs;
    }
    
    // if S<0 then S = S+N
    if (S < 0) {
        S = S + N;
    }
    
    int first_dir = DIRECTION_LOCAL;
    
    if (S <= N / 2) {
        // Forward direction (clockwise)
        if (S >= s2) {
            // start = (s2+start) mod N → move forward by s2
            first_dir = DIRECTION_EAST;  // +s2
        } else {
            // start = (s1 + start) mod N → move forward by s1
            first_dir = DIRECTION_SOUTH;  // +s1
        }
    } else {
        // Backward direction (counterclockwise)
        S = N - S;  // Reverse distance
        if (S >= s2) {
            // start = (N-s2+start) mod N → move backward by s2
            // (N-s2+start) mod N = (start - s2 + N) mod N
            first_dir = DIRECTION_WEST;  // -s2
        } else {
            // start = (N-s1+start) mod N → move backward by s1
            // (N-s1+start) mod N = (start - s1 + N) mod N
            first_dir = DIRECTION_NORTH;  // -s1
        }
    }
    
    // if start = 0 then start = N
    // Note: This is handled by mod operation, but we need to check the result
    // In our case, new_start is already in range [0, N-1] due to mod operation
    // The original algorithm's "if start = 0 then start = N" seems to be for
    // 1-based indexing, but we use 0-based, so this step is not needed.
    // However, we keep the logic for consistency with the specification.
    
    // Safety check: ensure we have a valid direction
    if (first_dir == DIRECTION_LOCAL && start != end) {
        // Fallback: use s1 in forward direction
        first_dir = DIRECTION_SOUTH;
    }

    dirs.push_back(first_dir);
    return dirs;
}
