
from simulation_evaluation.microgrid_simulator import ControllEnvironment
from deployment.Battery import Battery

class SpaceShareController:

    def __init__(self,day_nr=18, precision=1, battery_power=21.1, pv_scale=1.0, priorities=[1, 2, 3, 4, 5, 6, 7]):
        self.battery_power = battery_power
        self.pv_scale = pv_scale
        self.priorities = priorities
        self.precision = precision
        self.test_env = ControllEnvironment(day_nr=day_nr, battery_power=battery_power, pv_scale=pv_scale,
                                            priorities=priorities)

    def sort_device(self, df, dev, remaining_energy):
        #Already zero nothing to do
        if remaining_energy <= 0.0:
            return 0.0, 0.0

        used_energy = sum(df[dev])
        print("Used Energy: ",used_energy)
        remaining_energy2 = remaining_energy-used_energy
        print("Remaining Energy: ",remaining_energy2)

        if remaining_energy2>=0.0:
            return remaining_energy2,1.0
        else:
            return 0.0,remaining_energy/used_energy

    def run(self):

        self.latest ="Running Space Shared Control on Hist Data... "

        df_system_for = self.test_env.input_df.reset_index(drop=True)

        gen_energy = sum(df_system_for["Generated_Energy"])
        system_load = sum(df_system_for["System_Load"])
        initial_e_diff = df_system_for["Generated_Energy"][0] - df_system_for["Consumed_Energy"][0]
        bat = Battery(state_of_charge=df_system_for["Battery_SoC"][0] , battery_capacity=self.battery_power, max_discharge=40.0)
        if initial_e_diff > 0.0:
            bat.charge_battery(initial_e_diff/1000.0)
        else:
            bat.discharge_battery(initial_e_diff / 1000.0)
        battery_soc = bat.state_of_charge

        print("-------Energy State--------")
        remaining_energy = gen_energy - system_load * 1.2 + (
                battery_soc - 40.0) * self.battery_power * 1000 / 100 * 0.9  # system load + 20%; remaining battery SOC, with 90% gettable at a 21kw battery
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
            print("------------------------------------------------")
            print("For Device: " + prior_values[key] + " with energy avialable: " + str(remaining_energy))
            remaining_energy, fraction = self.sort_device(df_system_for, prior_values[key].split("_Quota")[0], remaining_energy)
            control_dict[prior_values[key]] = [fraction for x in range(0, 24)]
            print("Result: "+str(remaining_energy),"Fraction: ",fraction)

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

if __name__ == "__main__":
    # Basic Controller Run
    space_shared_controller = SpaceShareController(day_nr=18, precision=1, battery_power=21.1, pv_scale=1.0,
                                                   priorities=[1, 2, 3, 4, 5, 6, 7])

    spaceshared_util = space_shared_controller.run()
    print(spaceshared_util)