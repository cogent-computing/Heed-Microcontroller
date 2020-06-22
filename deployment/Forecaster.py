import sys
import pandas as pd
import datetime
import time
import json
from sqlalchemy import create_engine
import os
import threading

from deployment.Data_Retreiver import Data_Retreiver
from deployment.Battery import Battery


class Forecaster:

    def __init__(self, Battery, data, dev_list, going_back=7):

        self.dev_list = dev_list
        self.Battery = Battery
        self.data = data
        self.going_back = going_back
        # multiplying factor
        # Generation
        self.get_frac = 0.95  # 5% Error Allowed

        # Consumption
        self.get_cons = 1.05  # 5% Error Allowed
        self.latest = "Initialised"
        self.latest_forecast = None

    def stop(self):
        self.data.stop()

    def getLatest(self):
        return "Forecaster : " + self.latest

    def do_step(self, forecast_period=48, curr_ts=datetime.datetime.now()):

        df = self.data.retreive_aggregared_values(curr_ts)
        bat = Battery(state_of_charge=df['battery_soc'].values[0])

        df_full_hour = None

        for added_hours in range(0, forecast_period):
            hour = curr_ts.hour + added_hours
            while hour > 23:
                hour = hour - 23

            # Check if all Available, if not add mean values
            df_historic = self.data.retreive_average_vals_for_hour(curr_ts, hour, self.going_back)
            if df_historic is None:
                self.latest = "---- Mini Fault: Group Historic is empty"
                return
            df_system = df_historic[df_historic['dev_group'] == "System_Data"]

            df_system = df_system[['parameter', 'avg']]

            df_system.loc[df_system['parameter'] == "VenusGX/Dc/Pv/Power", "parameter"] = "generated_energy"
            df_system.loc[df_system[
                              'parameter'] == "VenusGX/Ac/Consumption/L1/Power",
                          'parameter'] = "consumed_energy"
            df_system.loc[
                df_system['parameter'] == "VenusGX/Dc/Battery/Power", 'parameter'] = "charged_energy"
            df_system.loc[df_system['parameter'] == "VenusGX/Dc/Battery/Soc", 'parameter'] = "battery_soc"

            df_devices = df_historic[df_historic['dev_group'] != "System_Data"]
            df_devices = df_devices.groupby([
                pd.Grouper('device'),
            ]).sum()
            df_devices[~df_devices.index.str.contains("AC")] = df_devices[
                                                                   ~df_devices.index.str.contains(
                                                                       "AC")] / 1000
            df_devices["parameter"] = df_devices.index

            df_hour = df_devices.append(df_system).reset_index(drop=True)
            df_hour = pd.pivot_table(df_hour, values='avg', columns=['parameter'])
            df_hour['timestamp'] = df['timestamp'].dt.floor('H').values[0]
            df_hour['timestamp'] = df_hour['timestamp'] + datetime.timedelta(hours=added_hours)
            df_hour.index = df_hour['timestamp']
            change = list(df_hour.columns)
            ch_val = {}
            for c in change:
                ch_val[c] = c.lower()
            df_hour = df_hour.rename(columns=ch_val)

            ##Calculate Battery Effect
            ##Calculate system Load
            df_hour['system_load'] = df_hour['consumed_energy'].values[0] - \
                                     df_devices.sum(axis=0, skipna=True).values[0]
            charged_energy_val = df_hour['generated_energy'].values[0] - df_hour['consumed_energy'].values[
                0]
            df_hour['charged_energy'] = charged_energy_val
            if charged_energy_val > 0.0:
                bat.charge_battery(charged_energy_val / 1000.0)
            else:
                bat.discharge_battery(-charged_energy_val / 1000.0)
            df_hour['battery_soc'] = bat.state_of_charge
            if df_full_hour is None:
                df_full_hour = df_hour
            else:
                df_full_hour = df_full_hour.append(df_hour)

        self.latest = ""
        # Add 0 to non existing values
        for d in self.dev_list:
            if d.lower() not in list(df_full_hour.columns):
                self.latest += "No data available, so adding 0-s for" + str(d) + "\n"
                df_full_hour[d.lower()] = 0.0
        df_full_hour = df_full_hour.fillna(0)
        with pd.option_context('display.max_rows', 5, 'display.max_columns', 5):
            self.latest = str(datetime.datetime.now()) +" : "+str(
                df_full_hour[["system_load", "generated_energy", "consumed_energy"]].tail(1).to_json(orient='records'))
        self.latest_forecast = df_full_hour
        self.data.update_forecast(df_full_hour)
