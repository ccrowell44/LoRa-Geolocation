#!/usr/bin/python3

import argparse
import csv
import json
import os
import sqlite3
import sys
from configparser import NoSectionError, NoOptionError, RawConfigParser
from datetime import datetime

import requests
from requests.auth import HTTPBasicAuth

SEC_DATA_MINE  = 'Data Mine Variables'   # Section for data mining configurations
DEV_LOC_URL  = 'DEV_LOC_URL'
BSTN_LOC_URL = 'BSTN_LOC_URL'
QUERY_URL    = 'QUERY_URL'
USERNAME     = 'USERNAME'
PASSWORD     = 'PASSWORD'


###############################################################################
# Get all the locations of the deployed base stations
#
###############################################################################
def get_all_bstn_locations(config):
    get_bstn_loc_url = config.get(SEC_DATA_MINE, BSTN_LOC_URL)

    r = requests.get(get_bstn_loc_url, auth=HTTPBasicAuth(
        config.get(SEC_DATA_MINE, USERNAME), config.get(SEC_DATA_MINE, PASSWORD)))

    bstn_location_dict = dict()
    json_data = json.loads(r.text)
    json_data = json_data['data']

    for obj in json_data:
        bstn_eui = obj['bstnEui']

        bstn_location_dict[bstn_eui] = {
            'lat': obj['lat'],
            'lng': obj['lng']
        }

    return bstn_location_dict


###############################################################################
# Determine the known location of the devices in the file.
#
###############################################################################
def gen_dev_loc_dict(input_file, config):
    dev_loc_dict = dict()

    with open(input_file, 'r') as csv_file:
        dev_data = csv.reader(csv_file)

        dev_loc_url = config.get(SEC_DATA_MINE, DEV_LOC_URL)
        for row in dev_data:
            for dev_eui in row:
                get_dev_loc_url = dev_loc_url + '?filterField=devEui&filterVal=' + dev_eui + '&fieldNames=lngLatLoc'

                r = requests.get(get_dev_loc_url, auth=HTTPBasicAuth(
                    config.get(SEC_DATA_MINE, USERNAME), config.get(SEC_DATA_MINE, PASSWORD)))

                ret_json = json.loads(r.text)

                # Skip devices without known locations
                if ret_json.get('data') and len(ret_json['data']) and len(ret_json['data'][0]):
                    lat = ret_json['data'][0][0][1]
                    lng = ret_json['data'][0][0][0]

                    if lat or lng:
                        dev_loc_dict[dev_eui] = {
                            'lat': lat,
                            'lng': lng
                        }

    return dev_loc_dict


