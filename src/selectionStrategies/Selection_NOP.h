#ifndef __NOXIMSELECTION_NOP_H__
#define __NOXIMSELECTION_NOP_H__

#include "SelectionStrategy.h"
#include "SelectionStrategies.h"
#include "../Router.h"

using namespace std;

class Selection_NOP : SelectionStrategy {
	public:
        int apply(Router * router, const vector < int >&directions, const RouteData & route_data);
        void perCycleUpdate(Router * router);
        int arbitrate(Router * router, const vector<pair<int,int> >& reservations);

		static Selection_NOP * getInstance();

	private:
		Selection_NOP(){};
		~Selection_NOP(){};

		static Selection_NOP * selection_NOP;
		static SelectionStrategiesRegister selectionStrategiesRegister;
};

#endif
