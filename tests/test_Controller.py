import unittest
import json
import os
#Data retreiver Run
import datetime
import pandas as pd


from deployment.Data_Retreiver import Data_Retreiver
from deployment.Dummy_Control_Enactor import Enactor
from deployment.Controller import Controller

class Controller_Test(unittest.TestCase):

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

        ## Conctrol Enactor
        sftp_location = json_data["sftp_location"]
        sftp_port = json_data["sftp_port"]
        sftp_username = json_data["sftp_username"]
        sftp_password = json_data["sftp_password"]
        sftp_key_location = json_data["sftp_key_location"]
        sftp_directory = json_data["sftp_directory"]

        # Global for Unit Test
        self.enact = Enactor(devices, sftp_location, sftp_port, sftp_username, sftp_password, sftp_key_location,
                        sftp_directory)

        # Controller Init
        ts_step = datetime.datetime.now()  # - datetime.timedelta(hours=3)

        self.allocation = json_data["allocation"]
        if 'System_Data' in self.allocation:
            del self.allocation['System_Data']



    def test_Controller(self):

       self.control = Controller(self.data, self.enact, self.allocation, 4)
       self.control.do_step()
