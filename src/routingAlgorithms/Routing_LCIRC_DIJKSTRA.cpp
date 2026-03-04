#include "Routing_LCIRC_DIJKSTRA.h"
#include <climits>
#include <vector>
#include <queue>
#include <algorithm>

RoutingAlgorithmsRegister Routing_LCIRC_DIJKSTRA::routingAlgorithmsRegister("LCIRC_DIJKSTRA", getInstance());

Routing_LCIRC_DIJKSTRA *Routing_LCIRC_DIJKSTRA::routing_LCIRC_DIJKSTRA = 0;

Routing_LCIRC_DIJKSTRA *Routing_LCIRC_DIJKSTRA::getInstance() {
    if (routing_LCIRC_DIJKSTRA == 0)
        routing_LCIRC_DIJKSTRA = new Routing_LCIRC_DIJKSTRA();
    return routing_LCIRC_DIJKSTRA;
}

std::vector<int> Routing_LCIRC_DIJKSTRA::route(Router *router, const RouteData &routeData)
{
    std::vector<int> dirs;

    const int N  = GlobalParams::lcirc_N;
    const int u  = routeData.current_id;
    const int w  = routeData.dst_id;
    const int s1 = GlobalParams::lcirc_s1;
    const int s2 = GlobalParams::lcirc_s2;

    // Safety checks
    if (N <= 0 || s1 <= 0 || s2 <= 0) {
        dirs.push_back(DIRECTION_LOCAL);
        return dirs;
    }

    if (u == w) {
        dirs.push_back(DIRECTION_LOCAL);
        return dirs;
    }

    // Ensure u and w are in valid range
    if (u < 0 || u >= N || w < 0 || w >= N) {
        dirs.push_back(DIRECTION_LOCAL);
        return dirs;
    }

    // Dijkstra's algorithm: find shortest path from u to w
    std::vector<int> dist(N, INT_MAX);
    std::vector<int> prev(N, -1);
    std::vector<int> dir_from_prev(N, DIRECTION_LOCAL);
    std::vector<bool> visited(N, false);

    dist[u] = 0;
    std::priority_queue<std::pair<int, int>, std::vector<std::pair<int, int>>, std::greater<std::pair<int, int>>> pq;
    pq.push({0, u});

    while (!pq.empty()) {
        int current = pq.top().second;
        pq.pop();

        if (visited[current])
            continue;
        visited[current] = true;

        if (current == w)
            break;

        // Check all 4 neighbors: ±s1, ±s2
        // Ensure current is in valid range before accessing arrays
        if (current < 0 || current >= N)
            break;

        int neighbors[4] = {
            (current + s1 + N) % N,      // +s1
            (current - s1 + N) % N,      // -s1
            (current + s2 + N) % N,      // +s2
            (current - s2 + N) % N       // -s2
        };
        int ndir[4] = {
            DIRECTION_SOUTH,       // S1+
            DIRECTION_NORTH,       // S1-
            DIRECTION_EAST,        // S2+
            DIRECTION_WEST         // S2-
        };

        for (int k = 0; k < 4; ++k) {
            int neighbor = neighbors[k];
            // Ensure neighbor is in valid range
            if (neighbor < 0 || neighbor >= N)
                continue;
            
            int edge_weight = 1; // All edges have weight 1
            int new_dist = dist[current] + edge_weight;

            if (!visited[neighbor] && dist[current] != INT_MAX) {
                // Check if we found a shorter path
                if (new_dist < dist[neighbor]) {
                    dist[neighbor] = new_dist;
                    prev[neighbor] = current;
                    dir_from_prev[neighbor] = ndir[k];
                    pq.push({dist[neighbor], neighbor});
                }
                // If paths have equal length, prefer s1 directions (NORTH/SOUTH) over s2 (EAST/WEST)
                else if (new_dist == dist[neighbor] && dist[neighbor] != INT_MAX) {
                    // Check if current direction is s1 (NORTH or SOUTH) and previous was s2 (EAST or WEST)
                    bool current_is_s1 = (ndir[k] == DIRECTION_NORTH || ndir[k] == DIRECTION_SOUTH);
                    bool prev_is_s2 = (dir_from_prev[neighbor] == DIRECTION_EAST || dir_from_prev[neighbor] == DIRECTION_WEST);
                    
                    if (current_is_s1 && prev_is_s2) {
                        // Prefer s1 direction over s2
                        prev[neighbor] = current;
                        dir_from_prev[neighbor] = ndir[k];
                    }
                }
            }
        }
    }

    // Check if destination is reachable
    if (dist[w] == INT_MAX) {
        // Path not found (shouldn't happen in connected circulant)
        dirs.push_back(DIRECTION_SOUTH);
        return dirs;
    }

    // Reconstruct path to get first step direction
    // Check all neighbors of u to find which one is on the shortest path to w
    // Prefer s1 directions (NORTH/SOUTH) over s2 (EAST/WEST) when multiple paths exist
    int neighbors[4] = {
        (u + s1 + N) % N,      // +s1 (SOUTH)
        (u - s1 + N) % N,      // -s1 (NORTH)
        (u + s2 + N) % N,      // +s2 (EAST)
        (u - s2 + N) % N       // -s2 (WEST)
    };
    int ndir[4] = {
        DIRECTION_SOUTH,       // S1+
        DIRECTION_NORTH,       // S1-
        DIRECTION_EAST,        // S2+
        DIRECTION_WEST         // S2-
    };
    
    int best_dir = DIRECTION_SOUTH;  // Default fallback
    bool found_s1 = false;
    
    // First, check s1 directions (preferred)
    for (int k = 0; k < 2; ++k) {
        int neighbor = neighbors[k];
        if (neighbor >= 0 && neighbor < N && dist[neighbor] != INT_MAX) {
            // Check if this neighbor is on shortest path: dist[neighbor] + shortest_path_from_neighbor_to_w == dist[w]
            // We can verify by checking if we can reach w from neighbor with dist[w] - dist[neighbor] steps
            if (dist[neighbor] == 1) {
                // Verify neighbor is on path by walking back from w
                int temp = w;
                int steps = 0;
                while (temp != -1 && temp != u && steps < N) {
                    if (temp == neighbor) {
                        best_dir = ndir[k];
                        found_s1 = true;
                        break;
                    }
                    temp = prev[temp];
                    steps++;
                }
                if (found_s1) break;
            }
        }
    }
    
    // If no s1 path found, check s2 directions or use standard reconstruction
    if (!found_s1) {
        // Try standard path reconstruction first
        int cur = w;
        while (cur != u && cur != -1) {
            if (prev[cur] == u) {
                best_dir = dir_from_prev[cur];
                break;
            }
            cur = prev[cur];
        }
        
        // If still not found, check s2 directions
        if (best_dir == DIRECTION_SOUTH) {
            for (int k = 2; k < 4; ++k) {
                int neighbor = neighbors[k];
                if (neighbor >= 0 && neighbor < N && dist[neighbor] != INT_MAX && dist[neighbor] == 1) {
                    int temp = w;
                    int steps = 0;
                    while (temp != -1 && temp != u && steps < N) {
                        if (temp == neighbor) {
                            best_dir = ndir[k];
                            break;
                        }
                        temp = prev[temp];
                        steps++;
                    }
                    if (best_dir != DIRECTION_SOUTH) break;
                }
            }
        }
    }

    dirs.push_back(best_dir);

    return dirs;
}
