#include "Selection_HOPCOUNT_MAX.h"
#include <climits>

SelectionStrategiesRegister Selection_HOPCOUNT_MAX::selectionStrategiesRegister("HOPCOUNT_MAX", getInstance());

Selection_HOPCOUNT_MAX * Selection_HOPCOUNT_MAX::selection_HOPCOUNT_MAX = 0;

Selection_HOPCOUNT_MAX * Selection_HOPCOUNT_MAX::getInstance() {
	if ( selection_HOPCOUNT_MAX == 0 )
		selection_HOPCOUNT_MAX = new Selection_HOPCOUNT_MAX();
    
	return selection_HOPCOUNT_MAX;
}

int Selection_HOPCOUNT_MAX::apply(Router * router, const vector < int >&directions, const RouteData & route_data){
    assert(directions.size()!=0);
    // For direction selection, use random (same as RANDOM)
    return directions[rand() % directions.size()];
}

void Selection_HOPCOUNT_MAX::perCycleUpdate(Router * router){ }

int Selection_HOPCOUNT_MAX::arbitrate(Router * router, const vector<pair<int,int> >& reservations) {
    assert(reservations.size() != 0);
    
    int max_hopcount = -1;
    vector<int> best_indices;
    
    // Find flits with maximum hopcount
    for (size_t i = 0; i < reservations.size(); i++) {
        int input_port = reservations[i].first;
        int vc = reservations[i].second;
        
        if (!router->buffer[input_port][vc].IsEmpty()) {
            Flit flit = router->buffer[input_port][vc].Front();
            
            if (flit.hop_no > max_hopcount) {
                max_hopcount = flit.hop_no;
                best_indices.clear();
                best_indices.push_back(i);
            } else if (flit.hop_no == max_hopcount) {
                best_indices.push_back(i);
            }
        }
    }
    
    // If no valid flits found, return random
    if (best_indices.size() == 0) {
        return rand() % reservations.size();
    }
    
    // Return random among best (maximum hopcount)
    return best_indices[rand() % best_indices.size()];
}
