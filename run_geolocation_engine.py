#!/usr/bin/python3

##############################################################################
#  Program:  run_geolocation_engine.py
# Language:  Python 3
#   Author:  Collin Crowell
#
# Purpose: Run the geolocation_engine.py script against real data.
#
##############################################################################

import argparse
import json
import os
import sqlite3
import sys

from geolocation_engine import *
from geolocation_utils import validate_euis, calc_distance


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
def locate_device_from_db(db_file, device_eui, gw_pin_data, debug=False):
    con = sqlite3.connect(db_file)
    cur = con.cursor()

    cur.execute("SELECT * FROM Geo WHERE devEui = '"+device_eui+"'ORDER BY uplinkId, time")

    rows = cur.fetchall()

    # Debug Tx Counters
    total_tx = 0  # Total transactions in db
    skipped_tx = 0  # Transactions not heard by three bstns
    cannot_compute_tx = 0  # Convergence error when geolocating end device

    last_time = None
    last_seq_no = None

    device_location_list = list()

    gw_pin_dict = dict()
    uplinks = list()
    for row in rows:
        time = int(row[3])
        seq_no = row[2]
        bstn_eui = row[1]
        bstn_lat = float(row[4])
        bstn_lng = float(row[5])

        real_dev_lat = float(row[6])
        real_dev_lng = float(row[7])

        # Invalid bstn location, skip
        if not bstn_lat or not bstn_lng:
            continue

        # No real location, skip
        if not real_dev_lat or not real_dev_lng:
            continue

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

                for uplink in uplinks:
                    if uplink.get_bstn_eui() not in gw_pin_dict:
                        gw_pin_dict[uplink.get_bstn_eui()] = {
                            "color": "red",
                            "lat": uplink.get_bstn_geolocation()[0],
                            "lng": uplink.get_bstn_geolocation()[1],
                            "zIndex": 50,
                            "name": uplink.get_bstn_eui()
                        }

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

        valid = True
        for ex_uplink in uplinks:
            if ex_uplink.get_bstn_geolocation()[0] == uplink.get_bstn_geolocation()[0] \
                    and ex_uplink.get_bstn_geolocation()[1] == uplink.get_bstn_geolocation()[1]:
                valid = False

        if valid:
            uplinks.append(uplink)
            last_time = time

    if debug:
        print("      Number of Transaction in DB: " + str(total_tx))
        print("Number of Valid Transaction in DB: " + str(total_tx - skipped_tx))
        print("Number of Successful Calculations: " + str(total_tx - skipped_tx - cannot_compute_tx))

    for eui in gw_pin_dict:
        gw_pin_data.append(gw_pin_dict[eui])

    return device_location_list


###############################################################################
# Calculate location estimate errors
#
###############################################################################
def calc_location_errors(locations):
    # Counters
    total_locs = 0
    fifty_or_less = 0
    fifty_to_one_hundred = 0
    one_hundred_to_two_hundred = 0
    two_hundred_to_five_hundred = 0
    five_hundred_or_more = 0

    for location in locations:
        calc_lat = location['lat']
        calc_lng = location['lng']
        real_lat = location['actLat']
        real_lng = location['actLng']

        if calc_lat and calc_lng and real_lat and real_lng:
            distance_error = calc_distance(lat1=calc_lat, lng1=calc_lng, lat2=real_lat, lng2=real_lng)

            total_locs += 1
            if distance_error <= 50:
                fifty_or_less += 1
            elif distance_error <= 100:
                fifty_to_one_hundred += 1
            elif distance_error <= 200:
                one_hundred_to_two_hundred += 1
            elif distance_error <= 500:
                two_hundred_to_five_hundred += 1
            else:
                five_hundred_or_more += 1

    print("Total number of locations: " + str(total_locs))
    per = round((fifty_or_less / total_locs) * 100, 2)
    print(str(per) + "% of location estimates were within 50 meters of the actual device location.")

    per = round((fifty_to_one_hundred / total_locs) * 100, 2)
    print(str(per) + "% of the location estimates were between 50 and 100 meters of the actual device location.")

    per = round((one_hundred_to_two_hundred / total_locs) * 100, 2)
    print(str(per) + "% of the location estimates were between 100 and 200 meters of the actual device location.")

    per = round((two_hundred_to_five_hundred / total_locs) * 100, 2)
    print(str(per) + "% of the location estimates were between 200 and 500 meters of the actual device location.")

    per = round((five_hundred_or_more / total_locs) * 100, 2)
    print(str(per) + "% of the location estimates were further than 500 meters of the actual device location.")


