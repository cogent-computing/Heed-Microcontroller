
import unittest
import datetime
import pandas as pd
import os
import json

from deployment.Data_Retreiver import Data_Retreiver

class test_Data_Retreiver(unittest.TestCase):

    def setUp(self):
        dir_path = os.path.dirname(os.path.dirname(os.path.realpath(__file__))) #Core directory always
        with open(os.path.join(os.path.join(dir_path,'config'),'runner_config.json')) as json_file:
            json_data = json.load(json_file)

        devices = json_data["devices"]

        # Data Retreiver
        sql_user = json_data["sql_user"]
        sql_pw = json_data["sql_pw"]
        sql_db = json_data["sql_db"]
        sql_addr = json_data["sql_addr"]
        sql_port = json_data["sql_port"]

        # Init Data Retreiver
        self.data = Data_Retreiver(devices, sql_user, sql_pw, sql_addr, sql_port, sql_db)

    def full_test_data(self):

        dev_light = "Nursery_1A_CPE_No_2"
        dev_socket = "Playground_AC_socket_No_1"
        group = ["Nursery_1A_CPE_No_1", "Nursery_1A_CPE_No_2", "Nursery_1B_CPE_No_3", "Nursery_1B_CPE_No_4",
                 "Nursery_1C_CPE_No_5", "Nursery_1C_CPE_No_6"]
        hour = 6

        data = self.data

        pd.set_option('display.max_columns', 30)
        dt_ts = datetime.datetime.now()
        print("--Forecast--\n", data.retreive_latest_forecast(dt_ts).head(5))
        print("--Raw Sys--\n", data.retreive_latest_raw_system_snapshot(dt_ts).head(5))
        print("--Priority--\n", data.retreive_latest_priority(dt_ts).head(5))
        print("--Group Energy--\n", data.get_total_energy_for_group(group, dt_ts))
        print("--Aggregated Values --\n", data.retreive_aggregared_values(dt_ts))
        print("--AVG for Hour Values --\n", data.retreive_average_vals_for_hour(dt_ts, hour))
        print("--Average P Light--\n", data.retreive_average_P_lights(dev_light, dt_ts))
        print("--AC Session--\n", data.retreive_AC_Session(dev_socket, dt_ts))
        print("--AC Energy--\n", data.retreive_AC_Energy(dev_socket, dt_ts))
        print("--Light Session--\n", data.retreive_Light_Session(dev_light, dt_ts))
        print("--Light Energy--\n", data.retreive_Light_Energy(dev_light, dt_ts))
        print("--Quota Latest Light--\n", data.get_latest_quota(dev_light, dt_ts))
        print("--Quota Latest Socket --\n", data.get_latest_quota(dev_socket, dt_ts))

        dec = {'nursery1_lights': {'state': 'Unconstrained', 'energy_est_used_total': 132.30215890353352,
                                   'constraining_factor': 1.0,
                                   'device_const': {'Nursery_1A_CPE_No_1': (4320, 4320, False),
                                                    'Nursery_1A_CPE_No_2': (4320, 4320, False),
                                                    'Nursery_1B_CPE_No_3': (4320, 4320, False),
                                                    'Nursery_1B_CPE_No_4': (4320, 4320, False),
                                                    'Nursery_1C_CPE_No_5': (4320, 4320, False),
                                                    'Nursery_1C_CPE_No_6': (4320, 4320, True)},
                                   'timestamp': '2020-03-04 14:01:09.698676'},
               'nursery2_lights': {'state': 'Unconstrained', 'energy_est_used_total': 338.3709751064285,
                                   'constraining_factor': 1.0,
                                   'device_const': {'Nursery_2A_CPE_No_7': (4320, 4320, False),
                                                    'Nursery_2A_CPE_No_8': (4320, 4320, False),
                                                    'Nursery_2B_CPE_No_9': (4320, 4320, False),
                                                    'Nursery_2B_CPE_No_10': (4320, 4320, False),
                                                    'Nursery_2C_CPE_No_11': (4320, 4320, False),
                                                    'Nursery_2C_CPE_No_12': (
                                                        4320, 4320, False)},
                                   'timestamp': '2020-03-04 14:01:17.163449'},
               'playground_lights': {'state': 'Unconstrained', 'energy_est_used_total': 496.9524094664317,
                                     'constraining_factor': 1.0,
                                     'device_const': {'Playground_No_1': (4320, 4320, False),
                                                      'Playground_No_2': (4320, 4320, False),
                                                      'Playground_No_3': (4320, 4320, False),
                                                      'Playground_No_4': (4320, 4320, False),
                                                      'Playground_No_5': (4320, 4320, False)},
                                     'timestamp': '2020-03-04 14:01:23.896520'},
               'playground_sockets': {'state': 'Unconstrained', 'energy_est_used_total': 54.497536810310116,
                                      'constraining_factor': 1.0,
                                      'device_const': {'Playground_AC_socket_No_1': (1200000, False),
                                                       'Playground_AC_Socket_No_2': (1200000, False)},
                                      'timestamp': '2020-03-04 14:01:26.412130'},
               'nursery1_sockets': {'state': 'Unconstrained', 'energy_est_used_total': 25.474201030282288,
                                    'constraining_factor': 1.0,
                                    'device_const': {'Nursery_AC_Socket_1A_No_1': (1200000, False),
                                                     'Nursery_AC_Socket_1A_No_2': (1200000, False),
                                                     'Nursery_AC_Socket_1B': (1200000, False),
                                                     'Nursery_AC_Socket_1C': (1200000, False)},
                                    'timestamp': '2020-03-04 14:01:31.457445'},
               'nursery2_sockets': {'state': 'Unconstrained', 'energy_est_used_total': 56.17494375631213,
                                    'constraining_factor': 1.0,
                                    'device_const': {'Nursery_AC_Socket_2A_No_1': (1200000, False),
                                                     'Nursery_AC_Socket_2A_No_2': (1200000, False),
                                                     'Nursery_AC_Socket_2B': (1200000, False),
                                                     'Nursery_AC_Socket_2C': (1200000, False)},
                                    'timestamp': '2020-03-04 14:01:36.379328'}}

        data.save_decision(dec)

