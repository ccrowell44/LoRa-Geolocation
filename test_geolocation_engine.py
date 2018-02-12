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
import sqlite3
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

from geolocation_engine import *


###############################################################################
# Locate a device from a SQLite db file.
#
# Return JSON Array of estimated locations:
# [
#    {
#       "lat":43.128362,
#       "lng":-70.742126
#    },
#    {
#       "lat":43.128352,
#       "lng":-70.742116
#    }
# ]
###############################################################################
def locate_device_from_db(db_file, device_eui, debug=False):
    con = sqlite3.connect(db_file)
    cur = con.cursor()

    cur.execute("SELECT * FROM Geo WHERE devEui = '"+device_eui+"'ORDER BY seqNo, time")

    rows = cur.fetchall()

    # Debug Tx Counters
    total_tx = 0  # Total transactions in db
    skipped_tx = 0  # Transactions not heard by three bstns
    cannot_compute_tx = 0  # Convergence error when geolocating end device

    last_time = None
    last_seq_no = None

    device_location_list = list()

    uplinks = list()
    for row in rows:
        time = int(row[3])
        seq_no = int(row[2])
        bstn_eui = row[1]
        bstn_lat = float(row[4])
        bstn_lng = float(row[5])

        real_dev_lat = float(row[6])
        real_dev_lng = float(row[7])

        if last_time is None:
            last_time = time

        if last_seq_no is None:
            last_seq_no = seq_no

        uplink = Uplink(time=time, rssi=0, snr=0, bstn_eui=bstn_eui, bstn_lat=bstn_lat, bstn_lng=bstn_lng)

        # New transaction, check if last transaction is valid for geolocation
        if seq_no != last_seq_no:
            total_tx += 1

            if len(uplinks) >= 3:
                if debug:
                    print('-'*20 + '\nSeqNo: ' + str(last_seq_no))
                    for up in uplinks:
                        print(str(up.get_time()) + ' ' + up.get_bstn_eui() + ' ' + str(up.get_bstn_geolocation()))
                    print('-' * 20)

                tx = Transaction(dev_eui=device_eui, join_id=0, seq_no=last_seq_no, datarate=0, uplinks=uplinks)

                location_engine = LocationEngine(transaction=tx, debug=False)
                calc_lat, calc_lng = location_engine.compute_device_location()

                if not calc_lat or not calc_lng:
                    cannot_compute_tx += 1
                else:
                    location = {
                        'lat': calc_lat,
                        'lng': calc_lng
                    }
                    if real_dev_lat and real_dev_lng:
                        location['actLat'] = real_dev_lat
                        location['actLng'] = real_dev_lng

                    device_location_list.append(location)

            else:
                skipped_tx += 1

            last_seq_no = seq_no
            uplinks = list()

        elif abs(time - last_time) > 200000:  # Filter out old (invalid) uplinks
            last_time = time
            continue

        uplinks.append(uplink)
        last_time = time

    if debug:
        print("      Number of Transaction in DB: " + str(total_tx))
        print("Number of Valid Transaction in DB: " + str(total_tx - skipped_tx))
        print("Number of Successful Calculations: " + str(total_tx - skipped_tx - cannot_compute_tx))

    return device_location_list


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
    print("Not implemented...")


###############################################################################
# Test with calculated TDOA values to verify correctness
#
###############################################################################
def filter_algorithm_test(db_namedebug=False, visualize=False):
    print("Start filter algorithm test: " + str(datetime.now()) + '\n')
    print("Not implemented...")

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

    print("Futures Start: " + str(datetime.now()))
    with ThreadPoolExecutor(max_workers=2) as executor:
        future_location = {executor.submit(call_compute, location_engine): location_engine for location_engine in calculation_list}
        for future in as_completed(future_location):
            lat, lng = future.result()
            # print('lat: ' + str(lat) + ' lng: ' + str(lng))
    print("  Futures End: " + str(datetime.now()))

    print("-"*30)

    print("Serial Start : " + str(datetime.now()))
    for location_engine in calculation_list:
        lat, lng = location_engine.compute_device_location()
        # print('lat: ' + str(lat) + ' lng: ' + str(lng))
    print("  Serial End : " + str(datetime.now()))

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
        convergence_error_test(debug=args.debug, visualize=args.vis)

    # Filter algorithm test
    elif args.filter:
        filter_algorithm_test(debug=args.debug, visualize=args.vis)

    print(sep)


if __name__ == "__main__":
    sys.exit(main())
