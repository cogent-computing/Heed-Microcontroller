import unittest
import os
import json
import pandas as pd
import warnings

from deployment.Forecaster_v2 import Forecaster
from deployment.Data_Retreiver import Data_Retreiver
from deployment.Battery import Battery

class TestForecasterV2(unittest.TestCase):

    def setUp(self):
        warnings.filterwarnings("ignore")
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
        data = Data_Retreiver(devices, sql_user, sql_pw, sql_addr, sql_port, sql_db)

        # Init forecast
        self.forecast = Forecaster(Battery, data, devices)

    def test_discharge(self):
        #get_forecast_dev
        #get_forecast_generation

        dir_path = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))  # Core directory always
        input_df = pd.read_csv(os.path.join(os.path.join(dir_path,"data"),'test_input.csv'))
        input_df.index = pd.to_datetime(input_df['timestamp'],errors='raise')
        output_df = pd.read_csv(os.path.join(os.path.join(dir_path, "data"), 'test_output.csv'))
        dev_list = [x for x in list(input_df.columns) if x not in ['battery_soc','generated_energy',
                                                                   'charged_energy','system_load','timestamp']]
        for dev in dev_list:
            res = self.forecast.get_forecast_dev(input_df[dev].to_frame(),forecast_period = 24)
            print(res[dev])
            print(output_df[dev].reset_index())
            self.assertSequenceEqual(res[dev],output_df[dev].reset_index())
            break