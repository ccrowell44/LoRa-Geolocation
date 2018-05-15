#!/usr/bin/python3

import argparse
import csv
import json
import os
import sqlite3
import sys


###############################################################################
# Load end device uplink data into a SQLite db file.
#
###############################################################################
def load_location_data(input_file, db_name, dev_loc_dict):
    print('Loading file ' + input_file + ' into DB ' + db_name + '...')

    with open(input_file, 'r', newline='', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)

        con = sqlite3.connect(db_name)

        with con:
            cur = con.cursor()
            #
            cur.execute("CREATE TABLE IF NOT EXISTS Geo(devEui TEXT, gwEui TEXT, uplinkId INT, time INT, "
                        "gwLat REAL, gwLng REAL, devLat REAL, devLng REAL)")

            for row in reader:
                dev_eui = row.get('devEui', '')
                gw_eui = row.get('gwEui', '')
                seq_no = row.get('seqno', '-1')
                time = row.get('ftsTmstClr', '-1')
                gw_lat = row.get('gwLat')
                gw_lng = row.get('gwLng')
                dev_lat = row.get('devLat')
                dev_lng = row.get('devLng')

                # Handle None or empty strings
                if not gw_lat:
                    gw_lat = '0'
                if not gw_lng:
                    gw_lng = '0'
                if not dev_lat:
                    dev_lat = '0'
                if not dev_lng:
                    dev_lng = '0'

                # Not a GPS enabled device
                if dev_lat == '0' and dev_lng == '0':
                    if dev_loc_dict.get(dev_eui):
                        dev_lat = str(dev_loc_dict[dev_eui]['lat'])
                        dev_lng = str(dev_loc_dict[dev_eui]['lng'])

                cur.execute("INSERT INTO Geo VALUES('"+dev_eui+"','"+gw_eui+"',"+seq_no+","+time +
                            ","+gw_lat+","+gw_lng+","+dev_lat+","+dev_lng+")")


###############################################################################
# parseArgs
#    -Parse arguments and provide help, description, etc
###############################################################################
def parse_args():
    desc = 'Load end device uplink data from a csv file into a SQLite db.'

    parser = argparse.ArgumentParser(formatter_class=argparse.RawTextHelpFormatter,
                                     description=desc)

    parser.add_argument('-n', '--name',
                        help='Name of the local db file.', default='geo.db')

    parser.add_argument('-l', '--loc',
                        help='Name of the device to location JSON file.')

    parser.add_argument('-c', '--csv', required=True,
                        help='Path to the csv file.')

    return parser.parse_args()


###############################################################################
# main()
#
###############################################################################
def main():
    args = parse_args()

    # Check if csv file exists
    if not os.path.exists(args.csv):
        print('File: ' + args.csv + ' does not exist')
        sys.exit(1)

    # Check if dev loc json file exists
    dev_loc_dict = dict()
    if args.loc:
        if not os.path.exists(args.loc):
            print('File: ' + args.loc + ' does not exist')
            sys.exit(1)
        else:
            dev_loc_dict = json.load(open(args.loc))

    load_location_data(input_file=args.csv, db_name=args.name, dev_loc_dict=dev_loc_dict)


if __name__ == "__main__":
    sys.exit(main())
