#include "Routing_LCIRC_VIRTUALCOORD.h"
#include <cmath>
#include <iostream>
#include <vector>
#include <algorithm>

RoutingAlgorithmsRegister Routing_LCIRC_VIRTUALCOORD::routingAlgorithmsRegister("LCIRC_VIRTUALCOORD", getInstance());

Routing_LCIRC_VIRTUALCOORD *Routing_LCIRC_VIRTUALCOORD::routing_LCIRC_VIRTUALCOORD = 0;
bool Routing_LCIRC_VIRTUALCOORD::initialized = false;
std::vector<std::pair<int, int> > Routing_LCIRC_VIRTUALCOORD::node_coordinates;
std::vector<std::pair<int, int> > Routing_LCIRC_VIRTUALCOORD::canonical_zeros;

Routing_LCIRC_VIRTUALCOORD *Routing_LCIRC_VIRTUALCOORD::getInstance() {
    if (routing_LCIRC_VIRTUALCOORD == 0)
        routing_LCIRC_VIRTUALCOORD = new Routing_LCIRC_VIRTUALCOORD();
    return routing_LCIRC_VIRTUALCOORD;
}

// Инициализирует систему координат и нулевые векторы
void Routing_LCIRC_VIRTUALCOORD::initializeCoordinates()
{
    const int N  = GlobalParams::lcirc_N;
    const int s1 = GlobalParams::lcirc_s1;
    const int s2 = GlobalParams::lcirc_s2;
    
    // Увеличиваем max_search для больших графов
    int max_search = std::max(15, (int)(std::sqrt(N) * 2));
    
    // Инициализируем массив координат узлов
    node_coordinates.clear();
    node_coordinates.resize(N, std::make_pair(0, 0));
    
    // Находим координаты всех узлов
    for (int node_id = 0; node_id < N; node_id++) {
        std::pair<int, int> best_coord(0, 0);
        int best_dist = 1000000;
        
        for (int x = -max_search; x <= max_search; x++) {
            for (int y = -max_search; y <= max_search; y++) {
                int value = (x * s1 + y * s2) % N;
                if (value < 0) value += N;
                
                if (value == node_id) {
                    int dist = std::abs(x) + std::abs(y);
                    if (dist < best_dist) {
                        best_dist = dist;
                        best_coord = std::make_pair(x, y);
                    }
                }
            }
        }
        
        node_coordinates[node_id] = best_coord;
    }
    
    // Находим канонические координаты нулей
    std::vector<std::pair<int, int> > zero_coords;
    
    // Находим все координаты нулей
    for (int x = -max_search; x <= max_search; x++) {
        for (int y = -max_search; y <= max_search; y++) {
            int value = (x * s1 + y * s2) % N;
            if (value < 0) value += N;
            if (value == 0 && (x != 0 || y != 0)) {
                zero_coords.push_back(std::make_pair(x, y));
            }
        }
    }
    
    // Определяем квадрант
    auto get_quadrant = [](int x, int y) -> int {
        if (x > 0 && y > 0) return 1;
        if (x < 0 && y > 0) return 2;
        if (x < 0 && y < 0) return 3;
        if (x > 0 && y < 0) return 4;
        if (x == 0 && y > 0) return 1;
        if (x == 0 && y < 0) return 3;
        if (x > 0 && y == 0) return 4;
        if (x < 0 && y == 0) return 2;
        return 0;
    };
    
    // Сортируем по манхэттенскому расстоянию
    std::sort(zero_coords.begin(), zero_coords.end(), 
        [](const std::pair<int, int>& a, const std::pair<int, int>& b) {
            return std::abs(a.first) + std::abs(a.second) < std::abs(b.first) + std::abs(b.second);
        });
    
    // Выбираем по одному из каждого квадранта
    canonical_zeros.clear();
    bool quadrants_found[5] = {false, false, false, false, false};
    
    for (const auto& coord : zero_coords) {
        if (canonical_zeros.size() >= 4) break;
        
        int quad = get_quadrant(coord.first, coord.second);
        if (quad != 0 && !quadrants_found[quad]) {
            canonical_zeros.push_back(coord);
            quadrants_found[quad] = true;
        }
    }
    
    // Если не нашли все 4, добавляем ближайшие
    if (canonical_zeros.size() < 4) {
        for (const auto& coord : zero_coords) {
            if (canonical_zeros.size() >= 4) break;
            bool found = false;
            for (const auto& c : canonical_zeros) {
                if (c.first == coord.first && c.second == coord.second) {
                    found = true;
                    break;
                }
            }
            if (!found) {
                canonical_zeros.push_back(coord);
            }
        }
    }
    
    initialized = true;
}

