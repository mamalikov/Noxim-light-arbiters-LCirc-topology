#ifndef __NOXIMROUTING_LCIRC_DIJKSTRA_H__
#define __NOXIMROUTING_LCIRC_DIJKSTRA_H__

#include "RoutingAlgorithm.h"
#include "RoutingAlgorithms.h"
#include "../Router.h"
#include "../GlobalParams.h"

// Routing algorithm for LCirculant topologies using Dijkstra's algorithm.
// At each hop, finds the shortest path from current node to destination,
// then sends packets first along s1 steps, then along s2 steps.

class Routing_LCIRC_DIJKSTRA : RoutingAlgorithm {
public:
    std::vector<int> route(Router *router, const RouteData &routeData) override;

    static Routing_LCIRC_DIJKSTRA *getInstance();

private:
    Routing_LCIRC_DIJKSTRA() {}
    ~Routing_LCIRC_DIJKSTRA() {}

    static Routing_LCIRC_DIJKSTRA *routing_LCIRC_DIJKSTRA;
    static RoutingAlgorithmsRegister routingAlgorithmsRegister;
};

#endif
