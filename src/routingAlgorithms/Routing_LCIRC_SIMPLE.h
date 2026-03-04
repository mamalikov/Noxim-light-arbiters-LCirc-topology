#ifndef __NOXIMROUTING_LCIRC_SIMPLE_H__
#define __NOXIMROUTING_LCIRC_SIMPLE_H__

#include "RoutingAlgorithm.h"
#include "RoutingAlgorithms.h"
#include "../Router.h"
#include "../GlobalParams.h"

// Simple greedy routing algorithm for LCirculant topologies.
// Algorithm:
//   S = end - start
//   if S=0 then return start (DIRECTION_LOCAL)
//   if S<0 then S = S+N
//   if S <= N/2 then
//     if S >= s2 then start = (s2+start) mod N (DIRECTION_EAST)
//     else start = (s1+start) mod N (DIRECTION_SOUTH)
//   else
//     S = N-S
//     if S >= s2 then start = (N-s2+start) mod N (DIRECTION_WEST)
//     else start = (N-s1+start) mod N (DIRECTION_NORTH)

class Routing_LCIRC_SIMPLE : RoutingAlgorithm {
public:
    std::vector<int> route(Router *router, const RouteData &routeData) override;

    static Routing_LCIRC_SIMPLE *getInstance();

private:
    Routing_LCIRC_SIMPLE() {}
    ~Routing_LCIRC_SIMPLE() {}

    static Routing_LCIRC_SIMPLE *routing_LCIRC_SIMPLE;
    static RoutingAlgorithmsRegister routingAlgorithmsRegister;
};

#endif
