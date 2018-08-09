#!/usr/bin/python3

##############################################################################
#  Program:  run_experiments.py
# Language:  Python 3
#   Author:  Collin Crowell
#
# Purpose:  Run experiments against the geolocation_engine.py script.

##############################################################################

import argparse
import json
import os
import sqlite3
import sys
import re
from geolocation_engine import *
import numpy as np
import matplotlib.mlab as mlab
import matplotlib.pyplot as plt
from run_geolocation_engine import locate_device_from_db

from geolocation_utils import validate_euis, calc_distance, ALGORITHMS


######################################################################
# Read EUIs from a file
#
######################################################################
def read_file_euis(filename):
    eui_list = list()
    try:
        with open(filename) as f:
            for line in f:
                line = line.split(',')
                for eui in line:
                    eui = eui.strip()
                    match = re.match('[0-9A-Fa-f]{16}', eui)
                    if match:
                        eui_list.append(eui)
                    else:
                        print('Invalid EUI in file: ' + eui)

    except TypeError:
        print('Error parsing EUI file')
        eui_list = list()

    return eui_list


######################################################################
# get_real_location
#
######################################################################
def get_real_location(db_file, eui):
    lat, lng = 0, 0

    real_loc_query = "select top 1 devLat, devLng from Geo where devEui = '" + eui + "'"

    con = sqlite3.connect(db_file)

    with con:
        cur = con.cursor()
        cur.execute(real_loc_query)
        row = cur.fetchone()

        if row is not None:
            lat = row[0]
            lng = row[1]

    return lat, lng


######################################################################
# run_albany_experiment
#
######################################################################
def run_albany_experiment():
    albany_db_file = os.path.join('example_data', 'geo_n_albany.db')
    albany_devices_file = os.path.join('example_data', 'valid_albany_devices.txt')

    eui_list = read_file_euis(albany_devices_file)

    final_stats = dict()
    for eui in eui_list:
        # real_lat, real_lng = get_real_location(albany_db_file, eui)

        for alg in ALGORITHMS:
            calculated_locations = locate_device_from_db(albany_db_file, eui, algorithm=alg)

            total_dist = 0.0
            for loc in calculated_locations:
                distance = round(calc_distance(loc['lat'], loc['lng'], loc['actLat'], loc['actLng']), 1)
                total_dist += distance

            if not final_stats.get(alg):
                final_stats[alg] = {
                    'calculated_locs': len(calculated_locations),
                    'total_distance': total_dist
                }
            else:
                final_stats[alg]['calculated_locs'] += len(calculated_locations)
                final_stats[alg]['total_distance'] += total_dist

    avg_dist_dict = dict()
    for algorithm in final_stats:
        print('         Algorithm: ' + algorithm)
        print('Total Calculations: ' + str(final_stats[algorithm]['calculated_locs']))
        avg_dist = round((final_stats[algorithm]['total_distance'] / final_stats[algorithm]['calculated_locs']))
        avg_dist_dict[algorithm] = avg_dist

        print('  Average Distance: ' + str(avg_dist))

    performance = list()
    totals = list()
    names = 'Schau And Robinson', 'Friedlander', 'Foy', 'Schmidt', 'Centroid'
    objects = tuple(ALGORITHMS)

    for obj in objects:
        performance.append(avg_dist_dict[obj])
        totals.append(final_stats[obj]['calculated_locs'])
    y_pos = np.arange(len(objects))

    plt.bar(y_pos-0.15, performance, width=0.3, align='center', alpha=0.5)
    plt.xticks(y_pos, names)
    plt.ylabel('Avg. Distance (m)')
    plt.title('Albany Devices')
    plt2 = plt.twinx()
    plt2.bar(y_pos+0.15, totals, width=0.3, align='center', alpha=0.5, color='r')
    plt2.set_ylabel('Num Calculations', color='r')
    plt2.tick_params('y', colors='r')
    plt.savefig('all_albany_devs_t.png')

    plt.show()


###############################################################################
# parseArgs
#    -Parse arguments and provide help, description, etc
###############################################################################
def parse_args():
    desc = "Run experiments agaisnt the geolocation_engine.py script"

    parser = argparse.ArgumentParser(formatter_class=argparse.RawTextHelpFormatter,
                                     description=desc)

    group = parser.add_mutually_exclusive_group()

    group.add_argument('-a', '--albany',
                       help="Run albany test",
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

    if args.albany:
        run_albany_experiment()

    print(sep)


if __name__ == "__main__":
    sys.exit(main())