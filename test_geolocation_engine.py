#!/usr/bin/python3

##############################################################################
#  Program:  test_geolocation_engine.py
# Language:  Python 3
#   Author:  Collin Crowell
#
# Purpose: Test the geolocation_engine.py functionality.
#
##############################################################################

import sys
import threading
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

from geolocation_engine import *


class CSVData(object):
    """
    Class for storing CSV data
    """
    def __init__(self, dev_eui, real_lat, real_lng):
        self.dev_eui = dev_eui
        self.real_lat = real_lat
        self.real_lng = real_lng

        self.calc_lat = None
        self.calc_lng = None
        self.distance_error = None


class AtomicCounter(object):
        """
        Atomic counter class
        """

        def __init__(self, start=0):
            self._current = start
            self._lock = threading.Lock()

        def increment(self, inc_by=1):
            with self._lock:
                self._current += inc_by

        def get_value(self):
            with self._lock:  # are integer operations atomic?
                return self._current


###############################################################################
# Get distance between two coordinates (in meters)
#
###############################################################################
def calc_distance(lat1, lng1, lat2, lng2):
    # R is earth's radius
    distance = math.acos(math.sin(lat1 * math.pi / 180) * math.sin(lat2 * math.pi / 180)
                         + math.cos(lat1 * math.pi / 180) * math.cos(lat2 * math.pi / 180)
                         * math.cos(lng2 * math.pi / 180 - lng1 * math.pi / 180)) * R

    return round(distance, 2)


###############################################################################
# Test with calculated TDOA values to verify correctness
#
###############################################################################
def calculated_time_data_test(debug=False, visualize=False):
    print("Calculated time data test: " + str(datetime.now()) + '\n')

    # Known Location (43.054150, -70.781951) for known time values
    uplinks = list()

    # distance to dev = 8863  meters ToF = 0.000029563 sec   299792458 m/s (speed of light)
    uplinks.append(Uplink(time=29563, rssi=0, snr=0, bstn_eui='FF250C00010001A8',
                          bstn_lat=43.128362, bstn_lng=-70.742126))

    # distance to dev = 14730 meters ToF = 0.000049133 sec   299792458 m/s (speed of light)
    uplinks.append(Uplink(time=49133, rssi=0, snr=0, bstn_eui='FF250C00010001A9',
                          bstn_lat=42.951207, bstn_lng=-70.895935))

    # distance to dev = 14850 meters ToF = 0.000049534 sec   299792458 m/s (speed of light)
    uplinks.append(Uplink(time=49534, rssi=0, snr=0, bstn_eui='FF250C00010001A7',
                          bstn_lat=43.118840, bstn_lng=-70.941940))

    tx = Transaction(dev_eui='00000000FFFFFFFF', join_id=0, seq_no=0, datarate=0, uplinks=uplinks)

    location_engine = LocationEngine(transaction=tx, debug=debug, visualize=visualize)

    lat, lng = location_engine.compute_device_location()

    if visualize or debug:
        print("\n")

    print("Calculated Device Location Lat: " + str(lat) + " Lng: " + str(lng))
    print("    Actual Device Location Lat: 43.054150 Lng: -70.781951")
    print("\nDistance Error: " + str(round(calc_distance(lat, lng, 43.054150, -70.781951), 1)) + ' meters')

    print('\n' + "End calculated time data test: " + str(datetime.now()))


###############################################################################
# Test with calculated TDOA values to verify correctness
#
###############################################################################
def convergence_error_test(debug=False, visualize=False):
    print("Start convergence error test: " + str(datetime.now()) + '\n')


###############################################################################
# Test with calculated TDOA values to verify correctness
#
###############################################################################
def filter_algorithm_test(debug=False, visualize=False):
    print("Start filter algorithm test: " + str(datetime.now()) + '\n')

    # TODO Populate result dict with calculated lat,lng values
    results_dict = dict()

    min_sample_size = 2
    result_list = list()  # list of (dev_eui, lat, lng) tuples
    for key in results_dict:
        current_results_list = results_dict[key]

        while True:
            lat_sum = 0
            lng_sum = 0
            for result in current_results_list:
                lat_sum += result[0]
                lng_sum += result[1]

            lat_avg = lat_sum / len(current_results_list)
            lng_avg = lng_sum / len(current_results_list)

            current_result_length = len(current_results_list)

            if current_result_length <= min_sample_size:
                result_list.append((key, lat_avg, lng_avg))
                break

            worst_loc = 0
            worst_loc_i = None
            for i, result in enumerate(current_results_list):
                distance = calc_distance(lat_avg, lng_avg, result[0], result[1])
                if distance > worst_loc:
                    worst_loc = distance
                    worst_loc_i = i

            del current_results_list[worst_loc_i]

    print(result_list)


