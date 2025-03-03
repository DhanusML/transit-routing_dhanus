import numpy as np
import pandas as pd
from RAPTOR.std_raptor import raptor_dhanus
from miscellaneous_func import read_testcase
from tqdm import tqdm


def generate_OD_matrix(size: int) -> np.ndarray:
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

    od_mat = np.array([origin_ids, destination_ids],
                      dtype=np.int32).T
    return od_mat


def _gen_random_date_time(date='2022-06-10'):
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


def get_available_options(od_mat: np.ndarray) -> list:
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
    for origin, destination in tqdm(od_mat):
        time = _gen_random_date_time()
        output = raptor_dhanus(origin, destination, time, MAX_TRANSFER,
                               WALKING_FROM_SOURCE, CHANGE_TIME_SEC,
                               PRINT_ITINERARY, routes_by_stop_dict,
                               stops_dict, stoptimes_dict,
                               footpath_dict, idx_by_route_stop_dict)

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
    list_of_pareto_journeys = get_available_options(od_mat)
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

    stops_file, trips_file, stop_times_file, transfers_file,\
        stops_dict, stoptimes_dict, footpath_dict,\
        routes_by_stop_dict, idx_by_route_stop_dict = \
        read_testcase(f'./{NETWORK_NAME}')
    # ## global variables end # ##

    beta = [-0.1, -2]
    od_mat = generate_OD_matrix(10)
    selected_journeys = get_optimal_choices(od_mat, beta)

    print(len(selected_journeys))
    for j in selected_journeys:
        print(j)
        print("*****\n")

    occupancy_dict = get_segment_occupancy(selected_journeys)
    for key in occupancy_dict.keys():
        print(key, occupancy_dict[key])
