#ifndef __NOXIMROUTING_LCIRC_H__
#define __NOXIMROUTING_LCIRC_H__

#include "RoutingAlgorithm.h"
#include "RoutingAlgorithms.h"
#include "../Router.h"
#include "../GlobalParams.h"

// Routing algorithm for LCirculant topologies.
// At each hop it recomputes the best direction using the same
// integer formulas as in lcirculant_params.py (no extra state in flits).

class Routing_LCIRC : RoutingAlgorithm {
public:
    std::vector<int> route(Router *router, const RouteData &routeData) override;

    static Routing_LCIRC *getInstance();

private:
    Routing_LCIRC() {}
    ~Routing_LCIRC() {}

    static Routing_LCIRC *routing_LCIRC;
    static RoutingAlgorithmsRegister routingAlgorithmsRegister;
};

#endif