// Проверяет и инициализирует при необходимости
void Routing_LCIRC_VIRTUALCOORD::ensureInitialized()
{
    if (!initialized) {
        initializeCoordinates();
    }
}

// Вычисляет маршрут от узла u к узлу w используя предвычисленные виртуальные координаты
std::pair<int, int> Routing_LCIRC_VIRTUALCOORD::calculate_route_virtual_coord(int u, int w, int d)
{
    // Используем предвычисленные координаты узлов
    int Xu = node_coordinates[u].first;
    int Yu = node_coordinates[u].second;
    int Xw = node_coordinates[w].first;
    int Yw = node_coordinates[w].second;
    
    // Вычисляем разность
    int X = Xw - Xu;
    int Y = Yw - Yu;
    
    // Если расстояние уже <= d, возвращаем
    if (std::abs(X) + std::abs(Y) <= d) {
        return std::make_pair(X, Y);
    }
    
    // Используем предвычисленные канонические координаты нулей
    // Исключаем (0,0)
    std::vector<std::pair<int, int> > zeros;
    for (const auto& z : canonical_zeros) {
        if (z.first != 0 || z.second != 0) {
            zeros.push_back(z);
        }
    }
    
    // Ищем оптимальный вектор
    int best_X = X, best_Y = Y;
    int best_dist = std::abs(X) + std::abs(Y);
    
    // Пробуем прибавлять векторы нулей итеративно
    bool improved = true;
    int iterations = 0;
    const int max_iterations = 10;
    
    while (improved && iterations < max_iterations && best_dist > d) {
        improved = false;
        iterations++;
        
        for (const auto& zero : zeros) {
            int zero_x = zero.first;
            int zero_y = zero.second;
            
            // Пробуем прибавить
            int new_X = best_X + zero_x;
            int new_Y = best_Y + zero_y;
            int new_dist = std::abs(new_X) + std::abs(new_Y);
            
            if (new_dist < best_dist) {
                best_X = new_X;
                best_Y = new_Y;
                best_dist = new_dist;
                improved = true;
                if (best_dist <= d) break;
            }
            
            // Пробуем вычесть
            new_X = best_X - zero_x;
            new_Y = best_Y - zero_y;
            new_dist = std::abs(new_X) + std::abs(new_Y);
            
            if (new_dist < best_dist) {
                best_X = new_X;
                best_Y = new_Y;
                best_dist = new_dist;
                improved = true;
                if (best_dist <= d) break;
            }
        }
    }
    
    // Если все еще не достигли d, пробуем комбинации двух векторов
    if (best_dist > d) {
        for (size_t i = 0; i < zeros.size(); i++) {
            for (size_t j = i + 1; j < zeros.size(); j++) {
                int zero_x1 = zeros[i].first, zero_y1 = zeros[i].second;
                int zero_x2 = zeros[j].first, zero_y2 = zeros[j].second;
                
                for (int sign1 = -1; sign1 <= 1; sign1 += 2) {
                    for (int sign2 = -1; sign2 <= 1; sign2 += 2) {
                        int new_X = best_X + sign1 * zero_x1 + sign2 * zero_x2;
                        int new_Y = best_Y + sign1 * zero_y1 + sign2 * zero_y2;
                        int new_dist = std::abs(new_X) + std::abs(new_Y);
                        
                        if (new_dist < best_dist) {
                            best_X = new_X;
                            best_Y = new_Y;
                            best_dist = new_dist;
                            if (best_dist <= d) goto done;
                        }
                    }
                }
            }
        }
    }
    
done:
    return std::make_pair(best_X, best_Y);
}

std::vector<int> Routing_LCIRC_VIRTUALCOORD::route(Router *router, const RouteData &routeData)
{
    std::vector<int> dirs;

    const int u  = routeData.current_id;
    const int w  = routeData.dst_id;
    const int d  = GlobalParams::lcirc_d;

    if (u == w) {
        dirs.push_back(DIRECTION_LOCAL);
        return dirs;
    }

    // Убеждаемся, что координаты инициализированы
    ensureInitialized();

    // Вычисляем маршрут используя предвычисленные виртуальные координаты
    std::pair<int, int> vec = Routing_LCIRC_VIRTUALCOORD::calculate_route_virtual_coord(u, w, d);
    int X = vec.first;
    int Y = vec.second;

    // Определяем направление на основе вектора
    int first_dir;
    if (X > 0)
        first_dir = DIRECTION_SOUTH;   // +s1
    else if (X < 0)
        first_dir = DIRECTION_NORTH;   // -s1
    else if (Y > 0)
        first_dir = DIRECTION_EAST;    // +s2
    else if (Y < 0)
        first_dir = DIRECTION_WEST;    // -s2
    else
        first_dir = DIRECTION_LOCAL;

    dirs.push_back(first_dir);
    return dirs;
}
