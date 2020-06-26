import unittest


class Battery:
    # https://www.sciencedirect.com/science/article/pii/S0360544218325064
    # Took basic ideas from here
    state_of_charge = 0.0
    battery_capacity = 21.1
    available_energy = 0.0
    max_discharge = 40.0
    charge_efficiency = 0.80
    self_discharge_h = 0.001  # Not Used as very smol

    def __init__(self, state_of_charge=100.0, battery_capacity=21.1, max_discharge=40.0, charge_efficiency=0.85,
                 self_discharge_h=0.001):
        # update values
        self.state_of_charge = state_of_charge
        self.available_energy = battery_capacity * state_of_charge / 100.0
        self.battery_capacity = battery_capacity
        self.max_discharge = max_discharge
        self.charge_efficiency = charge_efficiency
        self.self_discharge_h = self_discharge_h

    def get_storage_capacity_left(self):
        return (100.0 - self.state_of_charge) / 100.0 * self.battery_capacity / self.charge_efficiency

    def get_discharge_capacity_left(self):
        return (self.state_of_charge - self.max_discharge) / 100.0 * self.battery_capacity

    def charge_battery(self, added_energy):
        chargable_energy = (100.0 - self.state_of_charge) / 100.0 * self.battery_capacity / self.charge_efficiency
        if chargable_energy <= added_energy:
            self.state_of_charge = 100.0
            self.available_energy = self.battery_capacity
            return added_energy - chargable_energy
        else:
            self.state_of_charge += added_energy * self.charge_efficiency / self.battery_capacity * 100.0
            self.available_energy += added_energy * self.charge_efficiency
            return 0.0

    def discharge_battery(self, used_energy):
        dischargable_energy = (self.state_of_charge - self.max_discharge) / 100.0 * self.battery_capacity
        if dischargable_energy <= used_energy:
            self.state_of_charge = self.max_discharge
            self.available_energy = self.battery_capacity * self.max_discharge / 100.0
            return used_energy - dischargable_energy
        else:
            self.state_of_charge -= used_energy / self.battery_capacity * 100.0
            self.available_energy -= used_energy
            return 0.0

    def __str__(self):
        return "SoC: " + str(self.state_of_charge) + " Energy_Left: " + str(self.get_discharge_capacity_left())
