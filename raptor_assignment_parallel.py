from multiprocessing import pool
from miscellaneous_func import read_testcase
from multiprocessing import Pool
from time import time
from RAPTOR.raptor_functions import *
import numpy as np
import pandas as pd
from tqdm import tqdm


def raptor_dhanus_par(SOURCE: int, DESTINATION: int, D_TIME) -> list:
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
    out.append(rap_out)
    return out


def generate_od_matrix_with_time(size: int) -> np.ndarray:
    """
    Generates random origin destination pairs

    Params:
    size (int): the number of pairs requiered

    Returns:
    od_mat (np.ndarray): size*2 matrix of np.int32's ,
                         each row is an o-d pair

    """
    data = pd.read_csv(f'./GTFS/{NETWORK_NAME}/stops.txt')
    stop_ids = data['stop_id']

    start_indices = np.random.choice(np.arange(len(data)), size=size)
    stop_indices = np.random.choice(np.arange(len(data)), size=size)

    origin_ids = list(stop_ids.loc[start_indices])
    destination_ids = list(stop_ids.loc[stop_indices])
    date_times = [_gen_random_date_time() for _ in range(size)]

    od_mat = [(origin_ids[i], destination_ids[i], date_times[i])
              for i in range(size)]

    return od_mat


def _gen_random_date_time(date='2012-06-10'):
    """
    Returns a random date time.

    Args:
    date (str): date in the format `YYYY-MM-DD'.

    Returns:
    date_time (pd.datetime.datetime): random datetime object.
    """
    departure_date = date
    date_time = ':'.join(
        [
            str(np.random.randint(0, 24)).zfill(2),  # hour
            str(np.random.randint(0, 60)).zfill(2),  # minute
            '00'  # seconds
        ]
    )

    date_time = pd.to_datetime(departure_date + ' ' + date_time)
    return date_time


def get_available_options_par(od_mat: list) -> list:
    """
    Returns the list of list of pareto-optimal journeys.

    Params:
    od_mat (np.ndarray): each row is an origin destination pair.

    Returns:
    pareto_journeys (list): each entry of this list is a list of
                            pareto optimal journey for the o-d pair.
                            [[Journey,Journey], [Journey,Journey],...]
                            (See Journey from journey_rep for reference on
                            Journey object.)
    """
    pareto_journeys = []

    with Pool(CORES) as pool:
        outputs = pool.starmap(raptor_dhanus_par, od_mat)

    for output in outputs:
        if output[0] is not None:
            choices = output[0]['journeys']
            pareto_journeys.append(choices)

    return pareto_journeys


def _make_choice(util_list):
    """
    Picks the journey using the choice model, i.e, by
    computing the probabilities from the utility value of each
    journey.

    Args:
    util_list (list): list of floats.

    Returns:
    i (int): a random sample from [1...len(util_list)], where probability
             of picking i is p_i = exp(u_i)/\sum{exp(u_i)}
    """
    if len(util_list) == 1:
        return 0

    prob_list = np.array(util_list)
    prob_list = np.exp(prob_list)
    prob_list = prob_list/sum(prob_list)

    cumul_probs = np.zeros(len(prob_list)+1)
    for i in range(1, len(prob_list)+1):
        cumul_probs[i] = sum(prob_list[:i])

    rand_fl = np.random.random()

    for i in range(len(cumul_probs)-1):
        if cumul_probs[i] <= rand_fl and rand_fl <= cumul_probs[i+1]:
            return i

    print("not found")
    return 0


def get_optimal_choices(od_mat, beta):
    """
    Make choice of journey using the choice model.

    Args:
    od_mat (np.ndarray): matrix with rows being source destination pairs.
    beta (list): list of parameters of the choice model.

    Returns:
    selected_journeys (list): list of journeys chosen as per the model.
                              Formal: [Journey, Journey,...]

    """
    bT, bN = beta[0], beta[1]

    print("getting pareto optimal journeys")
    list_of_pareto_journeys = get_available_options_par(od_mat)
    selected_journeys = []

    print("making choice")
    for pareto_journeys in tqdm(list_of_pareto_journeys):
        util_list = []
        for journey in pareto_journeys:
            travel_time = journey.get_ovtt() + journey.get_ivtt()
            num_transfers = journey.transfers
            u = bT*travel_time/3600 + bN*num_transfers  # travelteim hrs
            util_list.append(u)

        choice = _make_choice(util_list)
        selected_journeys.append(pareto_journeys[choice])

    return selected_journeys


def get_segment_occupancy(journeys):
    """
    Takes a list of journeys as input and returns a dictionary,
    representing how crowded each trip is.

    Arguments:
    journeys (list): list of journeys (journey_rep.Journey object).

    Returns:
    occupancy_dict (dict): dictionary object, with keys
                           `trip_id'.
                           occupancy_dict[trip_id] = dict_segments,
                           where dict_segment[segment] gives the
                           number of passengers in the segment.
                           segment is of the form (start_id, stop_id),
                           the stop_id's of the origin and destination.
                           So, occupancy_dict[trip_id][(s1,s2)] gives
                           the number of people who were on the
                           trip `trip_id', from stops s1 to s2
    """
    occupancy_dict = {}

    for journey in journeys:
        thisJourneySeq = journey.journey_seq
        for leg in thisJourneySeq:
            if leg.mode == 'walk':
                continue
            else:
                trip_id = leg.trip_id
                if trip_id not in occupancy_dict:
                    occupancy_dict[trip_id] = {}

                route_id = int(trip_id.split('_')[0])
                start_id = leg.start_id
                stop_id = leg.stop_id
                stops_in_route = stops_dict.get(route_id)

                if stops_in_route is None:
                    raise Exception(f"route {route_id} not found")

                i = 0
                while i < len(stops_in_route)-1:
                    if stops_in_route[i] != start_id:
                        i += 1

                    else:
                        segment_start = stops_in_route[i]  # equal to start_id
                        segment_end = stops_in_route[i+1]
                        segment = (segment_start, segment_end)

                        while segment_end != stop_id:
                            if segment not in occupancy_dict[trip_id]:
                                occupancy_dict[trip_id][segment] = 1
                            else:
                                occupancy_dict[trip_id][segment] += 1

                            i += 1

                            if i >= len(stops_in_route):
                                raise Exception("invalid stop_seq")

                            segment_start = stops_in_route[i]
                            segment_end = stops_in_route[i+1]

                        else:
                            segment = (segment_start, segment_end)

                            if segment not in occupancy_dict[trip_id]:
                                occupancy_dict[trip_id][segment] = 1
                            else:
                                occupancy_dict[trip_id][segment] += 1

                            break

    return occupancy_dict

if __name__ == "__main__":
    # ## global variables ## #
    NETWORK_NAME = 'anaheim'
    MAX_TRANSFER = 4
    WALKING_FROM_SOURCE = 0
    CHANGE_TIME_SEC = 0
    PRINT_ITINERARY = 0
    CORES = 4

    stops_file, trips_file, stop_times_file, transfers_file,\
        stops_dict, stoptimes_dict, footpath_dict,\
        routes_by_stop_dict, idx_by_route_stop_dict = \
        read_testcase(f'./{NETWORK_NAME}')
    # ## global variables ## #

    beta = [-0.1, -2]
    od_mat = generate_od_matrix_with_time(100)
    selected_journeys = get_optimal_choices(od_mat, beta)

    print(len(selected_journeys))
    for j in selected_journeys:
        print(j)
        print("****\n")

    occupancy_dict = get_segment_occupancy(selected_journeys)
    for key in occupancy_dict.keys():
        print(key, occupancy_dict[key])
