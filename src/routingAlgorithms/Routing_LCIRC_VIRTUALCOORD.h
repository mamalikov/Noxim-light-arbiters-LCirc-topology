#ifndef __NOXIMROUTING_LCIRC_VIRTUALCOORD_H__
#define __NOXIMROUTING_LCIRC_VIRTUALCOORD_H__

#include "RoutingAlgorithm.h"
#include "RoutingAlgorithms.h"
#include "../Router.h"
#include "../GlobalParams.h"
#include <vector>
#include <utility>

// Routing algorithm for LCirculant topologies using virtual coordinates.
// Calculates route based on virtual coordinate system: finds coordinates of nodes u and w,
// computes difference vector (Xw-Xu, Yw-Yu), and if distance > d, adds zero vectors to reduce it.

class Routing_LCIRC_VIRTUALCOORD : RoutingAlgorithm {
public:
    std::vector<int> route(Router *router, const RouteData &routeData) override;

    static Routing_LCIRC_VIRTUALCOORD *getInstance();

private:
    Routing_LCIRC_VIRTUALCOORD() {}
    ~Routing_LCIRC_VIRTUALCOORD() {}

    // Инициализирует систему координат и нулевые векторы
    static void initializeCoordinates();
    
    // Проверяет и инициализирует при необходимости
    static void ensureInitialized();
    
    // Вычисляет маршрут от узла u к узлу w используя предвычисленные виртуальные координаты
    static std::pair<int, int> calculate_route_virtual_coord(int u, int w, int d);

    static Routing_LCIRC_VIRTUALCOORD *routing_LCIRC_VIRTUALCOORD;
    static RoutingAlgorithmsRegister routingAlgorithmsRegister;
    
    // Предвычисленные данные
    static bool initialized;
    static std::vector<std::pair<int, int> > node_coordinates;  // Координаты узлов [node_id] -> (x, y)
    static std::vector<std::pair<int, int> > canonical_zeros;    // Канонические координаты нулей
};

#endif
