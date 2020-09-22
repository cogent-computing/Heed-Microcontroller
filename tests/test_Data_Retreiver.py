import unittest
import json
import os
import datetime
import pandas as pd
from deployment.Data_Retreiver import Data_Retreiver

class DataRetreive_Test(unittest.TestCase):

    def setUp(self):

        dir_path = os.path.dirname(os.path.dirname(os.path.realpath(__file__))) #Core directory always
        with open(os.path.join(os.path.join(dir_path,'config'),'runner_config.json')) as json_file:
            json_data = json.load(json_file)

        self.devices = json_data["devices"]

        # Data Retreiver
        self.sql_user = json_data["sql_user"]
        self.sql_pw = json_data["sql_pw"]
        self.sql_db = json_data["sql_db"]
        self.sql_addr = json_data["sql_addr"]
        self.sql_port = json_data["sql_port"]

        self.data = Data_Retreiver(self.devices, self.sql_user, self.sql_pw, self.sql_addr, self.sql_port, self.sql_db)

    def test_components_noResp(self):
        self.data.get_unsent_logs(datetime.datetime.now())
        self.data.retreive_filled_aggre(datetime.datetime.now() - datetime.timedelta(days=20), 2)


    def test_componentResponse(self):
        dev_light = "Nursery_1A_CPE_No_2"
        dev_socket = "Playground_AC_socket_No_1"
        group = ["Nursery_1A_CPE_No_1", "Nursery_1A_CPE_No_2", "Nursery_1B_CPE_No_3", "Nursery_1B_CPE_No_4",
                 "Nursery_1C_CPE_No_5", "Nursery_1C_CPE_No_6"]
        hour = 6

        dt_ts = datetime.datetime.now()

        self.assertEqual(self.data.retreive_latest_forecast(dt_ts).shape,(1,2))
        self.assertEqual(self.data.retreive_latest_raw_system_snapshot(dt_ts).shape,(4,3))
        self.assertEqual(self.data.retreive_latest_priority(dt_ts).shape[0],1)
        self.assertEqual(self.data.get_total_energy_for_group(group, dt_ts).shape,(1,len(group)))
        self.assertEqual(self.data.retreive_aggregared_values(dt_ts).shape[0],1)
        self.assertEqual(self.data.retreive_average_vals_for_hour(dt_ts, hour, 8).shape[1],4)
        self.assertTrue(0 <= self.data.retreive_AC_Session(dev_socket, dt_ts) <= 5000)
        self.assertTrue(0 <= self.data.retreive_AC_Energy(dev_socket, dt_ts) <= 5000)
        self.assertEqual(len(self.data.retreive_Light_Session(dev_light, dt_ts)),2)
        self.assertEqual(len(self.data.retreive_Light_Energy(dev_light, dt_ts)),2)
        self.assertEqual(len(self.data.get_latest_quota(dev_light, dt_ts)),2)
        self.assertEqual(len(self.data.get_latest_quota(dev_socket, dt_ts)),2)

