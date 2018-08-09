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

    def compute_device_location(self, calculation='taylorSeries'):
        """
        Compute the estimated location of the device
        :return: (float, float)
        """
        self.__convert_bstn_coordinates()

        if calculation == 'taylorSeries':
            self.__taylor_series_expansion()
        elif calculation == 'smithAndAbel':
            self.__smith_and_abel_algorithm()
        elif calculation == 'schmidt':
            self.__schmidt_algorithm()
        elif calculation == 'friedlander':
            self.__friedlander_algorithm()
        elif calculation == 'friedlander3':
            self.__friedlander_algorithm3()
        elif calculation == 'schauAndRobinson':
            self.__schau_and_robinson()
        elif calculation == 'schauAndRobinson3':
            self.__schau_and_robinson3()
        elif calculation == 'centroid':
            self.__simple_centroid()

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

    def __taylor_series_expansion(self):
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

    def __smith_and_abel_algorithm(self):
        uplinks = self._transaction.get_uplinks()

        # Create reference bstn at 0,0
        x0 = uplinks[0].get_bstn_x()
        y0 = uplinks[0].get_bstn_y()

        x0 = x0 * -1
        y0 = y0 * -1

        print(x0, y0)

        for uplink in uplinks:
            uplink.set_bstn_x(uplink.get_bstn_x() + x0)
            uplink.set_bstn_y(uplink.get_bstn_y() + y0)
            print(str(uplink.get_bstn_x()) + ', ' + str(uplink.get_bstn_y()))

        # Distance from source to sensor_1
        Rs = V * (uplinks[0].get_time()  / self._T)
        print('Rs: ' + str(Rs))

        # Distance from source to sensor_2 minus Rs
        d21 = V * (uplinks[1].get_time()  / self._T) - Rs
        print('d21: ' + str(d21))

        # Distance from source to sensor_3 minus Rs
        d31 = V * (uplinks[2].get_time()  / self._T) - Rs
        print('d31: ' + str(d31))

        # Distance from sensor_2 to sensor_1
        R2 = math.sqrt(math.pow((uplinks[1].get_bstn_x() - uplinks[0].get_bstn_x()), 2) + math.pow((uplinks[1].get_bstn_y() - uplinks[0].get_bstn_y()), 2))
        print('R2: ' + str(R2))

        # Distance from sensor_3 to sensor_1
        R3 = math.sqrt(math.pow((uplinks[2].get_bstn_x() - uplinks[0].get_bstn_x()), 2) + math.pow((uplinks[2].get_bstn_y() - uplinks[0].get_bstn_y()), 2))

        error2 = math.pow(R2, 2) - math.pow(d21, 2) - 2 * Rs * d21  # - 2 * x2^T * xs
        error3 = math.pow(R3, 2) - math.pow(d31, 2) - 2 * Rs * d31  # - 2 * x3^T * xs

        print('error2: ' + str(error2))
        print('error3: ' + str(error3))

    def __schmidt_algorithm(self):
        uplinks = self._transaction.get_uplinks()

        # Ax + By = D

        # HARD CODED for Testing
        x1 = uplinks[0].get_bstn_x()
        x2 = uplinks[1].get_bstn_x()
        x3 = uplinks[2].get_bstn_x()
        # x4 = uplinks[3].get_bstn_x()
        y1 = uplinks[0].get_bstn_y()
        y2 = uplinks[1].get_bstn_y()
        y3 = uplinks[2].get_bstn_y()
        # y4 = uplinks[3].get_bstn_y()
        m32 = V * ((uplinks[2].get_time() - uplinks[1].get_time()) / self._T)
        m13 = V * ((uplinks[0].get_time() - uplinks[2].get_time()) / self._T)
        m42 = V * ((uplinks[3].get_time() - uplinks[1].get_time()) / self._T)
        m14 = V * ((uplinks[0].get_time() - uplinks[3].get_time()) / self._T)
        m21 = V * ((uplinks[1].get_time() - uplinks[0].get_time()) / self._T)
        m32 = V * ((uplinks[2].get_time() - uplinks[1].get_time()) / self._T)
        m42 = V * ((uplinks[3].get_time() - uplinks[1].get_time()) / self._T)
        R1 = math.sqrt(uplinks[0].get_bstn_x()**2 + uplinks[0].get_bstn_y()**2)
        R2 = math.sqrt(uplinks[1].get_bstn_x()**2 + uplinks[1].get_bstn_y()**2)
        R3 = math.sqrt(uplinks[2].get_bstn_x()**2 + uplinks[2].get_bstn_y()**2)
        R4 = math.sqrt(uplinks[3].get_bstn_x()**2 + uplinks[3].get_bstn_y()**2)

        # Characteristic Equations
        A3 = x1 * m32 + x2 * m13 + x3 * (-m32 - m13)
        B3 = y1 * m32 + y2 * m13 + y3 * (-m32 - m13)
        D3 = 0.5 * (m21 * m32 * m13 + R1**2 * m32 + R2**2 * m13 + R3**2 * (-m32 - m13))

        A4 = x1 * m42 + x2 * m14 + x3 * (-m42 - m14)
        B4 = y1 * m42 + y2 * m14 + y3 * (-m42 - m14)
        D4 = 0.5 * (m21 * m42 * m14 + R1**2 * m42 + R2**2 * m14 + R4**2 * (-m42 - m14))

        # Solve in one step
        g = np.matrix([[A3, B3],[A4, B4]])
        m = np.matrix([[D3],[D4]])
        # print('g: ' + str(g))
        # print('m: ' + str(m))
        # print('Inv g: ' + str(np.linalg.inv(g)))

        origin = np.dot(np.linalg.inv(g), m)
        # print('origin: ' + str(origin))

        self._dev_x = origin.item((0, 0))
        self._dev_y = origin.item((1, 0))

    def __friedlander_algorithm(self):
        uplinks = self._transaction.get_uplinks()

        # origin = (S^T * M^T * M * S)^-1 * S^T * M^T * M * u

        # HARD CODED for Testing
        x1 = uplinks[0].get_bstn_x()
        x2 = uplinks[1].get_bstn_x()
        x3 = uplinks[2].get_bstn_x()
        x4 = uplinks[3].get_bstn_x()
        y1 = uplinks[0].get_bstn_y()
        y2 = uplinks[1].get_bstn_y()
        y3 = uplinks[2].get_bstn_y()
        y4 = uplinks[3].get_bstn_y()

        m21 = V * ((uplinks[1].get_time() - uplinks[0].get_time()) / self._T)
        m31 = V * ((uplinks[2].get_time() - uplinks[0].get_time()) / self._T)
        m41 = V * ((uplinks[3].get_time() - uplinks[0].get_time()) / self._T)

        R1 = math.sqrt(uplinks[0].get_bstn_x() ** 2 + uplinks[0].get_bstn_y() ** 2)
        R2 = math.sqrt(uplinks[1].get_bstn_x() ** 2 + uplinks[1].get_bstn_y() ** 2)
        R3 = math.sqrt(uplinks[2].get_bstn_x() ** 2 + uplinks[2].get_bstn_y() ** 2)
        R4 = math.sqrt(uplinks[3].get_bstn_x() ** 2 + uplinks[3].get_bstn_y() ** 2)

        # Solve in one step
        I = np.identity(3)
        Z = np.roll(I, -1, 0)
        D = np.linalg.inv(np.matrix([[m21, 0, 0],
                                     [0, m31, 0],
                                     [0, 0, m41]]))

        S = np.matrix([[x2 - x1, y2 - y1],
                       [x3 - x1, y3 - y1],
                       [x4 - x1, y4 - y1]])
        M = (I - Z) * D
        u = 0.5 * np.matrix([[R2**2 - R1**2 - m21**2],
                             [R3**2 - R1**2 - m31**2],
                             [R4**2 - R1**2 - m41**2]])

        origin = np.linalg.inv(S.transpose() * M.transpose() * M * S) * S.transpose() * M.transpose() * M * u

        self._dev_x = origin.item((0, 0))
        self._dev_y = origin.item((1, 0))

    def __friedlander_algorithm3(self):
        uplinks = self._transaction.get_uplinks()

        # origin = (S^T * M^T * M * S)^-1 * S^T * M^T * M * u

        # HARD CODED for Testing
        x1 = uplinks[0].get_bstn_x()
        x2 = uplinks[1].get_bstn_x()
        x3 = uplinks[2].get_bstn_x()
        y1 = uplinks[0].get_bstn_y()
        y2 = uplinks[1].get_bstn_y()
        y3 = uplinks[2].get_bstn_y()

        m21 = V * ((uplinks[1].get_time() - uplinks[0].get_time()) / self._T)
        m31 = V * ((uplinks[2].get_time() - uplinks[0].get_time()) / self._T)

        R1 = math.sqrt(uplinks[0].get_bstn_x() ** 2 + uplinks[0].get_bstn_y() ** 2)
        R2 = math.sqrt(uplinks[1].get_bstn_x() ** 2 + uplinks[1].get_bstn_y() ** 2)
        R3 = math.sqrt(uplinks[2].get_bstn_x() ** 2 + uplinks[2].get_bstn_y() ** 2)

        # Solve in one step
        I = np.identity(2)
        Z = np.roll(I, -1, 0)
        D = np.linalg.inv(np.matrix([[m21, 0],
                                     [0, m31]]))

        S = np.matrix([[x2 - x1, y2 - y1],
                       [x3 - x1, y3 - y1]])
        M = (I - Z) * D
        u = 0.5 * np.matrix([[R2**2 - R1**2 - m21**2],
                             [R3**2 - R1**2 - m31**2]])

        origin = np.linalg.inv(S.transpose() * M.transpose() * M * S) * S.transpose() * M.transpose() * M * u

        self._dev_x = origin.item((0, 0))
        self._dev_y = origin.item((1, 0))

    def __schau_and_robinson(self):
        uplinks = self._transaction.get_uplinks()

        # Create reference bstn at 0,0
        x0 = uplinks[3].get_bstn_x()
        y0 = uplinks[3].get_bstn_y()

        x0 = x0 * -1
        y0 = y0 * -1

        print(x0, y0)

        for uplink in uplinks:
            uplink.set_bstn_x(uplink.get_bstn_x() + x0)
            uplink.set_bstn_y(uplink.get_bstn_y() + y0)

        # Uplink 4 is the origin

        # origin = (S^T * M^T * M * S)^-1 * S^T * M^T * M * u

        # HARD CODED for Testing
        x1 = uplinks[0].get_bstn_x()
        x2 = uplinks[1].get_bstn_x()
        x3 = uplinks[2].get_bstn_x()
        y1 = uplinks[0].get_bstn_y()
        y2 = uplinks[1].get_bstn_y()
        y3 = uplinks[2].get_bstn_y()

        d14 = V * ((uplinks[0].get_time() - uplinks[2].get_time()) / self._T)
        d24 = V * ((uplinks[1].get_time() - uplinks[2].get_time()) / self._T)
        d34 = V * ((uplinks[2].get_time() - uplinks[2].get_time()) / self._T)

        R1 = math.sqrt(uplinks[0].get_bstn_x() ** 2 + uplinks[0].get_bstn_y() ** 2)
        R2 = math.sqrt(uplinks[1].get_bstn_x() ** 2 + uplinks[1].get_bstn_y() ** 2)
        R3 = math.sqrt(uplinks[2].get_bstn_x() ** 2 + uplinks[2].get_bstn_y() ** 2)

        # Solve in two steps
        # 1) Find Rs
        # 2) Find origin(s)

        T = np.matrix([[R1**2 - d14**2],
                       [R2**2 - d24**2],
                       [R3**2 - d34**2]])

        d = np.matrix([[d14],
                       [d24],
                       [d34]])

        M = np.matrix([[x1, y1],
                       [x2, y2],
                       [x3, y3]])

        pM = np.linalg.pinv(M)

        a = 4 - 4 * d.transpose() * pM.transpose() * pM * d
        b = 2 * d.transpose() * pM.transpose() * pM * T + 2 * T.transpose() * pM.transpose() * pM * d
        c = - (T.transpose() * pM.transpose() * pM * T)

        desc = b ** 2 - 4 * a * c  # discriminant

        Rs1 = None
        Rs2 = None
        if desc < 0:
            print("This equation has no real solution")
        elif desc == 0:
            Rs1 = (-b + math.sqrt(b ** 2 - 4 * a * c)) / 2 * a
        else:
            Rs1 = (-b + math.sqrt((b ** 2) - (4 * (a * c)))) / (2 * a)
            Rs2 = (-b - math.sqrt((b ** 2) - (4 * (a * c)))) / (2 * a)

        origin = np.matrix([[0.0],
                            [0.0]])
        if Rs1 and Rs2:
            Rs1 = Rs1.item((0, 0))
            Rs2 = Rs2.item((0, 0))

            origin = 0.5 * pM * (T - 2 * Rs1 * d)
        elif Rs1:
            Rs1 = Rs1.item((0, 0))

            origin = 0.5 * pM * (T - 2 * Rs1 * d)

        self._dev_x = origin.item((0, 0)) - x0
        self._dev_y = origin.item((1, 0)) - y0

    def __schau_and_robinson3(self):
        uplinks = self._transaction.get_uplinks()

        # Create reference bstn at 0,0
        # Uplink 3 is the origin - uplinks[2]
        x0 = uplinks[2].get_bstn_x()
        y0 = uplinks[2].get_bstn_y()

        x0 = x0 * -1
        y0 = y0 * -1

        for num, uplink in enumerate(uplinks):
            uplink.set_bstn_x(uplink.get_bstn_x() + x0)
            uplink.set_bstn_y(uplink.get_bstn_y() + y0)

        # HARD CODED for Testing
        x1 = uplinks[0].get_bstn_x()
        x2 = uplinks[1].get_bstn_x()
        y1 = uplinks[0].get_bstn_y()
        y2 = uplinks[1].get_bstn_y()

        d13 = V * ((uplinks[0].get_time() - uplinks[2].get_time()) / self._T)
        d23 = V * ((uplinks[1].get_time() - uplinks[2].get_time()) / self._T)

        R1 = math.sqrt(uplinks[0].get_bstn_x() ** 2 + uplinks[0].get_bstn_y() ** 2)
        R2 = math.sqrt(uplinks[1].get_bstn_x() ** 2 + uplinks[1].get_bstn_y() ** 2)

        # Solve in two steps
        # 1) Find Rs
        # 2) Find origin(s)
        T = np.matrix([[R1 ** 2 - d13 ** 2],
                       [R2 ** 2 - d23 ** 2]])

        d = np.matrix([[d13],
                       [d23]])

        M = np.matrix([[x1, y1],
                       [x2, y2]])

        a = 4 - 4 * d.transpose() * np.linalg.inv(M).transpose() * np.linalg.inv(M) * d
        b = 2 * d.transpose() * np.linalg.inv(M).transpose() * np.linalg.inv(M) * T + 2 * T.transpose() * \
            np.linalg.inv(M).transpose() * np.linalg.inv(M) * d
        c = - (T.transpose() * np.linalg.inv(M).transpose() * np.linalg.inv(M) * T)

        desc = b ** 2 - 4 * a * c  # discriminant

        Rs1 = None
        Rs2 = None
        if desc < 0:
            pass
            # print("This equation has no real solution")
        elif desc == 0:
            Rs1 = (-b + math.sqrt(b ** 2 - 4 * a * c)) / (2 * a)
        else:
            Rs1 = (-b + math.sqrt((b ** 2) - (4 * (a * c)))) / (2 * a)
            Rs2 = (-b - math.sqrt((b ** 2) - (4 * (a * c)))) / (2 * a)

        origin = np.matrix([[0.0],
                            [0.0]])
        if Rs1 and Rs2:
            Rs1 = Rs1.item((0, 0))
            Rs2 = Rs2.item((0, 0))

            origin = 0.5 * np.linalg.inv(M) * (T - 2 * Rs2 * d)
        elif Rs1:
            Rs1 = Rs1.item((0, 0))

            origin = 0.5 * np.linalg.inv(M) * (T - 2 * Rs1 * d)

        self._dev_x = origin.item((0, 0)) - x0
        self._dev_y = origin.item((1, 0)) - y0

    def __simple_centroid(self):
        uplinks = self._transaction.get_uplinks()

        total_x = 0.0
        total_y = 0.0
        for uplink in uplinks:
            total_x += uplink.get_bstn_x()
            total_y += uplink.get_bstn_y()

        self._dev_x = total_x / len(uplinks)
        self._dev_y = total_y / len(uplinks)