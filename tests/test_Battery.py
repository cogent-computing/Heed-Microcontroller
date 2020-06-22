import unittest

from deployment.Battery import Battery

class BatteryTest(unittest.TestCase):

    def test_discharge(self):
        test_lights = [
            [{"state_of_charge": 100.0, "battery_capacity": 21.1, "max_discharge": 40.0, "charge_efficiency": 0.85},
             1.9, 0.0, 90.9, 10.76],
            [{"state_of_charge": 50.0, "battery_capacity": 21.1, "max_discharge": 40.0, "charge_efficiency": 0.85},
             1.9, 0.0, 40.9, 0.21],
            [{"state_of_charge": 45.0, "battery_capacity": 21.1, "max_discharge": 40.0, "charge_efficiency": 0.85},
             2.8, 1.74, 40.0, 0.0],
            [{"state_of_charge": 100.0, "battery_capacity": 5.1, "max_discharge": 50.0, "charge_efficiency": 0.85},
             2.8, 0.25, 50.0, 0.0],

        ]

        for test in test_lights:
            int_bat = Battery(state_of_charge=test[0]['state_of_charge'], battery_capacity=test[0]['battery_capacity'],
                          max_discharge=test[0]['max_discharge'], charge_efficiency=test[0]['charge_efficiency'])
            self.assertAlmostEqual(test[2], int_bat.discharge_battery(test[1]), places=1)
            self.assertAlmostEqual(test[3], int_bat.state_of_charge, places=0)
            self.assertAlmostEqual(test[4], int_bat.get_discharge_capacity_left(), places=1)