###############################################################################
# Filter calculated location estimates and determine error
#
###############################################################################
def filter_results_calc_error(locations):
    pin_data = list()
    min_sample_size = 10
    moving_dev_threshold = 0.0001

    # Copy locations list
    filt_locations = list(locations)

    # Check if moving GPS device
    first_lat = filt_locations[0]['actLat']
    first_lng = filt_locations[0]['actLng']

    moving = False
    start_weight = len(filt_locations)
    for location in filt_locations:
        if abs(first_lat - location['actLat']) > moving_dev_threshold:
            moving = True
            break
        if abs(first_lng - location['actLng']) > moving_dev_threshold:
            moving = True
            break

        # Add initial weights
        location['weight'] = start_weight

    if not moving:
        # Weight locations filter
        curr_weight = 1
        while True:
            lat_sum = 0
            lng_sum = 0
            weight_sum = 0
            for location in filt_locations:
                lat_sum += location['lat'] * location['weight']
                lng_sum += location['lng'] * location['weight']
                weight_sum += location['weight']

            lat_avg = lat_sum / float(weight_sum)
            lng_avg = lng_sum / float(weight_sum)

            current_result_length = len(filt_locations)

            if curr_weight >= current_result_length - min_sample_size:
                for location in filt_locations:
                    pin_data.append({
                        "color": "blue",
                        "lat": location['lat'],
                        "lng": location['lng'],
                        "zIndex": -1,
                        "name": 'Weight: ' + str(location['weight'])
                    })
                break

            worst_loc = 0
            worst_loc_i = None
            for i, location in enumerate(filt_locations):
                if location['weight'] < start_weight:
                    continue
                distance = calc_distance(lat_avg, lng_avg, location['lat'], location['lng'])
                if distance > worst_loc:
                    worst_loc = distance
                    worst_loc_i = i

            filt_locations[worst_loc_i]['weight'] = curr_weight
            curr_weight += 1

        pin_data.append({
            "color": "yellow",
            "lat": lat_avg,
            "lng": lng_avg,
            "zIndex": 100,
            "name": 'Calc'
        })

        pin_data.append({
            "color": "green",
            "lat": first_lat,
            "lng": first_lng,
            "zIndex": 100,
            "name": 'Actual'
        })

        distance_error = calc_distance(lat1=lat_avg, lng1=lng_avg, lat2=first_lat, lng2=first_lng)
        print('Post weighted filter distance error: ' + str(distance_error) + ' meters')

        # Remove locations filter
        while True:
            lat_sum = 0
            lng_sum = 0
            for location in filt_locations:
                lat_sum += location['lat']
                lng_sum += location['lng']

            lat_avg = lat_sum / len(filt_locations)
            lng_avg = lng_sum / len(filt_locations)

            current_result_length = len(filt_locations)

            if current_result_length <= min_sample_size:
                break

            worst_loc = 0
            worst_loc_i = None
            for i, location in enumerate(filt_locations):
                distance = calc_distance(lat_avg, lng_avg, location['lat'], location['lng'])
                if distance > worst_loc:
                    worst_loc = distance
                    worst_loc_i = i

            del filt_locations[worst_loc_i]

        distance_error = calc_distance(lat1=lat_avg, lng1=lng_avg, lat2=first_lat, lng2=first_lng)
        print('Post filter distance error: ' + str(distance_error) + ' meters')
    else:
        print('Moving device! Cannot perform filtering')

    return pin_data


###############################################################################
# Calc device locations
#
###############################################################################
def calc_dev_locations(device_eui, db_file):
    print('Device: ' + device_eui)
    # Calculate device location estimate
    gw_pin_data = list()
    locations = locate_device_from_db(db_file, device_eui, gw_pin_data)

    # Calculate errors
    if locations:
        calc_location_errors(locations)
        dev_pin_data = filter_results_calc_error(locations)

        locations = {'locations': dev_pin_data + gw_pin_data}

        dir_path = os.path.dirname(os.path.realpath(__file__))
        pin_data_path = [dir_path, 'build', 'pinData.json']
        pin_data_file = os.path.join(*pin_data_path)
        with open(pin_data_file, 'w') as outfile:
            json.dump(locations, outfile, indent=1)
    else:
        print('Cannot compute location errors!')


###############################################################################
# parseArgs
#    -Parse arguments and provide help, description, etc
###############################################################################
def parse_args():
    desc = "Test the geolocation_engine.py script"

    parser = argparse.ArgumentParser(formatter_class=argparse.RawTextHelpFormatter,
                                     description=desc)

    parser.add_argument('-e', '--eui',
                        help="Device EUI",
                        required=True)

    parser.add_argument('-d', '--db',
                        help="DB file",
                        default="geo.db")

    parser.add_argument('-v', '--vis',
                        help="Visualize the progress of the algorithm",
                        action="store_true")

    parser.add_argument('--debug',
                        help="Enable debug",
                        action="store_true")

    return parser.parse_args()


###############################################################################
# main()
#
###############################################################################
def main():
    args = parse_args()

    eui_list = validate_euis(args.eui)

    for eui in eui_list:
        print('Device: ' + eui)
        # Calculate device location estimate
        gw_pin_data = list()
        locations = locate_device_from_db(args.db, eui, gw_pin_data, debug=args.debug)

        # Calculate errors
        if locations:
            calc_location_errors(locations)
            dev_pin_data = filter_results_calc_error(locations)

            locations = {'locations': dev_pin_data + gw_pin_data}

            dir_path = os.path.dirname(os.path.realpath(__file__))
            pin_data_path = [dir_path, 'build', 'pinData.json']
            pin_data_file = os.path.join(*pin_data_path)
            with open(pin_data_file, 'w') as outfile:
                json.dump(locations, outfile, indent=1)
        else:
            print('Cannot compute location errors!')


if __name__ == "__main__":
    sys.exit(main())
