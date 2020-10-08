import unittest
import json
import os
import datetime
import pandas as pd

from deployment.Data_Retreiver import Data_Retreiver
from deployment.Remote_Logger import RemoteLogger

class RemoteLogger_Test(unittest.TestCase):

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

        self.mqtt_address = json_data["mqtt_address"]
        self.mqtt_port = json_data["mqtt_port"]
        self.mqtt_username = json_data["mqtt_username"]
        self.mqtt_password = json_data["mqtt_password"]

        self.data = Data_Retreiver(devices, sql_user, sql_pw, sql_addr, sql_port, sql_db)



    def test_RemoteLogger(self):
        rl = RemoteLogger(self.data, self.mqtt_address, self.mqtt_port, self.mqtt_username, self.mqtt_password)
        rl.do_step()