###############################################################################
# Load end device uplink data into a SQLite db file.
#
###############################################################################
def load_uplink_data(db_name, dev_loc_dict, bstn_loc_dict, config):
    # Write data to SQL db
    con = sqlite3.connect(db_name)

    with con:
        cur = con.cursor()

        cur.execute("CREATE TABLE IF NOT EXISTS Geo(devEui TEXT, gwEui TEXT, uplinkId TEXT, "
                    "time INT, gwLat REAL, gwLng REAL, devLat REAL, devLng REAL, PRIMARY KEY (gwEui, devEui, uplinkId))")

        # cur.execute("CREATE INDEX IF NOT EXISTS uplinkIdIndex ON GeoMillis (uplinkId);")

        temp_cnt = 0
        query_url = config.get(SEC_DATA_MINE, QUERY_URL)
        for dev_eui, loc_data in dev_loc_dict.items():
            print('Current Cnt: ' + str(temp_cnt))
            temp_cnt += 1
            # Perform queries
            q = "select time, gwtime, deveui, bstneui, dr, joinid, rssi, seqno , snr, rcvdlate from " \
                "evtlora_rp.evtlora where time > now() - "+str(144)+"h and freq < 920 and joinid >= 1 and deveui = '"+dev_eui+"'"

            r = requests.post(query_url, data=q, auth=HTTPBasicAuth(
                config.get(SEC_DATA_MINE, USERNAME), config.get(SEC_DATA_MINE, PASSWORD)))

            json_array = json.loads(r.text)

            if json_array:
                data_dict = dict()
                for data in json_array:
                    # Only add uplinks with known gateway locations
                    if bstn_loc_dict.get(data['bstneui']) is None:
                        continue

                    # This shouldn't matter. Back haul issue to Nwk Svr.
                    # if not int(float(data['rcvdlate'])):

                    # Create the uplink unique identifier
                    uplink_id = str(int(float(data['joinid']))) + ":" + str(int(float(data['seqno'])))

                    dict_entry = data_dict.get(uplink_id)
                    if dict_entry:
                        # Skip uplinks that are too slow
                        add_uplink = True
                        for uplink in dict_entry:
                            if abs(float(uplink['gwtime']) - float(data['gwtime'])) > 350000:
                                add_uplink = False

                        if add_uplink:
                            dict_entry.append(data)
                    else:
                        data_dict[uplink_id] = [data]

                for uplink_id, uplinks in data_dict.items():
                    # Skip uplinks that cannot be used to locate the device
                    if len(uplinks) < 3:
                        continue

                    for uplink in uplinks:
                        gw_eui = uplink['bstneui']
                        time = str(uplink['gwtime'])
                        gw_lat = str(bstn_loc_dict[uplink['bstneui']]['lat'])
                        gw_lng = str(bstn_loc_dict[uplink['bstneui']]['lng'])
                        dev_lat = str(dev_loc_dict[dev_eui]['lat'])
                        dev_lng = str(dev_loc_dict[dev_eui]['lng'])

                        try:
                            cur.execute("INSERT INTO Geo VALUES('" + dev_eui + "','" + gw_eui + "','" +
                                        uplink_id + "'," + time + "," + gw_lat + "," + gw_lng + "," +
                                        dev_lat + "," + dev_lng + ")")
                        except sqlite3.IntegrityError:
                            pass


            else:
                print('ERROR: Request failed for device EUI: ' + dev_eui)


##########################################################################
# Get and validate config file
#
###########################################################################
def get_config_file(config_file_name):
    """
    Loads the config file and check that it contains the required fields
    :param config_file_name: Name of the config file
    :return: The config file if valid
    """

    config = RawConfigParser()

    valid_file = False
    try:
        config.read(config_file_name)
        valid_file = True
    except Exception as e:
        print('Exception: ' + str(e))
        print('Unable to read config file: ' + config_file_name)
        config = None

    if valid_file:
        try:
            if not config.get(SEC_DATA_MINE, DEV_LOC_URL, fallback=None):
                print('Missing ' + DEV_LOC_URL + ' value in config')
                config = None
            elif not config.get(SEC_DATA_MINE, BSTN_LOC_URL, fallback=None):
                print('Missing ' + BSTN_LOC_URL + ' value in config')
                config = None
            elif not config.get(SEC_DATA_MINE, QUERY_URL, fallback=None):
                print('Missing ' + QUERY_URL + ' value in config')
                config = None
        except NoSectionError or NoOptionError:
            print('Invalid config file: ' + config_file_name)
            config = None

    return config


###############################################################################
# parseArgs
#    -Parse arguments and provide help, description, etc
###############################################################################
def parse_args():
    desc = 'Load end device uplink data into a sql db file.'

    parser = argparse.ArgumentParser(formatter_class=argparse.RawTextHelpFormatter,
                                     description=desc)

    parser.add_argument('-n', '--name',
                        help='Name of the local db file.', default='geo_micro.db')

    parser.add_argument('-f', '--file', required=True,
                        help='Path to file with comma or line separated device EUIs.')

    return parser.parse_args()


###############################################################################
# main()
#
###############################################################################
def main():
    args = parse_args()

    # Check if csv file exists
    if not os.path.exists(args.file):
        print('File: ' + args.file + ' does not exist')
        sys.exit(1)

    config = get_config_file(config_file_name='app.cfg')

    if config:
        print('Finding known locations of devices...')
        dev_loc_dict = gen_dev_loc_dict(input_file=args.file, config=config)

        print('Finding known locations of gateways...')
        bstn_loc_dict = get_all_bstn_locations(config=config)

        print("Start Time: " + str(datetime.now()))

        print('Loading device uplink data...')
        load_uplink_data(db_name=args.name, dev_loc_dict=dev_loc_dict, bstn_loc_dict=bstn_loc_dict, config=config)

        print("End Time: " + str(datetime.now()))


if __name__ == "__main__":
    sys.exit(main())
