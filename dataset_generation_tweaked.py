import numpy as np
import pandas as pd
from RAPTOR.std_raptor import raptor
from miscellaneous_func import *


def get_outputs(origin, destination, time):
    output = raptor(origin, destination, time, 10, 1, 0, 1)

def main():
    path = './GTFS/anaheim/'
    data = pd.read_csv(path+'stops.txt')
    stop_ids = data['stop_id']

    start_indices = np.random.choice(np.arange(len(data)), size=N)
    stop_indices = np.random.choice(np.arange(len(data)), size=N)

    origin_ids = list(stop_ids.loc[start_indices])
    destination_ids = list(stop_ids.loc[stop_indices])

    departure_date = '2022-06-10'
    time_array = []

    for i in range(N):
        time = ':'.join(
            [
                str(np.random.randint(0, 24)).zfill(2), # hour
                str(np.random.randint(0,60)).zfill(2), # minute
                '00' # seconds
            ]
        )
        time = departure_date + ' ' + time
        time_array.append(pd.to_datetime(time))

    print(len(origin_ids), len(destination_ids), len(time_array))

    for i in range(5):
        print(origin_ids[i], destination_ids[i], time_array[i], sep=', ',end='\n')

    with open('./new_data', 'w') as f:
        header = ("origin,destination,departure_time,"
                  "transfers,walk_time,wait_time,ovtt,ivtt\n")
        f.write(header)

        for i in range(N):
            origin = origin_ids[i]
            destination = destination_ids[i]
            time = time_array[i]

            output = raptor(origin, destination, time, MAX_TRANSFER,
                            WALKING_FROM_SOURCE, CHANGE_TIME_SEC,
                            PRINT_ITINERARY, routes_by_stop_dict,
                            stops_dict, stoptimes_dict, footpath_dict,
                            idx_by_route_stop_dict)

            if output[0] is not None:
                output_tt = output[0]['tt']
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




if __name__ == "__main__":
    N = 10
    MAX_TRANSFER = 10
    WALKING_FROM_SOURCE = 1
    CHANGE_TIME_SEC = 0
    PRINT_ITINERARY = 0

    stops_file, trips_file, stop_times_file, transfers_file,\
        stops_dict, stoptimes_dict, footpath_dict,\
        routes_by_stop_dict, idx_by_route_stop_dict = \
        read_testcase('./anaheim')

    main()
