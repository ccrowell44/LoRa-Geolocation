#!/usr/bin/python3

##############################################################################
#  Program:  geolocation_utils.py
# Language:  Python 3
#   Author:  Collin Crowell
#
# Purpose: Util functions for the geolocation engine.
#
##############################################################################

import math
import re

# speed of light through air in meters / second
V = 299792458

# earth radius in meters
R = 6371000

# Microseconds in second
M = 1000000.0

# Nanoseconds in second
N = 1000000000.0

# Supported algorithms
ALGORITHMS = ['schauAndRobinson3', 'friedlander', 'taylorSeries', 'schmidt', 'centroid']


###############################################################################
# Get distance between two coordinates (in meters)
#
###############################################################################
def calc_distance(lat1, lng1, lat2, lng2):
    """
    Get distance between two coordinates (in meters)
    :param lat1: lat of coordinate 1
    :param lng1: lng of coordinate 1
    :param lat2: lat of coordinate 2
    :param lng2: lng of coordinate 2
    :return: distance in meters
    """
    # R is earth's radius
    distance = math.acos(math.sin(lat1 * math.pi / 180) * math.sin(lat2 * math.pi / 180)
                         + math.cos(lat1 * math.pi / 180) * math.cos(lat2 * math.pi / 180)
                         * math.cos(lng2 * math.pi / 180 - lng1 * math.pi / 180)) * R

    return round(distance, 2)


######################################################################
# Convert comma separated list of EUIs into a list.
# Only add EUIs if valid
######################################################################
def validate_euis(comma_separated_euis):
    """
    Convert comma separated String of EUIs into a List. Only valid EUIs are added to list.
    :param comma_separated_euis: String with comma separated EUIs
    :return: list of valid email addresses
    """

    eui_list = list()
    euis = comma_separated_euis.split(',')
    for eui in euis:
        eui = eui.strip()
        match = re.match('[0-9A-Fa-f]{16}', eui)
        if match:
            eui_list.append(eui)
        else:
            print('Bad Syntax: ' + eui)

    return eui_list
