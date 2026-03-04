#include "Selection_HOPCOUNT_MIN.h"
#include <climits>

SelectionStrategiesRegister Selection_HOPCOUNT_MIN::selectionStrategiesRegister("HOPCOUNT_MIN", getInstance());

Selection_HOPCOUNT_MIN * Selection_HOPCOUNT_MIN::selection_HOPCOUNT_MIN = 0;

Selection_HOPCOUNT_MIN * Selection_HOPCOUNT_MIN::getInstance() {
	if ( selection_HOPCOUNT_MIN == 0 )
		selection_HOPCOUNT_MIN = new Selection_HOPCOUNT_MIN();
    
	return selection_HOPCOUNT_MIN;
}

int Selection_HOPCOUNT_MIN::apply(Router * router, const vector < int >&directions, const RouteData & route_data){
    assert(directions.size()!=0);
    // For direction selection, use random (same as RANDOM)
    return directions[rand() % directions.size()];
}

void Selection_HOPCOUNT_MIN::perCycleUpdate(Router * router){ }

int Selection_HOPCOUNT_MIN::arbitrate(Router * router, const vector<pair<int,int> >& reservations) {
    assert(reservations.size() != 0);
    
    int min_hopcount = INT_MAX;
    vector<int> best_indices;
    
    // Find flits with minimum hopcount
    for (size_t i = 0; i < reservations.size(); i++) {
        int input_port = reservations[i].first;
        int vc = reservations[i].second;
        
        if (!router->buffer[input_port][vc].IsEmpty()) {
            Flit flit = router->buffer[input_port][vc].Front();
            
            if (flit.hop_no < min_hopcount) {
                min_hopcount = flit.hop_no;
                best_indices.clear();
                best_indices.push_back(i);
            } else if (flit.hop_no == min_hopcount) {
                best_indices.push_back(i);
            }
        }
    }
    
    // If no valid flits found, return random
    if (best_indices.size() == 0) {
        return rand() % reservations.size();
    }
    
    // Return random among best (minimum hopcount)
    return best_indices[rand() % best_indices.size()];
}
