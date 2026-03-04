#include "Routing_LCIRC.h"
#include <cmath>

RoutingAlgorithmsRegister Routing_LCIRC::routingAlgorithmsRegister("LCIRC", getInstance());

Routing_LCIRC *Routing_LCIRC::routing_LCIRC = 0;

Routing_LCIRC *Routing_LCIRC::getInstance() {
    if (routing_LCIRC == 0)
        routing_LCIRC = new Routing_LCIRC();
    return routing_LCIRC;
}

// Алгоритм: кратчайший путь от 0 к v в циркулянте
// Вычисляет вектор (p1, p2) напрямую без расчета a*, b*, a*+b*
// Возвращает коэффициенты (c0, c2) где c0=p1, c2=p2 и стоимость cost = |p1| + |p2|
static void lcirc_best_coeffs_0_to_v(int v, int &c0, int &c2, int &best_cost)
{
    const int a  = GlobalParams::lcirc_a;
    const int b  = GlobalParams::lcirc_b;
    const int d  = GlobalParams::lcirc_d;

    // Шаг 1: Вычисляем xv и yv
    int xv = v % a;
    if (xv < 0) xv += a;  // Ensure positive
    
    // floor(v/a) для целых чисел
    int q = v / a;
    if (v < 0 && (v % a != 0)) q--;  // Adjust for negative v
    
    // yv = ceil(b/2) * [v/a] - b * [[v/a]/2]
    // ceil(b/2) для целых чисел: (b+1)/2
    int ceil_b2 = (b + 1) / 2;
    int yv = ceil_b2 * q - b * (q / 2);  // q/2 уже floor для целых

    // Шаг 2: Вычисляем p1 и p2 напрямую по условной логике
    int p1, p2;
    
    if ((yv < ceil_b2) && ((xv + yv) <= d)) {
        // Случай 1: (0,0) - вектор нуля, ближайшего к v
        p1 = xv;
        p2 = yv;
    } else if ((yv >= ceil_b2) && ((yv - xv) >= (b - d))) {
        // Случай 2: b* = (0,b) - вектор нуля, ближайшего к v
        p1 = xv;
        p2 = yv - b;
    } else {
        // Случай 3: a* = (a, ceil(b/2)) - вектор нуля, ближайшего к v
        p1 = xv - a;
        p2 = yv - (b/2);
    }

    c0 = p1;
    c2 = p2;
    best_cost = std::abs(p1) + std::abs(p2);
}

std::vector<int> Routing_LCIRC::route(Router *router, const RouteData &routeData)
{
    std::vector<int> dirs;

    const int N  = GlobalParams::lcirc_N;
    const int u  = routeData.current_id;
    const int w  = routeData.dst_id;

    if (u == w) {
        dirs.push_back(DIRECTION_LOCAL);
        return dirs;
    }

    // Сводим задачу к пути 0 -> v, где v = (w - u) mod N
    int v = w - u;
    v %= N;
    if (v < 0) v += N;  // Ensure v is in range [0, N-1]

    int c0 = 0, c2 = 0, best_cost = 0;
    lcirc_best_coeffs_0_to_v(v, c0, c2, best_cost);

    int first_dir;
    if (c0 > 0)
        first_dir = DIRECTION_SOUTH;   // +s1
    else if (c0 < 0)
        first_dir = DIRECTION_NORTH;   // -s1
    else if (c2 > 0)
        first_dir = DIRECTION_EAST;    // +s2
    else if (c2 < 0)
        first_dir = DIRECTION_WEST;    // -s2
    else
        first_dir = DIRECTION_LOCAL;   // v == 0, уже на месте по алгоритму

    dirs.push_back(first_dir);
    return dirs;
}
