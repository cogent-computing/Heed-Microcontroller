import unittest
import json
import os

from deployment.Control_Enactor import Enactor

class Enactor_Test(unittest.TestCase):

    def setUp(self):

        dir_path = os.path.dirname(os.path.dirname(os.path.realpath(__file__))) #Core directory always
        with open(os.path.join(os.path.join(dir_path,'config'),'runner_config.json')) as json_file:
            json_data = json.load(json_file)

        devices = json_data["devices"]

        sftp_location = json_data["sftp_location"]
        sftp_port = json_data["sftp_port"]
        sftp_username = json_data["sftp_username"]
        sftp_password = json_data["sftp_password"]
        sftp_key_location = os.path.join(dir_path,json_data["sftp_key_location"])
        sftp_directory = json_data["sftp_directory"]

        # Global for Unit Test
        self.enact = Enactor(devices, sftp_location, sftp_port, sftp_username, sftp_password, sftp_key_location,
                        sftp_directory)



    def test_check_diff_light(self):
        test_lights = [
            [0, (4320, 4320), 4320, 4320],
            [1, None, 4320, 4320],
            [1, (0, 1280), 1280, 1280],
            [1, (4320, 0), 1280, 1280],
            [1, (1280, 4320), 0, 1280],
            [1, (4320, 1280), 4320, 0],
            [0, (4320, 1280), 4320, 1280],
            [1.08, (1280, 4320), 4320, 1280],
        ]

        for test in test_lights:
            self.assertAlmostEqual(test[0], self.enact.check_diff_light(test[1], test[2], test[3]),1)

    def test_check_diff_socket(self):
        test_sockets = [
            [0, 1200000, 1200000],
            [1, None, 1200000],
            [1, 0, 1200000],
            [1, 1200000, 0],
            [0.66, 1200000, 600000],
            [0.66, 600000, 1200000],
        ]

        for test in test_sockets:
            self.assertAlmostEqual(test[0], self.enact.check_diff_socket(test[1], test[2]), 1)

