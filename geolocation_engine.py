#!/usr/bin/python3

##############################################################################
#  Program:  geolocation_engine.py
# Language:  Python 3
#   Author:  Collin Crowell
#
# Purpose: Geolocation solver for LoRa.
#
##############################################################################

import math
import numpy as np
from geolocation_utils import V, R, M, N


class Transaction(object):
    """
    Transaction sent by device
    """
    def __init__(self, dev_eui, join_id, seq_no, datarate, uplinks=list()):
        """
        :param dev_eui: str
        :param join_id: int
        :param seq_no: int
        :param datarate: int
        :param uplinks: list[Uplink]
        """
        self._dev_eui = dev_eui
        self._join_id = join_id
        self._seq_no = seq_no
        self._datarate = datarate
        self._uplinks = uplinks

    def get_dev_eui(self):
        """
        :return: str
        """
        return self._dev_eui

    def get_join_id(self):
        """
        :return: int
        """
        return self._join_id

    def get_seq_no(self):
        """
        :return: int
        """
        return self._seq_no

    def get_datarate(self):
        """
        :return: int
        """
        return self._datarate

    def get_uplinks(self):
        """
        :return: list[Uplink]
        """
        return self._uplinks

    def add_uplink(self, uplink):
        """
        Add an Uplink to the Transaction
        :param uplink: Uplink
        """
        self._uplinks.append(uplink)


class Uplink(object):
    """
    Uplink received by bstn
    NOTE: time is in nanoseconds
    """
    def __init__(self, bstn_eui, time, rssi, snr, bstn_lat, bstn_lng):
        """
        :param bstn_eui: str
        :param time: long
        :param rssi: float
        :param snr: float
        :param bstn_lat: float
        :param bstn_lng: float
        """
        self._bstn_eui = bstn_eui
        self._time = time
        self._rssi = rssi
        self._snr = snr
        self._bstn_lat = bstn_lat
        self._bstn_lng = bstn_lng
        self._bstn_x = None
        self._bstn_y = None

    def get_bstn_eui(self):
        """
        :return: str
        """
        return self._bstn_eui

    def get_time(self):
        """
        :return: long
        """
        return self._time

    def get_rssi(self):
        """
        :return: float
        """
        return self._rssi

    def get_snr(self):
        """
        :return: float
        """
        return self._snr

    def get_bstn_geolocation(self):
        """
        Tuple of lat and lng
        :return: (float, float)
        """
        return self._bstn_lat, self._bstn_lng

    def get_bstn_x(self):
        """
        :return: float
        """
        return self._bstn_x

    def get_bstn_y(self):
        """
        :return: float
        """
        return self._bstn_y

    def set_bstn_x(self, x):
        self._bstn_x = x

    def set_bstn_y(self, y):
        self._bstn_y = y

    def __str__(self):
        return str(self._time) + ' ' + self._bstn_eui + ' (' + str(self._bstn_lat) + ', ' + str(self._bstn_lng) + ')'


