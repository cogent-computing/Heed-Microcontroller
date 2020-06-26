import pandas as pd
import random
import datetime
import warnings
import sys
import re
import os

warnings.filterwarnings('ignore')


class DataProcessor:
    allocation = {
        "Nursery1_Lights": ["Nur 1A CPE1", "Nur 1A CPE2", "Nur 1B CPE3", "Nur 1B CPE4", "Nur 1C CPE5",
                            "Nur 1C CPE6"],
        "Nursery1_Sockets": ["Nur 1A S1", "Nur 1A S2", "Nur 1B S1", "Nur 1C S1"],
        "Nursery2_Lights": ["Nur 2A CPE7", "Nur 2A CPE8", "Nur 2B CPE9", "Nur 2B CPE10", "Nur 2C CPE11",
                            "Nur 2C CPE12"],
        "Nursery2_Sockets": ["Nur 2A S1", "Nur 2A S2", "Nur 2B S1", "Nur 2C S1"],
        "Playground_Lights": ["Playground CPE1", "Playground CPE2", "Playground CPE3", "Playground CPE4",
                              "Playground CPE5"],
        "Playground_Sockets": ["Playground S1", "Playground S2"],
        "Streetlights": ["Streetlight 1 CPE", "Streetlight 2 CPE", "Streetlight 3 CPE"]
    }

    priorities = {1: "Nursery1_Lights", 2: "Nursery2_Lights", 3: "Nursery1_Sockets", 4: "Playground_Lights",
                  5: "Nursery2_Sockets", 6: "Playground_Sockets", 7: "Streetlights"}

    var_alloc = {"Consumed_Energy": "AC_consumption_W",
                 "Generated_Energy": "PV_power_W",
                 "Battery_SoC": "State_of_charge"
                 }

    led_pattern = "LED[0-99]_P"
    socket_pattern = "vRELAY1_LVL"  # "AC_Day_Energy_session"
    ts = "timestamp"

    devices = list(priorities.values())

    def __init__(self):
        pass

    def set_priorities(self, arr_prior):
        self.priorities = {
            arr_prior[0]: "Nursery1_Lights",
            arr_prior[1]: "Nursery2_Lights",
            arr_prior[2]: "Nursery1_Sockets",
            arr_prior[3]: "Playground_Lights",
            arr_prior[4]: "Nursery2_Sockets",
            arr_prior[5]: "Playground_Sockets",
            arr_prior[6]: "Streetlights"
        }

    def reduce_to_groups(self, df, int_alloc=allocation):
        for indi in int_alloc:
            wanted = [x for x in list(df.columns) if bool([ele for ele in int_alloc[indi] if (ele in x) and (
                    re.search(self.led_pattern, x) or re.search(self.socket_pattern, x))])]
            df[indi] = df[wanted].sum(axis=1)
        return df[list(int_alloc.keys()) + list(self.var_alloc.values())]

    def load_csv_data(self, location="../data/microgrid_processed_august.csv"):
        df = pd.read_csv(location, error_bad_lines=True)
        #         print(df.columns)
        cols = list(df.columns)
        cols.remove(self.ts)
        for col in cols:
            df[col] = df[col].astype(float, errors='raise')
        df[self.ts] = pd.to_datetime(df[self.ts], format='%Y/%m/%d %H:%M:%S', errors='raise')
        df.index = df[self.ts]
        df = df.fillna(0.0)
        df = df.drop(self.ts, axis=1)

        df_groups = self.reduce_to_groups(df)

        for par in self.var_alloc:
            df_groups[par] = df_groups[self.var_alloc[par]]

        df_groups['System_Load'] = df_groups['Consumed_Energy'] - df[list(self.allocation.keys())].sum(axis=1)
        df_groups.loc[df_groups['System_Load'] < 50,'System_Load'] = 50
        df_groups['Consumed_Energy'] = df_groups['System_Load']+df[list(self.allocation.keys())].sum(axis=1)
        # df_groups = df_groups.drop(['Discharged_Energy', 'Charged_Energy'], axis=1)
        return df_groups[list(self.allocation.keys()) + list(self.var_alloc.keys()) + ['System_Load']]

    # Random Initial Select
    def select_random_day(self, df, actual_day_nr=None, actual_hour=None):
        diff = df.index.max() - df.index.min()
        if actual_day_nr is not None and actual_hour is not None:
            if actual_day_nr > diff.days - 2 or actual_day_nr <= 0:
                raise ValueError
        else:
            actual_day_nr = random.randint(0, diff.days - 1)
            actual_hour = random.randint(0, 23)
        int_df = df[
            df.index < df.index.min().round('1d') + datetime.timedelta(days=actual_day_nr + 1) + datetime.timedelta(
                hours=actual_hour)]
        int_df = int_df[int_df.index >= df.index.min().round('1d') + datetime.timedelta(days=actual_day_nr)]
        for dev in self.allocation:
            int_df[dev + "_Quota"] = 1.0
        return int_df, actual_day_nr, actual_hour


    def get_full_data_init(self, actual_day_nr=None, actual_hour=None, battery_power=21.1,battery_max_discharge = 40.0,
                           pv_scale=1.0,location="../data/microgrid_processed_august.csv"):
        df = self.load_csv_data(location=location)
        data, day, hour = self.select_random_day(df, actual_day_nr=actual_day_nr, actual_hour=actual_hour)

        for dev in self.priorities:
            data[self.priorities[dev] + "_Priority"] = dev

        data = self.scaleData(data, battery_power=battery_power, pv_scale=pv_scale,
                              battery_max_discharge=battery_max_discharge)

        return data

    def scaleData(self, data, battery_power=21.1, pv_scale=1.0,battery_max_discharge=40.0):
        soc = data[data.index == data.index.min()]['Battery_SoC'].values[0]
        energy_diff = data[data.index == data.index.min()]['Consumed_Energy'].values[0] - \
                      data[data.index == data.index.min()]['Generated_Energy'].values[0]
        bat = Battery(state_of_charge=soc, battery_capacity=battery_power,max_discharge=battery_max_discharge)
        bat.resolve_energy(energy_diff / 1000.0)

        first = True
        for inner_key, row_inner in data.iterrows():
            if first:
                first = False
                pass
            # Sort PV Values - Scaling
            data.loc[inner_key, 'Generated_Energy'] = data.loc[inner_key, 'Generated_Energy'] * pv_scale

            ret = bat.resolve_energy(
                (data.loc[inner_key, 'Generated_Energy'] - data.loc[inner_key, 'Consumed_Energy']) / 1000.0)  #
            data.loc[inner_key, 'Battery_SoC'] = bat.state_of_charge
        return data


