#ifndef __NOXIMSELECTION_HOPCOUNT_MIN_H__
#define __NOXIMSELECTION_HOPCOUNT_MIN_H__

#include "SelectionStrategy.h"
#include "SelectionStrategies.h"
#include "../Router.h"

using namespace std;

class Selection_HOPCOUNT_MIN : SelectionStrategy {
	public:
        int apply(Router * router, const vector < int >&directions, const RouteData & route_data);
        void perCycleUpdate(Router * router);
        int arbitrate(Router * router, const vector<pair<int,int> >& reservations);

		static Selection_HOPCOUNT_MIN * getInstance();

	private:
		Selection_HOPCOUNT_MIN(){};
		~Selection_HOPCOUNT_MIN(){};

		static Selection_HOPCOUNT_MIN * selection_HOPCOUNT_MIN;
		static SelectionStrategiesRegister selectionStrategiesRegister;
};

#endif
