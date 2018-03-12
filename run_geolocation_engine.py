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
import sqlite3
import sys

from geolocation_engine import *
from geolocation_utils import validate_euis


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

    if len(eui_list):
        # Calculate device location estimate
        locate_device_from_db(args.db, eui_list[0], debug=args.debug)


if __name__ == "__main__":
    sys.exit(main())