class LocationEngine(object):
    """
    Calculate the location of devices that are heard by three or more bstns with a single transaction. 
    Default time precision is nanoseconds.
    """
    def __init__(self, transaction, debug=False, microseconds=False, visualize=False):
        """
        :param transaction: Transaction
        :param debug: boolean
        :param microseconds: boolean
        :param visualize: boolean
        """
        self._transaction = transaction
        self._debug = debug
        self._visualize = visualize
        self._dev_x = None
        self._dev_y = None
        self._dev_lat = None
        self._dev_lng = None
        self._T = N
        if microseconds:
            self._T = M

        if len(self._transaction.get_uplinks()) < 3:
            raise RuntimeError("The LocationEngine requires 3 Uplinks per Transaction.")

        bstn_lat_sum = 0
        bstn_lng_sum = 0
        for uplink in self._transaction.get_uplinks():
            lat, lng = uplink.get_bstn_geolocation()
            bstn_lat_sum += lat
            bstn_lng_sum += lng


        '''self._transaction.get_uplinks().sort(key=lambda t: t.get_time(), reverse=True)

        last_uplink_time = 1
        for uplink in self._transaction.get_uplinks():
            if last_uplink < uplink.get_time():

        # 0.000006'''

        self._center_lat = bstn_lat_sum / len(self._transaction.get_uplinks())
        self._center_lng = bstn_lng_sum / len(self._transaction.get_uplinks())

        if self._debug:
            print('Center lat,lng: ' + str(self._center_lat) + ',' + str(self._center_lng))

    def get_dev_geolocation(self):
        """
        Tuple of lat and lng
        :return: (float, float)
        """
        return self._dev_lat, self._dev_lng

    def compute_device_location(self):
        """
        Compute the estimated location of the device
        :return: (float, float)
        """
        self.__convert_bstn_coordinates()

        self.__compute_dev_location()

        self.__convert_dev_coordinates()

        return self._dev_lat, self._dev_lng

    # HAVE NOT TRIED BUT SIMPLE SOLUTION MAY WORK
    #   https://en.wikipedia.org/wiki/Equirectangular_projection
    #   R = radius of the earth
    #   x = R * lng * cos(lat_c)
    #   y = R * lat
    def __convert_bstn_coordinates(self):
        lat_c = math.radians(self._center_lat)
        lng_c = math.radians(self._center_lng)

        for uplink in self._transaction.get_uplinks():
            lat, lng = uplink.get_bstn_geolocation()
            lat = math.radians(lat)
            lng = math.radians(lng)

            c = math.acos(math.sin(lat_c) * math.sin(lat) + math.cos(lat_c) * math.cos(lat) * math.cos(lng - lng_c))

            k = c / math.sin(c)

            x = k * math.cos(lat) * math.sin(lng - lng_c)
            y = k * (math.cos(lat_c) * math.sin(lat) - math.sin(lat_c) * math.cos(lat) * math.cos(lng - lng_c))

            uplink.set_bstn_x(x * R)
            uplink.set_bstn_y(y * R)

            if self._debug:
                print('Bstn ' + uplink.get_bstn_eui() + ' x,y: '
                      + str(uplink.get_bstn_x()) + ',' + str(uplink.get_bstn_y()))

    def __convert_dev_coordinates(self):
        if not self._dev_x and not self._dev_y:
            return

        x = self._dev_x / R
        y = self._dev_y / R

        if self._debug:
            print('x: ' + str(x))
            print('y: ' + str(y))

        lat_c = math.radians(self._center_lat)
        lng_c = math.radians(self._center_lng)

        c = math.sqrt(math.pow(x, 2) + math.pow(y, 2))

        self._dev_lat = math.degrees(math.asin(math.cos(c) * math.sin(lat_c) + (y * math.sin(c) * math.cos(lat_c)) / c))

        if lat_c == 90.0:
            self._dev_lng = math.degrees(lng_c + math.atan(-x / y))
        elif lat_c == -90.0:
            self._dev_lng = math.degrees(lng_c + math.atan(x / y))
        else:
            self._dev_lng = math.degrees(lng_c + math.atan((x * math.sin(c)) /
                                                           (c * math.cos(lat_c) * math.cos(c) -
                                                            y * math.sin(lat_c) * math.sin(c))))

    def __compute_dev_location(self):
        uplinks = self._transaction.get_uplinks()

        # Initial guess for location - Use first bstn's location
        x0 = uplinks[0].get_bstn_x() - 1000
        y0 = uplinks[0].get_bstn_y() + 1000

        # number of guesses
        guess = 25

        # size of step for each guess
        guess_by = 5000

        r_list = list()
        for uplink in uplinks:
            r_list.append(math.sqrt(math.pow(uplink.get_bstn_x() - x0, 2) + math.pow(uplink.get_bstn_y() - y0, 2)))

        h_list = list()
        for i in range(1, len(uplinks)):
            c = V * ((uplinks[i].get_time() - uplinks[0].get_time()) / self._T)
            h_list.append([c - (r_list[i] - r_list[0])])

        h = np.matrix(h_list)

        g_list = list()
        for i in range(1, len(uplinks)):
            g_list.append([((uplinks[0].get_bstn_x() - x0) / r_list[0] - (uplinks[i].get_bstn_x() - x0) / r_list[i]),
                           ((uplinks[0].get_bstn_y() - y0) / r_list[0] - (uplinks[i].get_bstn_y() - y0) / r_list[i])])

        g = np.matrix(g_list)

        if self._debug:
            print("Start Matrix h: \n" + str(h))
            print("Start Matrix g: \n" + str(g))

        i = 0
        j = 1

        inc_x = 0.0
        inc_y = 0.0
        err = 0

        while True:
            if err > 50:  # 15000
                x0 = None
                y0 = None
                break
            try:
                d = np.dot(np.dot(np.linalg.inv(np.dot(g.transpose(), g)), g.transpose()), h)

                dx = d[0, 0]
                dy = d[1, 0]
            except np.linalg.LinAlgError as e:
                if self._debug:
                    print("Exception! " + str(e))

                dx = 100
                dy = 100

                if i % 2 == 0:
                    inc_x -= guess_by * i
                    x0 = uplinks[0].get_bstn_x() + inc_x
                    y0 = uplinks[0].get_bstn_y() + inc_y
                else:
                    inc_x += guess_by * i
                    x0 = uplinks[0].get_bstn_x() + inc_x
                    y0 = uplinks[0].get_bstn_y() + inc_y

                i += 1

                if i > guess:
                    if j % 2 == 0:
                        inc_y -= guess_by * j
                        x0 = uplinks[0].get_bstn_x() + inc_x
                        y0 = uplinks[0].get_bstn_y() + inc_y
                    else:
                        inc_y += guess_by * j
                        x0 = uplinks[0].get_bstn_x() + inc_x
                        y0 = uplinks[0].get_bstn_y() + inc_y

                    i = 0
                    inc_x = 0.0
                    j += 1

                if j > guess:
                    if self._debug:
                        print("Max guesses reached!")
                    x0 = 0
                    y0 = 0
                    break

            x0 += dx
            y0 += dy

            if self._visualize:
                print('dx: ' + str(dx) + " dy: " + str(dy))

            if abs(dx) < 10 and abs(dy) < 10:
                if self._debug:
                    print("Location Engine Algorithm Completed Successfully")
                break

            try:
                r_list = list()
                for uplink in uplinks:
                    r_list.append(
                        math.sqrt(math.pow(uplink.get_bstn_x() - x0, 2) + math.pow(uplink.get_bstn_y() - y0, 2)))

                h_list = list()
                for i in range(1, len(uplinks)):
                    c = V * ((uplinks[i].get_time() - uplinks[0].get_time()) / self._T)
                    h_list.append([c - (r_list[i] - r_list[0])])

                h = np.matrix(h_list)

                g_list = list()
                for i in range(1, len(uplinks)):
                    g_list.append(
                        [((uplinks[0].get_bstn_x() - x0) / r_list[0] - (uplinks[i].get_bstn_x() - x0) / r_list[i]),
                         ((uplinks[0].get_bstn_y() - y0) / r_list[0] - (uplinks[i].get_bstn_y() - y0) / r_list[i])])

                g = np.matrix(g_list)

                if self._debug:
                    print("New Matrix h: \n" + str(h))
                    print("New Matrix g: \n" + str(g))

            except Exception as ex:
                print("Failed to update Matrices for Location Engine")
                print(ex)
                break

            err += 1

        if self._debug:
            print("Number of tries: " + str(err))

        self._dev_x = x0
        self._dev_y = y0
