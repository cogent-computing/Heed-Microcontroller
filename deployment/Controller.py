# Step 1 - Gather Data

import pandas as pd
import datetime
import re
import json
import os
import unittest
import time

# Own Imports
from deployment.Control_Enactor import Enactor
from deployment.Data_Retreiver import Data_Retreiver


class Controller:

    def __init__(self, data_ret, enact, allocation, reset_time=4):
        self.data_ret = data_ret
        self.enact = enact
        self.allocation = allocation
        self.reset_time = reset_time
        self.latest = "Initilised"

    def stop(self):
        self.enact.stop()
        self.data_ret.stop()


    def sort_plan_for_dev_socket(self, dev, limit, forecast, date_time):
        # print("Sorting Plan for Device: ", dev, " With Limit: ", str(limit), " and Estiamte: ", str(forecast))
        # get latest session value, add to it and then update the plan
        AC_Session = self.data_ret.retreive_AC_Session(dev, date_time)
        if AC_Session is None:
            AC_Session = self.data_ret.retreive_AC_Energy(dev, date_time)
        # print("AC Session:",AC_Session)
        change = False
        # if 1 then make it generous
        if limit >= 1:
            change = self.enact.enact_socket_plan(dev, 1200000)  # 1,200,000 is equivalent to 20kW
            return 1200000, change
        elif limit <= 0.0:
            change = self.enact.enact_socket_plan(dev, 0)
            return 0, change
        else:
            p_available = forecast * limit * 1.1 / 0.017
            # print("Power Availalbe", p_available)
            change = self.enact.enact_socket_plan(dev, AC_Session + p_available)
        return AC_Session + p_available, change

    def sort_plan_for_dev_light(self, dev, limit, forecast, date_time):
        # print("Sorting Plan for Device: ", dev, " With Limit: ", str(limit), " and Estiamte: ", str(forecast))
        # get latest session value, add to it and then update the plan

        # Nightlight and Brightlight
        BL_Session, NL_Session = self.data_ret.retreive_Light_Session(dev, date_time)
        if NL_Session is None:
            _, NL_Session = self.data_ret.retreive_Light_Energy(dev, date_time)
        if BL_Session is None:
            BL_Session, _ = self.data_ret.retreive_Light_Energy(dev, date_time)
        # print("Light Sessions: ", BL_Session, NL_Session)
        change = False
        # if 1 then make it generous
        if limit >= 1:
            change = self.enact.enact_light_plan(dev, 4320, 4320)
            return 4320, 4320, change
        elif limit <= 0.0:
            change = self.enact.enact_light_plan(dev, 0, 0)
            return 0, 0, change
        else:
            avg_p_cons = self.data_ret.retreive_average_P_lights(dev, date_time)
            if avg_p_cons is None:
                # print(" avg_p_cons Not found")
                avg_p_cons = 5.0
            avg_p_cons = avg_p_cons / 60 / 3  # to get minutely values for dimmed
            # print("Average P Cons", avg_p_cons)
            # Divided by three as the NL is half as bright than the BL
            minutes_available = forecast * limit / avg_p_cons * 1.1  # add 10%
            # print("Mins Availalbe: ", minutes_available)

            change = self.enact.enact_light_plan(dev, BL_Session + minutes_available / 2,
                                                 NL_Session + minutes_available)
            return BL_Session + minutes_available / 2, NL_Session + minutes_available, change

    def sort_lights(self, dev, remaining_energy, date_time):
        # Gather How much Energy It would consume
        df_dev_sums = self.data_ret.get_total_energy_for_group(self.allocation[dev], date_time)

        if df_dev_sums is None:
            self.latest = "---- Mini Fault: Group Energy Returned None, Considering No Values so 0"
            total_energy_used_f = 0.0
        else:
            # display(df_dev_sums)
            total_energy_used_f = df_dev_sums.sum(axis=1)[0]

        dev_info = {}
        if total_energy_used_f * 1.2 > remaining_energy:
            # Constrain devs and calculate
            const_rate = 1.0  # All available
            if total_energy_used_f != 0.0:
                const_rate = remaining_energy / total_energy_used_f / 1.2
            # print("Constraint Rate: " + str(const_rate))
            for d in self.allocation[dev]:
                # print("-----------------" + d + "------------------")
                dev_info[d] = self.sort_plan_for_dev_light(d, const_rate, df_dev_sums[d.lower()].values[0], date_time)
            return 0, {"state": "Constrained", "energy_est_used_total":
                total_energy_used_f * 1.2, "constraining_factor": const_rate, "device_const": dev_info}
        else:
            for d in self.allocation[dev]:
                # print("-----------------" + d + "------------------")
                dev_info[d] = self.sort_plan_for_dev_light(d, 1.0, df_dev_sums[d.lower()].values[0], date_time)
            return remaining_energy - total_energy_used_f * 1.2, {"state": "Unconstrained", "energy_est_used_total":
                total_energy_used_f, "constraining_factor": 1.0, "device_const": dev_info}

    def sort_sockets(self, dev, remaining_energy, date_time):
        # Gather How much Energy It would consume
        df_dev_sums = self.data_ret.get_total_energy_for_group(self.allocation[dev], date_time)

        if df_dev_sums is None:
            self.latest = "---- Mini Fault: Group Energy Returned None, Considering No Values so 0"
            total_energy_used_f = 0.0
        else:
            # display(df_dev_sums)
            total_energy_used_f = df_dev_sums.sum(axis=1)[0]
        dev_info = {}
        if total_energy_used_f * 1.2 > remaining_energy:
            # Constrain devs and calculate
            const_rate = 1.0  # All available
            if total_energy_used_f != 0.0:
                const_rate = remaining_energy / total_energy_used_f / 1.2
            # print("Constraint Rate: " + str(const_rate))
            for d in self.allocation[dev]:
                # print("-----------------" + d + "------------------")
                dev_info[d] = self.sort_plan_for_dev_socket(d, const_rate, df_dev_sums[d.lower()].values[0], date_time)
            return 0, {"state": "Constrained", "energy_est_used_total":
                total_energy_used_f * 1.2, "constraining_factor": const_rate, "device_const": dev_info}
        else:
            for d in self.allocation[dev]:
                # print("-----------------" + d + "------------------")
                dev_info[d] = self.sort_plan_for_dev_socket(d, 1.0, df_dev_sums[d.lower()].values[0], date_time)
            return remaining_energy - total_energy_used_f * 1.2, {"state": "Unconstrained", "energy_est_used_total":
                total_energy_used_f, "constraining_factor": 1.0, "device_const": dev_info}

    def sort_device(self, dev, remaining_energy, date_time):
        if "ights" in dev:
            return self.sort_lights(dev, remaining_energy, date_time)
        else:
            return self.sort_sockets(dev, remaining_energy, date_time)

    def revert_to_standard(self, latest_ts):
        self.latest = "Checking Time for revert \n"
        if latest_ts.hour >= self.reset_time - 1 and latest_ts.hour <= self.reset_time + 1:
            self.latest = "Within 1 hour range on reset, don't panic yet\n"
        else:
            self.latest = "Reverting to standard setup as no data is available\n"
            decision_summary = {}
            for a in self.allocation:
                dev_info = {}
                for dev in self.allocation[a]:
                    if "ights" in a:
                        dev_info[dev] = (4329, 4320, self.enact.enact_light_plan(dev, 4320, 4320))
                    else:
                        dev_info[dev] = (1200000, self.enact.enact_socket_plan(dev, 1200000))
                decision = {"state": "Unconstrained", "energy_est_used_total":
                    0, "constraining_factor": 1.0, "device_const": dev_info, "timestamp": latest_ts}
                decision_summary[a] = decision
            self.latest += "Decisions: "+str(decision_summary)+"\n"
            self.data_ret.save_decision(decision_summary)

    def do_step(self, latest_ts = datetime.datetime.now()):
        df_priority = self.data_ret.retreive_latest_priority(latest_ts)

        df_system = self.data_ret.retreive_latest_raw_system_snapshot(latest_ts)
        if df_system is None or df_system.isnull().values.any():
            self.latest = "---- Mini Fault: Historic Returned None, Waiting..."
            self.revert_to_standard(latest_ts)
            return None
        # When Deciding
        # latest_ts = datetime.datetime.now()

        self.latest ="Latest Data From: " + str(latest_ts)+"\n"

        df_system_for = self.data_ret.retreive_latest_forecast(latest_ts)
        if df_system_for is None or df_system_for.isnull().values.any():
            self.latest = "---- Mini Fault: Forecast Returned None, Waiting..."
            self.revert_to_standard(latest_ts)
            return None
        system_load = df_system_for["system_load"][0]
        if system_load < 0:
            system_load = 0
        gen_energy = df_system_for["generated_energy"][0]
        battery_soc = df_system[df_system['parameter'] == "VenusGX/Dc/Battery/Soc"]["value"].values[0]

        self.latest +="-------Energy State--------\n"
        remaining_energy = gen_energy - system_load * 1.2 + (
                battery_soc - 40.0) * 21.1 * 1000 / 100 * 0.9  # system load + 20%; remaining battery SOC, with 90% gettable at a 21kw battery
        self.latest +="Generated energy: " + str(gen_energy)+"\n"
        self.latest +="System Load: " + str(system_load)+"\n"
        self.latest +="Battery SoC: " + str(battery_soc)+"\n"
        self.latest +="Remaining Energy: " + str(remaining_energy)+"\n"

        # display(df_priority)
        # Get Value pair from Priority:
        if df_priority is None:
            self.latest +="Priority Returned None, Considering Standard..."+"\n"
            prior_values = {0: 'nursery1_lights', 4: 'nursery1_sockets', 1: 'nursery2_lights', 5: 'nursery2_sockets',
                            3: 'playground_lights', 6: 'playground_sockets'}
        else:
            prior_values = {}
            for label, content in df_priority.items():
                if label not in ['id', 'timestamp']:
                    prior_values[content[0]] = label
        self.latest +=str(prior_values)+"\n"

        #remaining_energy = 0  # Overwrite for testing

        decision_summary = {}

        for key in sorted(prior_values.keys()):
            self.latest +="------------------------------------------------\n"
            self.latest +="For Device: " + prior_values[key] + " with energy avialable: " + str(remaining_energy)+"\n"
            remaining_energy, decision = self.sort_device(prior_values[key], remaining_energy, latest_ts)
            decision['timestamp'] = str(latest_ts)
            decision_summary[prior_values[key]] = decision
            self.latest +="Decisions: "+str(decision)+"\n"
            self.latest +="Remaining: "+str(remaining_energy)+"\n"

        self.latest +="Decision Summary: \n"
        self.latest +=str(decision_summary)+"\n"
        self.data_ret.save_decision(decision_summary)

    def getLatest(self):
        return "Controller : "+self.latest