#ifndef __NOXIMSELECTIONSTRATEGY_H__
#define __NOXIMSELECTIONSTRATEGY_H__

#include <vector>
#include "../DataStructs.h"
#include "../Utils.h"

using namespace std;

struct Router;

class SelectionStrategy
{
	public:
        virtual int apply(Router * router, const vector < int >&directions, const RouteData & route_data) = 0;
        virtual void perCycleUpdate(Router * router) = 0;
        
        // Arbitration method: selects a reservation from multiple reservations for the same output port
        // Returns index in reservations vector, or -1 if no valid selection
        virtual int arbitrate(Router * router, const vector<pair<int,int> >& reservations) = 0;
};

#endif
