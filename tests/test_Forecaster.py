import unittest
import json
import os
import datetime
import pandas as pd

from deployment.Data_Retreiver import Data_Retreiver
from deployment.Battery import Battery
from deployment.Forecaster import Forecaster


class Forecast_Test(unittest.TestCase):

    def setUp(self):

        dir_path = os.path.dirname(os.path.dirname(os.path.realpath(__file__))) #Core directory always
        with open(os.path.join(os.path.join(dir_path,'config'),'runner_config.json')) as json_file:
            json_data = json.load(json_file)

        self.devices = json_data["devices"]
        self.devices = {x: self.devices[x] for x in self.devices if x != "Victron_VenusGX"}
        # Data Retreiver
        self.sql_user = json_data["sql_user"]
        self.sql_pw = json_data["sql_pw"]
        self.sql_db = json_data["sql_db"]
        self.sql_addr = json_data["sql_addr"]
        self.sql_port = json_data["sql_port"]

        # Init Data Retreiver
        self.data = Data_Retreiver(self.devices, self.sql_user, self.sql_pw, self.sql_addr, self.sql_port, self.sql_db)


        self.curr_ts = datetime.datetime.now()
        print("Running Forecasting -- ", self.curr_ts, " --")
        self.forecast_period = 48


    def test_Forecast(self):
        forecast = Forecaster(Battery, self.data, self.devices)
        forecast.do_step(self.forecast_period, self.curr_ts)
        self.assertEqual(forecast.latest_forecast.shape[0],self.forecast_period)
        self.assertEqual(forecast.latest_forecast.shape[1], len(self.devices)+6)
        #6are the: battery_soc 	charged_energy 	consumed_energy 	generated_energy 	timestamp 	system_load