#ifndef __NOXIMSELECTION_DISTANCE_MAX_H__
#define __NOXIMSELECTION_DISTANCE_MAX_H__

#include "SelectionStrategy.h"
#include "SelectionStrategies.h"
#include "../Router.h"

using namespace std;

class Selection_DISTANCE_MAX : SelectionStrategy {
	public:
        int apply(Router * router, const vector < int >&directions, const RouteData & route_data);
        void perCycleUpdate(Router * router);
        int arbitrate(Router * router, const vector<pair<int,int> >& reservations);

		static Selection_DISTANCE_MAX * getInstance();

	private:
		Selection_DISTANCE_MAX(){};
		~Selection_DISTANCE_MAX(){};
		
		// Helper function to calculate remaining distance to destination
		int calculateRemainingDistance(int current_id, int dst_id);

		static Selection_DISTANCE_MAX * selection_DISTANCE_MAX;
		static SelectionStrategiesRegister selectionStrategiesRegister;
};

#endif
