"""
Runs the query algorithm
1. Run the sample query on Anaheim as given in GitHub
2. After that place this code in the directory with query_file.py and run
3. Run this at cores<= 30 cores for now
"""
from time import time as time_measure
from miscellaneous_func import *
from multiprocessing import Pool

print_logo()


from RAPTOR.raptor_functions_dhanus import *

NETWORK_NAME = './anaheim'
stops_file, trips_file, stop_times_file, transfers_file, stops_dict, stoptimes_dict, footpath_dict, routes_by_stop_dict, idx_by_route_stop_dict = read_testcase(
    NETWORK_NAME)
MAX_TRANSFER, WALKING_FROM_SOURCE, CHANGE_TIME_SEC = 6, 1, 0
PRINT_ITINERARY, OPTIMIZED = 1, 0
D_TIME = stop_times_file.arrival_time.sort_values().iloc[0]


def raptor_dhanus(SOURCE: int, DESTINATION: int) -> list:
    '''
    Standard Raptor implementation

    Args:
        SOURCE (int): stop id of source stop.
        DESTINATION (int): stop id of destination stop.
        D_TIME (pandas.datetime): departure time.
        MAX_TRANSFER (int): maximum transfer limit.
        WALKING_FROM_SOURCE (int): 1 or 0. 1 indicates walking from SOURCE is allowed.
        CHANGE_TIME_SEC (int): change-time in seconds.
        PRINT_ITINERARY (int): 1 or 0. 1 means print complete path.
        routes_by_stop_dict (dict): preprocessed dict. Format {stop_id: [id of routes passing through stop]}.
        stops_dict (dict): preprocessed dict. Format {route_id: [ids of stops in the route]}.
        stoptimes_dict (dict): preprocessed dict. Format {route_id: [[trip_1], [trip_2]]}.
        footpath_dict (dict): preprocessed dict. Format {from_stop_id: [(to_stop_id, footpath_time)]}.
        idx_by_route_stop_dict (dict): preprocessed dict. Format {(route id, stop id): stop index in route}.

    Returns:
        out (list): list of pareto-optimal arrival timestamps.

    Examples:
        >>> output = raptor(36, 52, pd.to_datetime('2022-06-30 05:41:00'), 4, 1, 0, 1, routes_by_stop_dict, stops_dict, stoptimes_dict, footpath_dict, idx_by_route_stop_dict)
        >>> print(f"Optimal arrival time are: {output}")

    See Also:
        HypRAPTOR, Tip-based Public Transit Routing (TBTR)
    '''

    out = []
    # Initialization
    marked_stop, marked_stop_dict, label, pi_label, star_label, inf_time = initialize_raptor(routes_by_stop_dict, SOURCE, MAX_TRANSFER)
    change_time = pd.to_timedelta(CHANGE_TIME_SEC, unit='seconds')
    (label[0][SOURCE], star_label[SOURCE]) = (D_TIME, D_TIME)
    Q = {}  # Format of Q is {route:stop index}
    if WALKING_FROM_SOURCE == 1:
        try:
            trans_info = footpath_dict[SOURCE]
            for i in trans_info:
                (p_dash, to_pdash_time) = i
                label[0][p_dash] = D_TIME + to_pdash_time
                star_label[p_dash] = D_TIME + to_pdash_time
                pi_label[0][p_dash] = ('walking', SOURCE, p_dash, to_pdash_time, D_TIME + to_pdash_time)
                if marked_stop_dict[p_dash] == 0:
                    marked_stop.append(p_dash)
                    marked_stop_dict[p_dash] = 1
        except KeyError:
            pass

    # Main Code
    # Main code part 1
    for k in range(1, MAX_TRANSFER + 1):
        Q.clear()
        while marked_stop:
            p = marked_stop.pop()
            marked_stop_dict[p] = 0
            try:
                routes_serving_p = routes_by_stop_dict[p]
                for route in routes_serving_p:
                    stp_idx = idx_by_route_stop_dict[(route, p)]
                    try:
                        Q[route] = min(stp_idx, Q[route])
                    except KeyError:
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
                if current_trip_t == -1 or label[k - 1][p_i] + change_time < current_trip_t[current_stopindex_by_route][
                    1]:  # assuming arrival_time = departure_time
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
                    if label[k][p_dash] > new_p_dash_time and new_p_dash_time < min(star_label[p_dash], star_label[DESTINATION]):
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
                # print('code ended with termination condition')
                pass
            break
    _, _, rap_out = post_processing_dhanus(DESTINATION, pi_label, PRINT_ITINERARY, label)
    out.append((SOURCE,DESTINATION,D_TIME,rap_out))
    return out

if __name__ == "__main__":
    # Read network

    print_network_details(transfers_file, trips_file, stops_file)
    # od_pair_list = [(36,52), (52, 43)]
    # Query parameters
    
    arguments = [(36,52)]
    cores = 30
    start = time_measure()
    with Pool(cores) as pool:
        result = pool.starmap(raptor_dhanus, arguments )
        
    with open('./travel_time_data.txt', 'w') as f:
        header = ("origin,destination,departure_time,"
                "transfers,walk_time,wait_time,ovtt,ivtt\n")
        f.write(header)
            
        for super_output in result:
            
            print("super output :",super_output)
            
            origin, destination, time, output = super_output[0]
            
            if output is not None:
                output_tt = output['tt']
                for tr, t_times in output_tt:
                    walk_time = t_times['walk_time']
                    wait_time = t_times['wait_time']
                    ovtt = t_times['ovtt']
                    ivtt = t_times['ivtt']

                    line = [origin, destination, time, tr, walk_time,
                            wait_time, ovtt, ivtt]
                    line = [str(x) for x in line]
                    line = ','.join(line)
                    line = line + '\n'
                    f.write(line)

