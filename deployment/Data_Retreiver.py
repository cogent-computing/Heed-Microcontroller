import pandas as pd
import datetime
import re
import subprocess
import psutil
from sqlalchemy import create_engine
import sqlalchemy
from psycopg2.extensions import register_adapter
from psycopg2 import extras
import os


import warnings
warnings.filterwarnings('ignore')

class Data_Retreiver:

    def __init__(self, dev_list, sql_user, sql_pw, sql_addr, sql_port, sql_db, reset_time=4):
        # #Init DB
        self.reset_time = reset_time
        db_string = "postgres://" + sql_user + ":" + sql_pw + "@" + sql_addr + ":" + sql_port + "/" + sql_db
        self.db = create_engine(db_string)
        self.dev_list = dev_list
        # register_adapter(dict, extras.Json)
        self.init_db()

    def stop(self):
        self.db.dispose()

    # -------- Inits --------

    def init_db(self):
        # Init Decision Enaction DB
        df_string = "CREATE TABLE IF NOT EXISTS decision_store (id SERIAL PRIMARY KEY, " + \
                    "timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP, " + \
                    "dev_group TEXT, device TEXT, state TEXT, group_est_energy_cons REAL, quota_param1 REAL, quota_param2 REAL)"
        self.db.execute(df_string)

    def init_db_forecast(self):
        # TODO Needs fixing
        df_string = "CREATE TABLE IF NOT EXISTS forecasted_energy_data (id SERIAL PRIMARY KEY, " + \
                    "timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP, " + \
                    "battery_soc REAL, charged_energy REAL, consumed_energy REAL, " + \
                    "generated_energy REAL, system_load REAL"
        for d in self.dev_list:
            df_string += ", " + d + " REAL"
        df_string += " )"
        self.db.execute(df_string)

    def init_db_log(self, df):
        df_string = "CREATE TABLE IF NOT EXISTS logging_data (id SERIAL PRIMARY KEY, " + \
                    "timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP," + \
                    "transmitted BOOLEAN DEFAULT FALSE, message_id REAL"
        for d in list(df.columns):
            df_string += ", " + d + " REAL"
        df_string += " )"
        self.db.execute(df_string)

    # -------- Aggregation and Logging --------

    def get_cpu_temperature(self):
        try:
            process = subprocess.Popen(['"/opt/vc/bin/vcgencmd', 'measure_temp'], stdout=subprocess.PIPE)
            output, _error = process.communicate()
            return float(output[output.index('=') + 1:output.rindex("'")])
        except FileNotFoundError as ex:
            return 0.0

    def get_storage_info(self):
        disk = psutil.disk_usage('/')
        disk_total = disk.total / 2 ** 30  # GiB.
        disk_used = disk.used / 2 ** 30
        disk_free = disk.free / 2 ** 30
        disk_percent_used = disk.percent
        return (disk_percent_used, disk_used, disk_free)

    def get_actions(self, end_date):
        # Priorities
        db_string = "SELECT Count(*) FROM preference_users WHERE timestamp < '%s' " % (end_date)
        ret = self.db.execute(db_string)
        row = ret.fetchone()
        return row[0]

    def create_log(self, curr_ts):
        main_df = None
        # Get System Paramters - Storage; Ping Google;Cov;
        sys_vals = {"mem": psutil.virtual_memory()[2],
                    "cpu": psutil.cpu_percent(),
                    "storage_perc": self.get_storage_info()[0],
                    "storage_free": self.get_storage_info()[2],
                    "temperature": self.get_cpu_temperature(),
                    "user_actions": self.get_actions(curr_ts)
                    }

        sys_df = pd.DataFrame(sys_vals, index=[0])
        # print(sys_df)

        # Get Historic Data for the Day + System paramters (Cons/Gen/Soc)
        df_hist_cons = self.retreive_latest_full_aggregation(curr_ts)
        if df_hist_cons is None:
            return None
        cols = list(df_hist_cons.columns)
        cols = {x: "hist_" + x for x in cols}
        df_hist_cons = df_hist_cons.rename(columns=cols)
        # print(df_hist_cons)

        # Get Forecasted Consumptions/Energy +System paramters (Cons/Gen/Soc)
        df_for = self.retreive_latest_full_forecast(curr_ts)
        if df_for is None:
            return None
        cols = list(df_for.columns)
        cols = {x: "forcast_" + x for x in cols}
        df_for = df_for.rename(columns=cols)
        # print(df_for)

        # Get Quotas for System (AVG)
        df_quotas = self.retreive_latest_quotas(curr_ts)
        if df_quotas is None:
            return None
        quota_dict = {}
        for index, row in df_quotas.iterrows():
            quota_dict["Quota1_" + row["device"]] = row["quota_param1"]
            quota_dict["Quota2_" + row["device"]] = row["quota_param2"]
        df_quotas = pd.DataFrame(quota_dict, index=[0])
        # print(df_quotas)

        # Get Priorities
        df_prior = self.retreive_latest_priority(curr_ts)
        if df_prior is None:
            return None
        df_prior = df_prior.drop(['id', 'timestamp'], axis=1)
        cols = list(df_prior.columns)
        cols = {x: "priority_" + x for x in cols}
        df_prior = df_prior.rename(columns=cols)
        # print(df_prior)

        full_log_df = pd.concat([sys_df, df_hist_cons, df_for, df_quotas, df_prior], axis=1)

        self.save_created_log(curr_ts, full_log_df)

        return full_log_df

    def save_created_log(self, curr_ts, full_log_df):
        self.init_db_log(full_log_df)

        db_string = """INSERT INTO  logging_data (timestamp"""
        for item in list(full_log_df.columns):
            db_string += ", " + item
        db_string += ") VALUES ('" + str(curr_ts) + "'"
        for item in list(full_log_df.columns):
            if full_log_df[item][0] is not None:
                db_string += ", '" + str(full_log_df[item][0]) + "'"
            else:
                db_string += ", 'NaN'"
        db_string += """)"""
        self.db.execute(db_string)

    def get_unsent_logs(self, end_date):
        # Priorities
        db_string = "SELECT * FROM logging_data WHERE timestamp < '%s' AND transmitted = False" % (end_date)
        ret = self.db.execute(db_string)
        df_to_send = pd.DataFrame(ret.fetchall())
        if len(df_to_send) == 0:
            print("No Data Available for unsent logs", end_date, " at: ",
                  datetime.datetime.now())
            return None
        df_to_send.columns = ret.keys()
        # display(df_priority)
        return df_to_send

    def update_log(self, entry_id, msg_id, transmitted):
        # print("Update:",entry_id, msg_id, transmitted)
        db_string = "UPDATE logging_data SET message_id = " + str(
            msg_id) + ",transmitted=" + str(transmitted) + " WHERE transmitted = False and id=" + str(entry_id)
        self.db.execute(db_string)

    def update_mid(self, msg_id):
        db_string = "SELECT id FROM logging_data WHERE transmitted=False AND message_id = " + str(
            msg_id) + " ORDER BY timestamp ASC"
        ret = self.db.execute(db_string)
        row = ret.fetchone()
        if row is None:
            return None
        else:
            self.update_log(row[0], msg_id, True)
            return row[0]

    # -------- Priorities and Misc --------

    def retreive_latest_quotas(self, end_date):
        # Quotas
        db_string = """SELECT t1.device,t1.quota_param1,t1.quota_param2 from decision_store  as t1
                        Inner JOIN
                        (SELECT device, MAX(timestamp) AS MAXDATESTAMP
                           FROM decision_store   GROUP BY device) as t2
                        ON t1.device = t2.device and t1.timestamp = t2.MAXDATESTAMP   
                        WHERE t1.timestamp < '%s'""" % (end_date)
        ret = self.db.execute(db_string)
        df_quotas = pd.DataFrame(ret.fetchall())
        if len(df_quotas) == 0:
            print("No Data Available for quotas", end_date, " at: ",
                  datetime.datetime.now())
            return None
        df_quotas.columns = ret.keys()
        return df_quotas

    def retreive_latest_priority(self, end_date):
        # Priorities
        db_string = "SELECT * FROM preference_users WHERE timestamp < '%s' ORDER BY timestamp DESC LIMIT 1" % (
            end_date)
        ret = self.db.execute(db_string)
        df_priority = pd.DataFrame(ret.fetchall())
        if len(df_priority) == 0:
            print("No Data Available for priorities", end_date, " at: ",
                  datetime.datetime.now())
            return None
        df_priority.columns = ret.keys()
        # display(df_priority)
        return df_priority

    # -------- Current State / Energy Session values --------

    def retreive_latest_full_aggregation(self, end_ts):
        # Find out the total energy predicted to be consumed until the next 6AM
        if end_ts.hour < self.reset_time:
            start_ts = end_ts.replace(hour=self.reset_time - 1, microsecond=0, second=59,
                                      minute=59) - datetime.timedelta(
                days=1)
        else:
            start_ts = end_ts.replace(hour=self.reset_time - 1, microsecond=0, second=59, minute=59)
        # print("Time region:", start_ts, end_ts)
        db_string = """SELECT SUM(system_load)/4 as system_load,SUM(consumed_energy)/4 as consumed_energy, SUM(generated_energy)/4 as generated_energy"""
        int_dev = {x: self.dev_list[x] for x in self.dev_list if x != 'Victron_VenusGX'}
        for dev in int_dev:
            db_string += ", SUM(" + dev + ")/4 as " + dev
        db_string += """ FROM aggregated_energy_data 
        WHERE timestamp BETWEEN '%s' and '%s'""" % (start_ts, end_ts)
        ret = self.db.execute(db_string)
        df_system_for = pd.DataFrame(ret.fetchall())
        if len(df_system_for) == 0:
            print("No Data Available for ", "'aggregated_energy_data'", start_ts, " at: ",
                  datetime.datetime.now())
            return None
        df_system_for.columns = ret.keys()
        return df_system_for

    def retreive_aggregared_values(self, end_ts):
        db_string = "select * from aggregated_energy_data WHERE timestamp < '%s' ORDER BY timestamp DESC LIMIT 1" % (
            end_ts)
        ret = self.db.execute(db_string)
        df = pd.DataFrame(ret.fetchall())
        if len(df) == 0:
            print("No Data Available for ", "'retreive_aggregared_values'", end_ts, " at: ",
                  datetime.datetime.now())
            return None
        df.columns = ret.keys()
        return df

    def retreive_average_vals_for_hour(self, curr_ts, hour, going_back):
        db_string = "SELECT foo.dev_group,foo.device,foo.parameter,AVG(foo.value) FROM " \
                    "(SELECT extract(hour from timestamp) as hour, dev_group,device,parameter,value " \
                    "FROM raw_energy_data WHERE timestamp BETWEEN '%s' AND '%s') AS foo WHERE foo.hour = '%s' " \
                    "GROUP BY dev_group,device,parameter" % (
                        curr_ts - datetime.timedelta(days=going_back), curr_ts, hour)

        ret2 = self.db.execute(db_string)
        df_historic = pd.DataFrame(ret2.fetchall())
        if len(df_historic) == 0:
            print("No Data Available for ", "'retreive_average_vals_for_hour'", curr_ts, " ", hour, " ", going_back,
                  " at: ",
                  datetime.datetime.now())
            return None
        df_historic.columns = ret2.keys()

        # Get average overall values in case missing
        db_string = "SELECT foo.dev_group,foo.device,foo.parameter,AVG(foo.value) FROM " \
                    "(SELECT extract(hour from timestamp) as hour, dev_group,device,parameter,value " \
                    "FROM raw_energy_data ) AS foo " \
                    "GROUP BY dev_group,device,parameter"

        ret = self.db.execute(db_string)
        df_historic_avg = pd.DataFrame(ret.fetchall())
        df_historic_avg.columns = ret2.keys()
        df_historic = pd.merge(df_historic, df_historic_avg, how='outer', on=['dev_group', 'device', 'parameter'])
        df_historic['avg'] = df_historic['avg_x'].combine_first(df_historic['avg_y'])
        df_historic = df_historic.drop(['avg_x', 'avg_y'], axis=1)
        return df_historic

    def retreive_filled_aggre(self, req_ts, period_hist):
        try:
            period = int(req_ts.minute / 15)
            req_ts=req_ts.replace(minute = period*15, second=0,microsecond=0)
            db_string = "SELECT * FROM aggregated_energy_data WHERE timestamp BETWEEN '%s' AND '%s'" % (
                req_ts - datetime.timedelta(days=period_hist), req_ts)
            ret2 = self.db.execute(db_string)
            df_historic = pd.DataFrame(ret2.fetchall())
            df_historic.columns = ret2.keys()
            df_historic['timestamp'] = df_historic['timestamp'].dt.tz_localize(None)
            del df_historic['id']
            # Data range
            days = pd.date_range(start=req_ts - datetime.timedelta(days=period_hist), end=req_ts, freq='15min')
            df_fill = pd.DataFrame({'timestamp': days})
            #result = pd.concat([df_historic,df_fill])
            #print(df_fill.shape)
            #print(df_historic.shape)
            result = df_historic.merge(df_fill,on="timestamp",how="outer")
            #print(result.shape)
            result.index = result['timestamp']
            result.sort_index(inplace=True)
            result = result.interpolate()
            result = result.fillna(0)
            return result
        except ValueError as ex:
            print("Value Error probably not data avilable for period:> ",req_ts, " ",period_hist," Error:",ex)
            return None

    def retreive_latest_raw_system_snapshot(self, end_ts):
        # Latest Snapshot of System
        if end_ts.hour < self.reset_time:
            start_ts = end_ts.replace(hour=self.reset_time, microsecond=0, second=0, minute=0) - datetime.timedelta(
                days=1)
        else:
            start_ts = end_ts.replace(hour=self.reset_time, microsecond=0, second=0, minute=0)
        # print("Time region:", start_ts, end_ts)
        db_string = """SELECT max(timestamp) as timestamp, parameter, max(value) as value FROM raw_energy_data 
                    WHERE dev_group = 'System_Data' AND timestamp BETWEEN '%s' AND '%s' group by parameter""" % (
            start_ts, end_ts)
        ret = self.db.execute(db_string)
        df_system = pd.DataFrame(ret.fetchall())
        if len(df_system) == 0:
            print("No Data Available for ", "'retreive_latest_raw_system_snapshot'", end_ts, " at: ",
                  datetime.datetime.now())
            return None
        df_system.columns = ret.keys()
        return df_system

    def retreive_average_P_lights(self, dev, end_ts):
        # Is acutall 0.95 Quantile value
        db_string = """SELECT """ + dev + """ FROM aggregated_energy_data
                   WHERE """ + dev + """ > 0 and """ + dev + """ <  1000 AND timestamp < '%s'""" % (end_ts)
        ret = self.db.execute(db_string)
        df = pd.DataFrame(ret.fetchall())
        if len(df) == 0:
            print("No Data Available for ", "'retreive_average_P_lights'", dev, end_ts, " at: ",
                  datetime.datetime.now())
            return 0.0
        df.columns = ret.keys()
        quant_95 = df[dev.lower()].quantile(0.95)
        return quant_95

    def retreive_AC_Session(self, dev, end_ts):
        # get latest session value, add to it and then update the plan
        if end_ts.hour < self.reset_time:
            start_ts = end_ts.replace(hour=self.reset_time - 1, microsecond=0, second=59,
                                      minute=59) - datetime.timedelta(days=1)
        else:
            start_ts = end_ts.replace(hour=self.reset_time, microsecond=0, second=1, minute=0)
        # print("Time region:", start_ts, end_ts)
        db_string = """SELECT MAX(value)
               FROM raw_state_data
               WHERE device = '""" + dev + """' AND parameter = 'AC_Day_Energy_session'
               and timestamp BETWEEN '%s' and '%s'""" % (start_ts, end_ts)
        ret = self.db.execute(db_string)
        AC_Session = ret.fetchone()[0]
        return AC_Session

    def retreive_AC_Energy(self, dev, date_time):
        # TODO Return actual energy usage measured
        return 0.0

    def retreive_Light_Session(self, dev, end_ts):
        # get latest session value, add to it and then update the plan
        if end_ts.hour < self.reset_time:
            start_ts = end_ts.replace(hour=self.reset_time - 1, microsecond=0, second=59,
                                      minute=59) - datetime.timedelta(days=1)
        else:
            start_ts = end_ts.replace(hour=self.reset_time, microsecond=0, second=1, minute=0)
        # print("Time region:",start_ts,end_ts)
        db_string = """SELECT MAX(value)
                FROM raw_state_data
                WHERE device = '""" + dev + """' AND parameter = 'LED_NL_session'
                and timestamp BETWEEN '%s' and '%s'""" % (start_ts, end_ts)
        ret = self.db.execute(db_string)
        NL_Session = ret.fetchone()[0]
        if NL_Session is None:
            NL_Session = 0.0
        db_string = """SELECT MAX(value)
                FROM raw_state_data
                WHERE device = '""" + dev + """' AND parameter = 'LED_BL_session'
                and timestamp BETWEEN '%s' and '%s'""" % (start_ts, end_ts)
        ret = self.db.execute(db_string)
        BL_Session = ret.fetchone()[0]
        return BL_Session, NL_Session

    def retreive_Light_Energy(self, dev, date_time):
        # TODO Return actual Energy
        return 0.0, 0.0

    # -------- Forecasting ---------

    def update_forecast(self, df):
        # drop all previosu predictions
        # db_string = "DELETE FROM forecasted_energy_data"
        # self.db.execute(db_string)

        # TODO Modify so it overwrites and not appends
        df.to_sql('forecasted_energy_data', con=self.db, if_exists='replace', index=False)

    def retreive_latest_full_forecast(self, start_ts):
        # Find out the total energy predicted to be consumed until the next 6AM
        if start_ts.hour < self.reset_time:
            end_ts = start_ts.replace(hour=self.reset_time, microsecond=0, second=1, minute=0)
        else:
            end_ts = start_ts.replace(hour=self.reset_time, microsecond=0, second=0, minute=0) + datetime.timedelta(
                days=1)
        # print("Time region:", start_ts, end_ts)
        db_string = """SELECT SUM (system_load) as system_load, SUM(consumed_energy) as consumed_energy, SUM(generated_energy) as generated_energy"""
        int_dev = {x: self.dev_list[x] for x in self.dev_list if x != 'Victron_VenusGX'}
        for dev in int_dev:
            db_string += ", SUM(" + dev + ") as " + dev
        db_string += """ FROM forecasted_energy_data 
        WHERE timestamp BETWEEN '%s' and '%s'""" % (start_ts, end_ts)
        ret = self.db.execute(db_string)
        df_system_for = pd.DataFrame(ret.fetchall())
        if len(df_system_for) == 0:
            print("No Data Available for ", "'retreive_latest_full_forecast'", start_ts, " at: ",
                  datetime.datetime.now())
            return None
        df_system_for.columns = ret.keys()
        return df_system_for

    def retreive_latest_forecast(self, start_ts):
        # Find out the total energy predicted to be consumed until the next 6AM
        if start_ts.hour < self.reset_time:
            end_ts = start_ts.replace(hour=self.reset_time, microsecond=0, second=1, minute=0)
        else:
            end_ts = start_ts.replace(hour=self.reset_time, microsecond=0, second=0, minute=0) + datetime.timedelta(
                days=1)
        # print("Time region:", start_ts, end_ts)
        db_string = """SELECT SUM(system_load) as system_load, SUM(generated_energy) as generated_energy 
        FROM forecasted_energy_data 
        WHERE timestamp BETWEEN '%s' and '%s'""" % (start_ts, end_ts)
        ret = self.db.execute(db_string)
        df_system_for = pd.DataFrame(ret.fetchall())
        if len(df_system_for) == 0:
            print("No Data Available for ", "'retreive_latest_forecast'", start_ts, " at: ",
                  datetime.datetime.now())
            return None
        df_system_for.columns = ret.keys()
        return df_system_for

    def get_total_energy_for_group(self, group, start_ts):
        # Gather How much Energy It would consume
        if start_ts.hour < self.reset_time:
            end_ts = start_ts.replace(hour=self.reset_time - 1, microsecond=0, second=59, minute=59)
        else:
            end_ts = start_ts.replace(hour=self.reset_time, microsecond=0, second=1, minute=0) + datetime.timedelta(
                days=1)
        # print("Time region:", start_ts, end_ts)
        db_string = """SELECT"""
        for d in group:
            db_string += " SUM(" + d + ") as " + d + ","
        db_string = db_string[: -1] + """ FROM forecasted_energy_data
               WHERE timestamp BETWEEN '%s' and '%s'""" % (start_ts, end_ts)
        ret = self.db.execute(db_string)
        df_dev_sums = pd.DataFrame(ret.fetchall())
        if len(df_dev_sums) == 0:
            print("No Data Available for ", "'get_total_energy_for_group'", group, start_ts, " at: ",
                  datetime.datetime.now())
            return None
        df_dev_sums.columns = ret.keys()
        return df_dev_sums

    # -------- Decisions and Quotas --------

    def save_decision(self, decision):
        # print("saving decision")
        save_when = [True]  # [True, False]
        for group in decision:
            # print(group)
            for dev in decision[group]['device_const']:
                if len(decision[group]['device_const'][dev]) == 3:
                    if decision[group]['device_const'][dev][2] in save_when:  # If needs updating
                        # print("Save for", group, dev)
                        db_string = """INSERT INTO  decision_store (timestamp, dev_group, device, state, 
                        group_est_energy_cons, quota_param1, quota_param2) VALUES('""" + str(decision[group]["timestamp"]) + """', 
                                         '""" + group + """', 
                                           '""" + dev + """', 
                                         '""" + decision[group]["state"] + """', 
                                         '""" + str(decision[group]["energy_est_used_total"]) + """',
                                          '""" + str(decision[group]['device_const'][dev][0]) + """', 
                                           '""" + str(decision[group]['device_const'][dev][1]) + """')"""
                        self.db.execute(db_string)
                elif len(decision[group]['device_const'][dev]) == 2:
                    if decision[group]['device_const'][dev][1] in save_when:  # If needs updating
                        # print("Save for", group, dev)
                        db_string = """INSERT INTO  decision_store (timestamp, dev_group, device, state, 
                            group_est_energy_cons, quota_param1) VALUES('""" + str(decision[group]["timestamp"]) + """', 
                                             '""" + group + """', 
                                               '""" + dev + """', 
                                             '""" + decision[group]["state"] + """', 
                                             '""" + str(decision[group]["energy_est_used_total"]) + """',
                                              '""" + str(decision[group]['device_const'][dev][0]) + """')"""
                        self.db.execute(db_string)

    def get_latest_quota(self, dev, end_ts):
        db_string = """SELECT quota_param1, quota_param2 
                        FROM decision_store where device = '""" + dev + """' and timestamp < '%s'
                        ORDER BY timestamp DESC Limit 1""" % (end_ts)
        ret = self.db.execute(db_string)
        res = ret.fetchone()
        if len(res) < 2:
            print("No Known Quota")
            return None, None
        return res[0], res[1]

        # Failed Pandas easy way attempt
        # df_dec = pd.DataFrame.from_dict(decision).T
        # df_dec['device_group'] = df_dec.index
        #
        # df_dec.to_sql("decision_store", con=self.db, if_exists='append', index=False,
        #               dtype={"device_group": sqlalchemy.VARCHAR, "constraining_factor": sqlalchemy.FLOAT,
        #                      "device_const": extras.Json,
        #                      "energy_est_used_total": sqlalchemy.FLOAT, "state": sqlalchemy.VARCHAR,
        #                      "timestamp": sqlalchemy.DateTime()})


