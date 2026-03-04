#ifndef __NOXIMSELECTION_DISTANCE_MIN_H__
#define __NOXIMSELECTION_DISTANCE_MIN_H__

#include "SelectionStrategy.h"
#include "SelectionStrategies.h"
#include "../Router.h"

using namespace std;

class Selection_DISTANCE_MIN : SelectionStrategy {
	public:
        int apply(Router * router, const vector < int >&directions, const RouteData & route_data);
        void perCycleUpdate(Router * router);
        int arbitrate(Router * router, const vector<pair<int,int> >& reservations);

		static Selection_DISTANCE_MIN * getInstance();

	private:
		Selection_DISTANCE_MIN(){};
		~Selection_DISTANCE_MIN(){};
		
		// Helper function to calculate remaining distance to destination
		int calculateRemainingDistance(int current_id, int dst_id);

		static Selection_DISTANCE_MIN * selection_DISTANCE_MIN;
		static SelectionStrategiesRegister selectionStrategiesRegister;
};

#endif