###############################################################################
# Test the speed of the location engine in python
#
###############################################################################
def performance_test():
    print("Start performance test: " + str(datetime.now()) + '\n')

    calculation_list = list()
    for i in range(0, 10000):
        # Known Location (43.054150, -70.781951) for known time values
        uplinks = list()

        # distance to dev = 8863  meters ToF = 0.000029563 sec
        uplinks.append(Uplink(time=29563, rssi=0, snr=0, bstn_eui='FF250C00010001A8',
                              bstn_lat=43.128362, bstn_lng=-70.742126))

        # distance to dev = 14730 meters ToF = 0.000049133 sec
        uplinks.append(Uplink(time=49133, rssi=0, snr=0, bstn_eui='FF250C00010001A9',
                              bstn_lat=42.951207, bstn_lng=-70.895935))

        # distance to dev = 14850 meters ToF = 0.000049534 sec
        uplinks.append(Uplink(time=49534, rssi=0, snr=0, bstn_eui='FF250C00010001A7',
                              bstn_lat=43.118840, bstn_lng=-70.941940))

        # Add error
        uplinks.append(Uplink(time=55534, rssi=0, snr=0, bstn_eui='FF250C00010001A7',
                              bstn_lat=43.178840, bstn_lng=-70.241940))

        tx = Transaction(dev_eui='00000000FFFFFFFF', join_id=0, seq_no=0, datarate=0, uplinks=uplinks)

        calculation_list.append(LocationEngine(transaction=tx, debug=False))

    def call_compute(location_engine):
        return location_engine.compute_device_location()

    print("Need real data for better test!!")
    print("<========= Futures Start : " + str(datetime.now()))
    with ThreadPoolExecutor(max_workers=2) as executor:
        future_location = {executor.submit(call_compute, location_engine): location_engine for location_engine in calculation_list}
        for future in as_completed(future_location):
            lat, lng = future.result()
            # print('lat: ' + str(lat) + ' lng: ' + str(lng))
    print("             Futures End : " + str(datetime.now()) + " =========>")

    print("<=========  Serial Start : " + str(datetime.now()))
    for location_engine in calculation_list:
        lat, lng = location_engine.compute_device_location()
        # print('lat: ' + str(lat) + ' lng: ' + str(lng))
    print("              Serial End : " + str(datetime.now()) + " =========>")

    print("\nEnd performance test: " + str(datetime.now()))


###############################################################################
# parseArgs
#    -Parse arguments and provide help, description, etc
###############################################################################
def parse_args():
    desc = "Test the geolocation_engine.py script"

    parser = argparse.ArgumentParser(formatter_class=argparse.RawTextHelpFormatter,
                                     description=desc)

    parser.add_argument('-d', '--debug',
                        help="Enable debug",
                        action="store_true")

    parser.add_argument('-v', '--vis',
                        help="Visualize the progress of the algorithm",
                        action="store_true")

    group = parser.add_mutually_exclusive_group()

    group.add_argument('-c', '--calc',
                        help="Run calculated test",
                        action="store_true")

    group.add_argument('-p', '--perf',
                        help="Run performance test",
                        action="store_true")

    group.add_argument('-e', '--err',
                       help="Run convergence error test",
                       action="store_true")

    group.add_argument('-f', '--filter',
                       help="Run filter algorithm test",
                       action="store_true")

    return parser.parse_args()


###############################################################################
# main()
#
###############################################################################
def main():
    args = parse_args()

    sep = '-' * 50
    print(sep)

    # Test against calculated data
    if args.calc:
        calculated_time_data_test(debug=args.debug, visualize=args.vis)

    # Performance test
    elif args.perf:
        performance_test()

    # Convergence error test
    elif args.err:
        convergence_error_test()

    # Filter algorithm test
    elif args.filter:
        filter_algorithm_test()

    print(sep)


if __name__ == "__main__":
    sys.exit(main())
