import numpy as np
import pandas as pd
from RAPTOR.std_raptor import raptor_dhanus
from miscellaneous_func import *
from tqdm import tqdm
import time

"""
                README
               --------

Before running:
    * Copy `journey_rep.py' from `Internship_2022_2/Dhanus/' to
      `transit-routing/RAPTOR/'
    * Replace `transit-routing/RAPTOR/std_raptor' with
      `Internship_2022_2/Dhanus/std_raptor_dhanus.py'
    * Replace `transit-routing/RAPTOR/raptor_functions.py' with
      `Internship_2022_2/Dhanus/raptor_function_dhanus.py'
      (don't forget to rename the files).
    * Copy this file to `transit-routing/' before running.

"""

def main():
    path = './GTFS/anaheim/'
    #path = './GTFS/bangalore/'
    data = pd.read_csv(path+'stops.txt')
    stop_ids = data['stop_id']

    start_indices = np.random.choice(np.arange(len(data)), size=N)
    stop_indices = np.random.choice(np.arange(len(data)), size=N)

    origin_ids = list(stop_ids.loc[start_indices])
    destination_ids = list(stop_ids.loc[stop_indices])

    #departure_date = '2022-06-10'
    departure_date = '2018-06-10' # nothing special about this date!
    time_array = []

    for i in range(N):
        time = ':'.join(
            [
                str(np.random.randint(0, 24)).zfill(2), # hour
                str(np.random.randint(0,60)).zfill(2), # minute
                '00' # seconds always 0
            ]
        )
        time = departure_date + ' ' + time
        time_array.append(pd.to_datetime(time))

    with open('./travel_time_data_mini.txt', 'w') as f:
        header = ("origin,destination,departure_time,"
                  "transfers,walk_time,wait_time,ovtt,ivtt\n")
        f.write(header)

        for i in tqdm(range(N)):
            origin = origin_ids[i]
            destination = destination_ids[i]
            time = time_array[i]

            output = raptor_dhanus(origin, destination, time, MAX_TRANSFER,
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
    N = 5
    MAX_TRANSFER = 4
    WALKING_FROM_SOURCE = 1
    CHANGE_TIME_SEC = 0
    PRINT_ITINERARY = 0

    stops_file, trips_file, stop_times_file, transfers_file,\
        stops_dict, stoptimes_dict, footpath_dict,\
        routes_by_stop_dict, idx_by_route_stop_dict = \
        read_testcase('./anaheim')
        #read_testcase('./bangalore')

    _start_time = time.time()
    main()
    _end_time = time.time()
    print("generated data in `travel_time_data.txt'")
    print(f"time taken: {_end_time-_start_time} seconds")
