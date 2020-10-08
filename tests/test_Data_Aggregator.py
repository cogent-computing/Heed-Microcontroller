import unittest
import json
import os

from deployment.Data_Retreiver import Data_Retreiver
from deployment.Data_Aggregator import Aggregator

class Aggregator_Test(unittest.TestCase):

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

        # Init Data Retreiver
        self.data = Data_Retreiver(self.devices, self.sql_user, self.sql_pw, self.sql_addr, self.sql_port, self.sql_db)

        self.sql_table = json_data["sql_aggregate"]
        self.sql_table_raw = json_data["sql_raw_energy"]
        self.sql_table_state = json_data["sql_raw_energy"]



    def test_Aggregator(self):
        self.aggre = Aggregator(self.devices, self.sql_table, self.sql_table_raw, self.sql_table_state, self.sql_addr,
                                self.sql_port, self.sql_user, self.sql_pw, self.sql_db)

        # Do step and get the final output that would be printed to the log
        self.aggre.do_step()