def full_test_data(data, dev_light, dev_socket, group, hour):
    pd.set_option('display.max_columns', 30)
    dt_ts = datetime.datetime.now()
    print("--Forecast--\n", data.retreive_latest_forecast(dt_ts).head(5))
    print("--Raw Sys--\n", data.retreive_latest_raw_system_snapshot(dt_ts).head(5))
    print("--Priority--\n", data.retreive_latest_priority(dt_ts).head(5))
    print("--Group Energy--\n", data.get_total_energy_for_group(group, dt_ts))
    print("--Aggregated Values --\n", data.retreive_aggregared_values(dt_ts))
    print("--AVG for Hour Values --\n", data.retreive_average_vals_for_hour(dt_ts, hour))
    print("--Average P Light--\n", data.retreive_average_P_lights(dev_light, dt_ts))
    print("--AC Session--\n", data.retreive_AC_Session(dev_socket, dt_ts))
    print("--AC Energy--\n", data.retreive_AC_Energy(dev_socket, dt_ts))
    print("--Light Session--\n", data.retreive_Light_Session(dev_light, dt_ts))
    print("--Light Energy--\n", data.retreive_Light_Energy(dev_light, dt_ts))
    print("--Quota Latest Light--\n", data.get_latest_quota(dev_light, dt_ts))
    print("--Quota Latest Socket --\n", data.get_latest_quota(dev_socket, dt_ts))

    dec = {'nursery1_lights': {'state': 'Unconstrained', 'energy_est_used_total': 132.30215890353352,
                               'constraining_factor': 1.0, 'device_const': {'Nursery_1A_CPE_No_1': (4320, 4320, False),
                                                                            'Nursery_1A_CPE_No_2': (4320, 4320, False),
                                                                            'Nursery_1B_CPE_No_3': (4320, 4320, False),
                                                                            'Nursery_1B_CPE_No_4': (4320, 4320, False),
                                                                            'Nursery_1C_CPE_No_5': (4320, 4320, False),
                                                                            'Nursery_1C_CPE_No_6': (4320, 4320, True)},
                               'timestamp': '2020-03-04 14:01:09.698676'},
           'nursery2_lights': {'state': 'Unconstrained', 'energy_est_used_total': 338.3709751064285,
                               'constraining_factor': 1.0, 'device_const': {'Nursery_2A_CPE_No_7': (4320, 4320, False),
                                                                            'Nursery_2A_CPE_No_8': (4320, 4320, False),
                                                                            'Nursery_2B_CPE_No_9': (4320, 4320, False),
                                                                            'Nursery_2B_CPE_No_10': (4320, 4320, False),
                                                                            'Nursery_2C_CPE_No_11': (4320, 4320, False),
                                                                            'Nursery_2C_CPE_No_12': (
                                                                                4320, 4320, False)},
                               'timestamp': '2020-03-04 14:01:17.163449'},
           'playground_lights': {'state': 'Unconstrained', 'energy_est_used_total': 496.9524094664317,
                                 'constraining_factor': 1.0, 'device_const': {'Playground_No_1': (4320, 4320, False),
                                                                              'Playground_No_2': (4320, 4320, False),
                                                                              'Playground_No_3': (4320, 4320, False),
                                                                              'Playground_No_4': (4320, 4320, False),
                                                                              'Playground_No_5': (4320, 4320, False)},
                                 'timestamp': '2020-03-04 14:01:23.896520'},
           'playground_sockets': {'state': 'Unconstrained', 'energy_est_used_total': 54.497536810310116,
                                  'constraining_factor': 1.0,
                                  'device_const': {'Playground_AC_socket_No_1': (1200000, False),
                                                   'Playground_AC_Socket_No_2': (1200000, False)},
                                  'timestamp': '2020-03-04 14:01:26.412130'},
           'nursery1_sockets': {'state': 'Unconstrained', 'energy_est_used_total': 25.474201030282288,
                                'constraining_factor': 1.0,
                                'device_const': {'Nursery_AC_Socket_1A_No_1': (1200000, False),
                                                 'Nursery_AC_Socket_1A_No_2': (1200000, False),
                                                 'Nursery_AC_Socket_1B': (1200000, False),
                                                 'Nursery_AC_Socket_1C': (1200000, False)},
                                'timestamp': '2020-03-04 14:01:31.457445'},
           'nursery2_sockets': {'state': 'Unconstrained', 'energy_est_used_total': 56.17494375631213,
                                'constraining_factor': 1.0,
                                'device_const': {'Nursery_AC_Socket_2A_No_1': (1200000, False),
                                                 'Nursery_AC_Socket_2A_No_2': (1200000, False),
                                                 'Nursery_AC_Socket_2B': (1200000, False),
                                                 'Nursery_AC_Socket_2C': (1200000, False)},
                                'timestamp': '2020-03-04 14:01:36.379328'}}

    data.save_decision(dec)