class Battery:
    # https://www.sciencedirect.com/science/article/pii/S0360544218325064
    # Took basic ideas from here
    state_of_charge = 0.0
    battery_capacity = 21.1
    available_energy = 0.0
    max_discharge = 50.0
    charge_efficiency = 0.85
    self_discharge_h = 0.001  # Not Used as very smol

    def __init__(self, state_of_charge=0.0, battery_capacity=21.1, max_discharge=50.0, charge_efficiency=0.85,
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

    def resolve_energy(self, energy):
        if energy >= 0:
            self.charge_battery(energy)
            return 0.0
        else:
            return self.discharge_battery(-energy)

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


class ControllEnvironment:
    battery = None
    curr_date = None
    input_df = None
    df_control = None

    def __init__(self, step=0, day_nr=38, actual_hour=0, battery_power=21.1,battery_max_discharge = 40.0, pv_scale=1.0,
                 priorities=[1, 2, 3, 4, 5, 6, 7],step_type="binary",control_args=None,location="../data/microgrid_processed_august.csv"):
        self.step = step
        self.battery_power = battery_power
        self.battery_max_discharge = battery_max_discharge
        self.pv_scale = pv_scale
        self.initialise_data(day_nr=day_nr, actual_hour=actual_hour, battery_power=battery_power,
                             battery_max_discharge =battery_max_discharge,
                                 pv_scale=pv_scale, priorities=priorities,location=location)


    def initialise_data(self, day_nr=38, actual_hour=3, battery_power=21.1, battery_max_discharge = 40.0, pv_scale=1.0,
                        priorities=[1, 2, 3, 4, 5, 6, 7],location="../data/microgrid_processed_august.csv"):
        dp = DataProcessor()
        dp.set_priorities(priorities)
        data = dp.get_full_data_init(actual_day_nr=day_nr, actual_hour=actual_hour,
                                     battery_power=battery_power, battery_max_discharge = battery_max_discharge,
                                     pv_scale=pv_scale,location=location)
        # Save Value
        self.input_df = data
        soc = data[data.index == data.index.max()]['Battery_SoC'].values[0]
        self.battery = Battery(state_of_charge=soc, battery_capacity=battery_power,max_discharge=battery_max_discharge)
        self.curr_date = data[data.index == data.index.max()].index[0]

    def get_starting_scenario(self):
        return self.input_df

    def save_result(self,df,location = "./output_data.csv"):
        df.to_csv(location, date_format='%d/%m/%Y %H:%M')

    def step_24h(self,control_df,battery_power=21.1, pv_scale=1.0, step_type="binary"):
        df_control = pd.DataFrame.from_dict(control_df)
        int_df = self.input_df
        int_df = int_df[[x for x in list(int_df.columns) if "_Quota" not in x]]
        int_df.reset_index(drop=True, inplace=True)
        dev_cols =[x.split("_Quota")[0] for x in list(df_control.columns)]
        int_df = pd.concat([int_df, df_control], axis=1)
        #Battery Sort
        soc = int_df[int_df.index == int_df.index.min()]['Battery_SoC'].values[0]
        energy_diff = int_df[int_df.index == int_df.index.min()]['Consumed_Energy'].values[0] - \
                      int_df[int_df.index == int_df.index.min()]['Generated_Energy'].values[0]
        bat = Battery(state_of_charge=soc, battery_capacity=battery_power,max_discharge=self.battery_max_discharge)
        bat.resolve_energy(energy_diff / 1000.0)

        # Enact Changes
        if step_type == "binary":
            for inner_key, row_inner in int_df.iterrows():
                saved_energy = 0.0
                for dev in dev_cols:
                    if int_df.loc[inner_key, dev+"_Quota"] < 0.99:
                        saved_energy+=int_df.loc[inner_key, dev]
                        int_df.loc[inner_key, dev] = 0.0
                int_df.loc[inner_key,"Consumed_Energy"] = int_df.loc[inner_key,"Consumed_Energy"]-saved_energy
                energy_diff = int_df.loc[inner_key,'Generated_Energy']- int_df.loc[inner_key,'Consumed_Energy']
                bat.resolve_energy(energy_diff / 1000.0)
                int_df.loc[inner_key, "Battery_SoC"] = bat.state_of_charge
                self.battery = bat
        elif step_type == "percentage":
            for inner_key, row_inner in int_df.iterrows():
                saved_energy = 0.0
                for dev in dev_cols:
                    saved_energy+=(1.0-int_df.loc[inner_key, dev+"_Quota"])*int_df.loc[inner_key, dev]
                    int_df.loc[inner_key, dev] = int_df.loc[inner_key, dev]*int_df.loc[inner_key, dev+"_Quota"]
                int_df.loc[inner_key,"Consumed_Energy"] = int_df.loc[inner_key,"Consumed_Energy"]-saved_energy
                energy_diff = int_df.loc[inner_key,'Generated_Energy']- int_df.loc[inner_key,'Consumed_Energy']
                bat.resolve_energy(energy_diff / 1000.0)
                int_df.loc[inner_key, "Battery_SoC"] = bat.state_of_charge
                self.battery = bat
        elif step_type == "quota":
            #For Quotas, the quota itself needs to be replaced with wether the device was curtailed and by how much
            for inner_key, row_inner in int_df.iterrows():
                saved_energy = 0.0
                for dev in dev_cols:
                    if int_df.loc[inner_key, dev + "_Quota"] < int_df.loc[inner_key, dev]:
                        saved_energy+=int_df.loc[inner_key, dev] - int_df.loc[inner_key, dev + "_Quota"]
                        int_df.loc[inner_key, dev] = int_df.loc[inner_key, dev + "_Quota"]
                        int_df.loc[inner_key, dev + "_Quota"] = int_df.loc[inner_key, dev + "_Quota"]/int_df.loc[inner_key, dev]
                    else:
                        int_df.loc[inner_key, dev + "_Quota"] = 1.0
                int_df.loc[inner_key,"Consumed_Energy"] = int_df.loc[inner_key,"Consumed_Energy"]-saved_energy
                energy_diff = int_df.loc[inner_key,'Generated_Energy']- int_df.loc[inner_key,'Consumed_Energy']
                bat.resolve_energy(energy_diff / 1000.0)
                int_df.loc[inner_key, "Battery_SoC"] = bat.state_of_charge
                self.battery = bat
        else:
            raise TypeError
        return int_df