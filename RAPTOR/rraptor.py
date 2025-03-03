"""
Module contains rRAPTOR implementation
"""
from RAPTOR.raptor_functions import *


def rraptor(SOURCE: int, DESTINATION: int, d_time_groups, MAX_TRANSFER: int, WALKING_FROM_SOURCE: int, CHANGE_TIME_SEC: int, PRINT_ITINERARY: int,
            OPTIMIZED: int, routes_by_stop_dict: dict, stops_dict: dict, stoptimes_dict: dict, footpath_dict: dict, idx_by_route_stop_dict: dict) -> list:
    '''
    Standard rRaptor implementation

    Args:
        SOURCE (int): stop id of source stop.
        DESTINATION (int): stop id of destination stop.
        d_time_groups (pandas.group): all possible departures times from all stops.
        MAX_TRANSFER (int): maximum transfer limit.
        WALKING_FROM_SOURCE (int): 1 or 0. 1 means walking from SOURCE is allowed.
        CHANGE_TIME_SEC (int): change-time in seconds.
        PRINT_ITINERARY (int): 1 or 0. 1 means print complete path.
        OPTIMIZED (int): 1 or 0. 1 means collect trips and 0 means collect routes.
        routes_by_stop_dict (dict): preprocessed dict. Format {stop_id: [id of routes passing through stop]}.
        stops_dict (dict): preprocessed dict. Format {route_id: [ids of stops in the route]}.
        stoptimes_dict (dict): preprocessed dict. Format {route_id: [[trip_1], [trip_2]]}.
        footpath_dict (dict): preprocessed dict. Format {from_stop_id: [(to_stop_id, footpath_time)]}.
        idx_by_route_stop_dict (dict): preprocessed dict. Format {(route id, stop id): stop index in route}.

    Returns:
        if OPTIMIZED==1:
            out (list):  list of trips required to cover all optimal journeys Format: [trip_id]
        elif OPTIMIZED==0:
            out (list):  list of routes required to cover all optimal journeys. Format: [route_id]

    Examples:
        >>> output = rraptor(36, 52, d_time_groups, 4, 1, 0, 1, 0, routes_by_stop_dict, stops_dict, stoptimes_dict, footpath_dict, idx_by_route_stop_dict)
        >>> print(f"Optimal arrival time are: {output}")

    See Also:
        One-To-Many rRAPTOR

    '''
    out = []

    d_time_list = d_time_groups.get_group(SOURCE)[["trip_id", 'arrival_time', 'stop_sequence']].values.tolist()
    if WALKING_FROM_SOURCE == 1:
        try:
            source_footpaths = footpath_dict[SOURCE]
            for connection in source_footpaths:
                d_time_list.extend(d_time_groups.get_group(connection[0])[["trip_id", 'arrival_time', 'stop_sequence']].values.tolist())
        except KeyError:
            pass
    d_time_list.sort(key=lambda x: x[1], reverse=True)

    _, _, label, _, star_label, inf_time = initialize_raptor(routes_by_stop_dict, SOURCE, MAX_TRANSFER)
    change_time = pd.to_timedelta(CHANGE_TIME_SEC, unit='seconds')

    for dep_details in d_time_list:
        pi_label = {x: {stop: -1 for stop in routes_by_stop_dict.keys()} for x in range(0, MAX_TRANSFER + 1)}
        marked_stop = deque()
        marked_stop_dict = {stop: 0 for stop in routes_by_stop_dict.keys()}  # Binary variable indicating if a stop is marked
        start_tid, d_time, s_idx = dep_details
        first_stop = stops_dict[int(start_tid.split("_")[0])][s_idx]
        if first_stop!=SOURCE:
            marked_stop.append(first_stop)
            marked_stop_dict[first_stop] = 1
            to_pdash_time = [foot_connect[1] for foot_connect in footpath_dict[SOURCE] if foot_connect[0]==first_stop][0]
            label[0][first_stop] = d_time - change_time
            star_label[first_stop] = d_time - change_time
            pi_label[0][first_stop] = ('walking', SOURCE, first_stop, to_pdash_time, d_time - change_time)
        else:
            marked_stop.append(SOURCE)
            marked_stop_dict[SOURCE] = 1
            (label[0][SOURCE], star_label[SOURCE]) = (d_time, d_time)
        if PRINT_ITINERARY == 1:
            print(f"SOURCE, DESTINATION, d_time: {SOURCE, DESTINATION, d_time}")
        # Initialization
        Q = {}
        # Main Code
        # Main code part 1
        for k in range(1, MAX_TRANSFER + 1):
            Q.clear()  # Format of Q is {route:stop}
            while marked_stop:
                p = marked_stop.pop()
                marked_stop_dict[p] = 0
                if k == 1:
                    Q[int(start_tid.split('_')[0])] = s_idx
                    break
                try:
                    routes_serving_p = routes_by_stop_dict[p]
                    for route in routes_serving_p:
                        stp_idx = idx_by_route_stop_dict[(route, p)]
                        if route in Q.keys() and Q[route] != stp_idx:
                            Q[route] = min(stp_idx, Q[route])
                        else:
                            Q[route] = stp_idx
                except KeyError:
                    continue
            # Main code part 2
            for route, current_stopindex_by_route in Q.items():
                current_trip_t = -1
                for p_i in stops_dict[route][current_stopindex_by_route:]:
                    if current_trip_t != -1 and current_trip_t[current_stopindex_by_route][1] < min(star_label[p_i], star_label[DESTINATION]):
                        arr_by_t_at_pi = current_trip_t[current_stopindex_by_route][1]
                        label[k][p_i], star_label[p_i] = arr_by_t_at_pi, arr_by_t_at_pi
                        pi_label[k][p_i] = (boarding_time, boarding_point, p_i, arr_by_t_at_pi, tid)
                        if marked_stop_dict[p_i] == 0:
                            marked_stop.append(p_i)
                            marked_stop_dict[p_i] = 1
                    if current_trip_t == -1 or label[k - 1][p_i] + change_time < current_trip_t[current_stopindex_by_route][1]: # assuming arrival_time = departure_time
                        tid, current_trip_t = get_latest_trip_new(stoptimes_dict, route, label[k - 1][p_i], current_stopindex_by_route, change_time)
                        if current_trip_t == -1:
                            boarding_time, boarding_point = -1, -1
                        else:
                            boarding_point = p_i
                            boarding_time = current_trip_t[current_stopindex_by_route][1]
                    current_stopindex_by_route = current_stopindex_by_route + 1
            # Main code part 3
            marked_stop_copy = [*marked_stop]
            for p in marked_stop_copy:
                try:
                    trans_info = footpath_dict[p]
                    for i in trans_info:
                        (p_dash, to_pdash_time) = i
                        new_p_dash_time = label[k][p] + to_pdash_time
                        if (label[k][p_dash] > new_p_dash_time) and new_p_dash_time < min(star_label[p_dash], star_label[DESTINATION]):
                            label[k][p_dash], star_label[p_dash] = new_p_dash_time, new_p_dash_time
                            pi_label[k][p_dash] = ('walking', p, p_dash, to_pdash_time, new_p_dash_time)
                            if marked_stop_dict[p_dash] == 0:
                                marked_stop.append(p_dash)
                                marked_stop_dict[p_dash] = 1
                except KeyError:
                    continue
            # Main code End
            if marked_stop == deque([]):
                if PRINT_ITINERARY == 1:
                    print('code ended with termination condition')
                break
        out.extend(post_processing_rraptor(DESTINATION, pi_label, PRINT_ITINERARY, label, OPTIMIZED, D_TIME=d_time))
        if PRINT_ITINERARY == 1:
            print('------------------------------------')
    return out
