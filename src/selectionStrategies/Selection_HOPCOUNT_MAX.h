#ifndef __NOXIMSELECTION_HOPCOUNT_MAX_H__
#define __NOXIMSELECTION_HOPCOUNT_MAX_H__

#include "SelectionStrategy.h"
#include "SelectionStrategies.h"
#include "../Router.h"

using namespace std;

class Selection_HOPCOUNT_MAX : SelectionStrategy {
	public:
        int apply(Router * router, const vector < int >&directions, const RouteData & route_data);
        void perCycleUpdate(Router * router);
        int arbitrate(Router * router, const vector<pair<int,int> >& reservations);

		static Selection_HOPCOUNT_MAX * getInstance();

	private:
		Selection_HOPCOUNT_MAX(){};
		~Selection_HOPCOUNT_MAX(){};

		static Selection_HOPCOUNT_MAX * selection_HOPCOUNT_MAX;
		static SelectionStrategiesRegister selectionStrategiesRegister;
};

#endif
