
from simulation_evaluation.microgrid_simulator import ControllEnvironment
from deployment.Battery import Battery

class ProtectionController:

    def __init__(self,day_nr=18, precision=1, battery_power=21.1,battery_max_discharge=40.0,
                 pv_scale=1.0, priorities=[1, 2, 3, 4, 5, 6, 7]):
        self.battery_power = battery_power
        self.battery_max_discharge = battery_max_discharge
        self.pv_scale = pv_scale
        self.priorities = priorities
        self.precision = precision
        self.test_env = ControllEnvironment(day_nr=day_nr, battery_power=battery_power,
                                            battery_max_discharge = self.battery_max_discharge,pv_scale=pv_scale,
                                            priorities=priorities)

    def sort_hour(self, values):
        energy_diff = values["Generated_Energy"] - values['Consumed_Energy']
        dev_load = values['Consumed_Energy'] - values['System_Load']
        print("Consumed Energy: ",values['Consumed_Energy']," System Load: ",values['System_Load']," Generated Energy:",
              values["Generated_Energy"], " Device Energy:",dev_load, " EnergyDiff: ",energy_diff," Battery:",self.bat)
        if energy_diff < 0:
            diff = self.bat.discharge_battery(-energy_diff/1000.0)
        else:
            diff = self.bat.charge_battery(energy_diff/1000.0)
        if self.bat.state_of_charge <= self.bat.max_discharge:
            print("Battery Energy Fully Discharged: ",self.bat, "Diff: ",diff)
            if diff >= dev_load:
                print("Energy not available - Remaining energy less than used by devices: ", 0.0)
                return 0.0
            else:
                print("Energy not available - Devices partially curtailed: ",diff/dev_load)
                return diff/dev_load
        else:
            print("Battery  Energy Available:",self.bat)
            return 1.0

    def run(self):

        self.latest ="Running Protection Controller on  Hist Data... "

        df_system_for = self.test_env.input_df.reset_index(drop=True)

        gen_energy = sum(df_system_for["Generated_Energy"])
        system_load = sum(df_system_for["System_Load"])
        initial_e_diff = df_system_for["Generated_Energy"][0] - df_system_for["Consumed_Energy"][0]
        bat = Battery(state_of_charge=df_system_for["Battery_SoC"][0] , battery_capacity=self.battery_power,
                      max_discharge=self.battery_max_discharge)
        if initial_e_diff > 0.0:
            bat.charge_battery(initial_e_diff/1000.0)
        else:
            bat.discharge_battery(initial_e_diff / 1000.0)
        battery_soc = bat.state_of_charge
        self.bat = bat
        print("-------Energy State--------")
        remaining_energy = self.bat.get_discharge_capacity_left()*1000.0 # remaining battery SOC, with 90% gettable at a 21kw battery
        print("Generated energy: " + str(gen_energy))
        print("System Load: " + str(system_load))
        print("Battery SoC: " + str(battery_soc))
        print("Remaining Energy: " + str(remaining_energy))

        devs = ['Nursery1_Lights_Quota','Nursery1_Sockets_Quota','Nursery2_Lights_Quota', 'Nursery2_Sockets_Quota',
                'Playground_Lights_Quota','Playground_Sockets_Quota','Streetlights_Quota']
        prior_values ={}
        for i, value in enumerate(devs):
            prior_values[self.priorities[i]] = value

        print("Priorities: ",prior_values)

        #remaining_energy = 0  # Overwrite for testing

        control_dict={}
        for key in sorted(prior_values.keys()):
            control_dict[prior_values[key]] = []

        for key, values in df_system_for.iterrows():
            print("------------------------------------------------")
            print("For Hour: " + str(key))
            fraction = self.sort_hour(values)
            print("Resulting Fraction: ", fraction)
            for key2 in sorted(prior_values.keys()):
                control_dict[prior_values[key2]].append(fraction)

        self.control_dict = control_dict

        print("Control Command:\n",control_dict)
        applied = self.test_env.step_24h(control_dict, battery_power=self.battery_power, pv_scale=self.pv_scale,
                                         step_type="percentage")
        return self.evaluate_individual(applied)


    def get_deployment(self):
        # All On almost
        applied = self.test_env.step_24h(self.control_dict, battery_power=self.battery_power, pv_scale=self.pv_scale,
                                         step_type="percentage")
        return applied

    def evaluate_individual(self, individual):
        return sum(individual['Battery_SoC']) / 100.0 / 24.0
