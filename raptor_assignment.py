import numpy as np
import pandas as pd
from RAPTOR.std_raptor import raptor_dhanus
from miscellaneous_func import *
from tqdm import tqdm
import time


def generate_OD_matrix(size):
    data = pd.read_csv(f'./GTFS/{NETWORK_NAME}/stops.txt')
    stop_ids = data['stop_id']

    start_indices = np.random.choice(np.arange(len(data)), size=size)
    stop_indices = np.random.choice(np.arange(len(data)), size=size)

    origin_ids = list(stop_ids.loc[start_indices])
    destination_ids = list(stop_ids.loc[stop_indices])

    od_mat = np.array([origin_ids, destination_ids],
                      dtype=np.int32).T
    # print(od_mat)
    return od_mat


def _gen_random_date_time(date='2022-06-10'):
    departure_date = date
    time = ':'.join(
        [
            str(np.random.randint(0,24)).zfill(2), # hour
            str(np.random.randint(0, 60)).zfill(2), # minute
            '00' # seconds
        ]
    )

    time = pd.to_datetime(departure_date + ' ' + time)
    return time


def get_available_options(od_mat):
    pareto_journeys = []
    for origin, destination in od_mat:
        time = _gen_random_date_time()
        output = raptor_dhanus(origin, destination, time, MAX_TRANSFER,
                               WALKING_FROM_SOURCE, CHANGE_TIME_SEC,
                               PRINT_ITINERARY, routes_by_stop_dict,
                               stops_dict, stoptimes_dict,
                               footpath_dict, idx_by_route_stop_dict)

        if output[0] is not None:
            choices = output[0]['journeys']
            pareto_journeys.append(choices)

    for x in pareto_journeys:
        #print(x[0])
        pass
    return pareto_journeys


def _make_choice(util_list):
    if len(util_list) == 1:
        return 0

    prob_list = np.array(util_list)
    print("1", prob_list)
    prob_list = np.exp(prob_list)
    print("2", prob_list)
    prob_list = prob_list/sum(prob_list)
    print("3", prob_list)

    cumul_probs = np.zeros(len(prob_list)+1)
    for i in range(1, len(prob_list)+1):
        cumul_probs[i] = sum(prob_list[:i])

    print("cumul", cumul_probs)
    rand_fl = np.random.random()
    print("rnadom", rand_fl)

    for i in range(len(cumul_probs)-1):
        if cumul_probs[i]<=rand_fl and rand_fl<=cumul_probs[i+1]:
            print(f"selection={i}, {rand_fl}")

            return i

    print("not found")
    return 0


def get_optimal_choices(od_mat, beta):
    bT, bN = beta[0], beta[1]

    list_of_pareto_journeys = get_available_options(od_mat)
    selected_journeys = []

    for pareto_journeys in list_of_pareto_journeys:
        util_list = []
        for journey in pareto_journeys:
            travel_time = journey.get_ovtt() + journey.get_ivtt()
            num_transfers = journey.transfers
            u = bT*travel_time/3600 + bN*num_transfers # travelteim hrs
            util_list.append(u)

        choice = _make_choice(util_list)
        selected_journeys.append(pareto_journeys[choice])

    return selected_journeys


if __name__ == "__main__":

    ### global variables ###
    NETWORK_NAME = 'anaheim'
    MAX_TRANSFER = 4
    WALKING_FROM_SOURCE = 1
    CHANGE_TIME_SEC = 0
    PRINT_ITINERARY = 0

    stops_file, trips_file, stop_times_file, transfers_file,\
        stops_dict, stoptimes_dict, footpath_dict,\
        routes_by_stop_dict, idx_by_route_stop_dict = \
        read_testcase(f'./{NETWORK_NAME}')
    ### global variables end ###

    beta = [-0.1, -2]
    od_mat = generate_OD_matrix(10)
    selected_journeys = get_optimal_choices(od_mat, beta)
    print(len(selected_journeys))
