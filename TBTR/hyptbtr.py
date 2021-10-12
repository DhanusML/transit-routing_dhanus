"""
Module contains HypTBTR implementation.
"""
from TBTR.TBTR_functions import *


def hyptbtr(SOURCE, DESTINATION, D_TIME, MAX_TRANSFER, WALKING_FROM_SOURCE, PRINT_PARA, stop_out, trip_groups,
            routes_by_stop_dict, stops_dict, stoptimes_dict, footpath_dict, trip_transfer_dict, trip_set):
    """
    Hyptbtr implementation.
    Args:
        SOURCE (int): stop id of source stop.
        DESTINATION (int): stop id of destination stop.
        D_TIME (pandas.datetime): departure time.
        MAX_TRANSFER (int): maximum transfer limit.
        WALKING_FROM_SOURCE (int): 1 or 0. 1 means walking from SOURCE is allowed.
        PRINT_PARA (int): 1 or 0. 1 means print complete path.
        stop_out (dict): key: stop-id (int), value: stop-cell id of key (int). Note: stop-cell id=-1 denotes cut stop.
        trip_groups (dict): key: tuple of all possible combinations of stop cell id, value: set of trip ids belonging to the stop cell combination
        routes_by_stop_dict (dict): preprocessed dict. Format {stop_id: [id of routes passing through stop]}.
        stops_dict (dict): preprocessed dict. Format {route_id: [ids of stops in the route]}.
        stoptimes_dict (dict): preprocessed dict. Format {route_id: [[trip_1], [trip_2]]}.
        footpath_dict (dict): preprocessed dict. Format {from_stop_id: [(to_stop_id, footpath_time)]}.
        trip_transfer_dict (nested dict): keys: id of trip we are transferring from, value: {keys: stop number, value: list of tuples of form (id of trip we are transferring to, stop number)}.
        trip_set (set): set of trip ids from which trip-transfers are available.
    Returns:
        out (list): List of pareto-optimal arrival Timestamps
    """
    out = []
    final_trips = trip_groups[tuple(sorted((stop_out[SOURCE], stop_out[DESTINATION])))]

    J = initialize_tbtr()

    L = initialize_from_desti_new(routes_by_stop_dict, stops_dict, DESTINATION, footpath_dict)

    R_t, Q = initialize_from_source_new(footpath_dict, SOURCE, routes_by_stop_dict, stops_dict, stoptimes_dict,
                                        D_TIME, MAX_TRANSFER, WALKING_FROM_SOURCE)

    n = 0
    while n < MAX_TRANSFER:
        for trip in Q[n]:
            from_stop, tid, to_stop, trip_route, tid_idx = trip[0: 5]
            trip = stoptimes_dict[trip_route][tid_idx][from_stop:to_stop]
            try:
                L[trip_route]
                stop_list, _ = zip(*trip)
                for last_leg in L[trip_route]:
                    idx = [x[0] for x in enumerate(stop_list) if x[1] == last_leg[2]]
                    if idx and from_stop < last_leg[0] and trip[idx[0]][1] + last_leg[1] < J[n][0]:
                        if last_leg[1] == pd.to_timedelta(0, unit="seconds"):
                            walking = (0, 0)
                        else:
                            walking = (1, stops_dict[trip_route][last_leg[0]])
                        J = update_label(trip[idx[0]][1] + last_leg[1], n, (tid, walking), J, MAX_TRANSFER)
            except KeyError:
                pass
            try:
                if tid in trip_set and trip[1][1] < J[n][0]:
                    connection_list = [connection for from_stop_idx, transfer_stop_id in
                                       enumerate(trip[1:], from_stop + 1)
                                       for connection in trip_transfer_dict[tid][from_stop_idx] if
                                       connection[0] in final_trips]
                    enqueue(connection_list, n + 1, (tid, 0, 0), R_t, Q, stoptimes_dict)
            except IndexError:
                pass
        n = n + 1
    tbtr_out = post_process(J, Q, DESTINATION, SOURCE, footpath_dict, stops_dict, stoptimes_dict, PRINT_PARA,
                            D_TIME, MAX_TRANSFER)
    out.append(tbtr_out)
    return out
