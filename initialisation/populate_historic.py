import asyncio, telnetlib3
import difflib
import re
import sys
import traceback
from pprint import pprint

import datetime
import time
import json
from sqlalchemy import create_engine
from sqlalchemy_utils import database_exists, create_database
import os
import pandas as pd

dir_path = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))  # Core directory always
with open(os.path.join(os.path.join(dir_path, 'config'), 'runner_config.json')) as json_file:
    json_data = json.load(json_file)

devices = json_data["devices"]

# Data Retreiver
sql_user = json_data["sql_user"]
sql_pw = json_data["sql_pw"]
sql_db = json_data["sql_db"]
sql_addr = json_data["sql_addr"]
sql_port = json_data["sql_port"]

sql_table = json_data["sql_raw_energy"]
sql_table2 = json_data["sql_raw_state"]
sql_table3 = json_data["sql_preference"]

sql_aggregate =  json_data["sql_aggregate"]
sql_decision = json_data["sql_decision"]

devices = json_data["devices"]

if "Victron_VenusGX" in devices:
    del devices["Victron_VenusGX"]
allocation = json_data["allocation"]
forecast_sql = json_data["sql_forecast"]

print("Starting Population...")

# Making initial connection object with Database
db_string = "postgres://" + sql_user + ":" + sql_pw + "@" + sql_addr + ":" + sql_port + "/" + sql_db
db = create_engine(db_string)

curr_time = datetime.datetime.now()
curr_time = curr_time - datetime.timedelta(minutes=(curr_time.minute % 15),
                                           seconds=curr_time.second,
                                           microseconds=curr_time.microsecond)

similarity = {
    "Streetlight_No_1": ['Streetlight 1 CPE LED1_P', 'Streetlight 1 CPE LED2_P', 'Streetlight 1 CPE LED3_P'],
    "Streetlight_No_2": ['Streetlight 2 CPE LED1_P', 'Streetlight 2 CPE LED2_P', 'Streetlight 2 CPE LED3_P'],
    "Streetlight_No_3": ['Streetlight 3 CPE LED1_P', 'Streetlight 3 CPE LED2_P', 'Streetlight 3 CPE LED3_P'],
    "Playground_No_1": ['Playground CPE1 LED1_P', 'Playground CPE1 LED2_P', 'Playground CPE1 LED3_P'],
    "Playground_No_2": ['Playground CPE2 LED1_P', 'Playground CPE2 LED2_P', 'Playground CPE2 LED3_P'],
    "Playground_No_3": ['Playground CPE3 LED1_P', 'Playground CPE3 LED2_P', 'Playground CPE3 LED3_P'],
    "Playground_No_4": ['Playground CPE4 LED1_P', 'Playground CPE4 LED2_P', 'Playground CPE4 LED3_P'],
    "Playground_No_5": ['Playground CPE5 LED1_P', 'Playground CPE5 LED2_P', 'Playground CPE5 LED3_P'],
    "Playground_AC_socket_No_1": ['Playground S1 vRELAY1_LVL'],
    "Playground_AC_Socket_No_2": ['Playground S2 vRELAY1_LVL'],
    "Nursery_AC_Socket_1A_No_1": ['Nur 1A S1 vRELAY1_LVL'],
    "Nursery_AC_Socket_1A_No_2": ['Nur 1A S2 vRELAY1_LVL'],
    "Nursery_AC_Socket_1B": ['Nur 1B S1 vRELAY1_LVL'],
    "Nursery_AC_Socket_1C": ['Nur 1C S1 vRELAY1_LVL'],
    "Nursery_1A_CPE_No_1": ['Nur 1A CPE1 LED1_P', 'Nur 1A CPE1 LED2_P', 'Nur 1A CPE1 LED3_P'],
    "Nursery_1A_CPE_No_2": ['Nur 1A CPE2 LED1_P', 'Nur 1A CPE2 LED2_P', 'Nur 1A CPE2 LED3_P'],
    "Nursery_1B_CPE_No_3": ['Nur 1B CPE3 LED1_P', 'Nur 1B CPE3 LED2_P', 'Nur 1B CPE3 LED3_P'],
    "Nursery_1B_CPE_No_4": ['Nur 1B CPE4 LED1_P', 'Nur 1B CPE4 LED2_P', 'Nur 1B CPE4 LED3_P'],
    "Nursery_1C_CPE_No_5": ['Nur 1C CPE5 LED1_P', 'Nur 1C CPE5 LED2_P', 'Nur 1C CPE5 LED3_P'],
    "Nursery_1C_CPE_No_6": ['Nur 1C CPE6 LED1_P', 'Nur 1C CPE6 LED2_P', 'Nur 1C CPE6 LED3_P'],
    "Nursery_AC_Socket_2A_No_1": ['Nur 2A S1 vRELAY1_LVL'],
    "Nursery_AC_Socket_2A_No_2": ['Nur 2A S2 vRELAY1_LVL'],
    "Nursery_AC_Socket_2B": ['Nur 2B S1 vRELAY1_LVL'],
    "Nursery_AC_Socket_2C": ['Nur 2C S1 vRELAY1_LVL'],
    "Nursery_2A_CPE_No_7": ['Nur 2A CPE7 LED1_P', 'Nur 2A CPE7 LED2_P', 'Nur 2A CPE7 LED3_P'],
    "Nursery_2A_CPE_No_8": ['Nur 2A CPE8 LED1_P', 'Nur 2A CPE8 LED2_P', 'Nur 2A CPE8 LED3_P'],
    "Nursery_2B_CPE_No_9": ['Nur 2B CPE9 LED1_P', 'Nur 2B CPE9 LED2_P', 'Nur 2B CPE9 LED3_P'],
    "Nursery_2B_CPE_No_10": ['Nur 2B CPE10 LED1_P', 'Nur 2B CPE10 LED2_P', 'Nur 2B CPE10 LED3_P'],
    "Nursery_2C_CPE_No_11": ['Nur 2C CPE11 LED1_P', 'Nur 2C CPE11 LED2_P', 'Nur 2C CPE11 LED3_P'],
    "Nursery_2C_CPE_No_12": ['Nur 2C CPE12 LED1_P', 'Nur 2C CPE12 LED2_P', 'Nur 2C CPE12 LED3_P']
}

var_alloc = {'VenusGX/Ac/Consumption/L1/Power': "AC_consumption_W",
             'VenusGX/Dc/Pv/Power': "PV_power_W",
             'VenusGX/Dc/Battery/Soc': "State_of_charge",
             'VenusGX/Dc/Battery/Power': ["Discharged_energy_W", "Charged_energy_W"]
             }

date_range = [curr_time - datetime.timedelta(minutes=x * 15) for x in range(24 * 4)]

df = pd.read_csv("../data/microgrid_processed_august.csv", error_bad_lines=True)
cols = list(df.columns)
cols.remove("timestamp")
for col in cols:
    df[col] = df[col].astype(float, errors='raise')
df['timestamp'] = pd.to_datetime(df['timestamp'], format='%Y/%m/%d %H:%M:%S', errors='raise')
df.index = df['timestamp']

df_system = df[
    ['Pot_PV_power_W', 'AC_consumption_W', 'Charged_energy_W', 'Discharged_energy_W', 'PV_power_W', 'State_of_charge']]
# with pd.option_context('display.max_rows', None, 'display.max_columns', None):
#     print(df_system.head(2))

cols = [x for x in cols if 'vRELAY1_LVL' in x or 'CPE' in x]
df_devices = df[cols]
# with pd.option_context('display.max_rows', None, 'display.max_columns', None):
#     print(df_devices.head(2))
print(date_range)

for d in date_range:
    # Populate System
    # "System_Data" "Victron_VenusGX"
    for var in var_alloc:
        print("Inserting for date: ", d, " Group: ", "System_Data", " Dev: ", var)
        if len(var_alloc[var])==2:
            insert_mean = df[df['timestamp'].dt.hour == d.hour][var_alloc[var][1]].mean() - df[df['timestamp'].dt.hour == d.hour][var_alloc[var][0]].mean()
        else:
            insert_mean = df[df['timestamp'].dt.hour == d.hour][var_alloc[var]].mean()
        db_string = """INSERT INTO  """ + sql_table + """(timestamp,dev_group, device, parameter, value)
                            VALUES('""" + str(d) + """',
                            '""" + "System_Data" + """',
                                   '""" + "Victron_VenusGX" + """',
                                 '""" + var + """',
                                 '""" + str(insert_mean) + """')"""
        db.execute(db_string)
    # Populate Devices
    for alloc in allocation:
        for dev in allocation[alloc]:
            print("Inserting for date: ", d, " Group: ", alloc, " Dev: ", dev)
            for param in similarity[dev]:
                insert_mean = df[df['timestamp'].dt.hour == d.hour][param].mean()
                if "light" in alloc.lower():
                    insert_mean = insert_mean * 1000
                db_string = """INSERT INTO  """ + sql_table + """(timestamp,dev_group, device, parameter, value)
                                    VALUES('""" + str(d) + """',
                                    '""" + alloc + """',
                                           '""" + dev + """',
                                         '""" + param.split(" ")[-1] + """',
                                         '""" + str(insert_mean) + """')"""
                db.execute(db_string)
            # Insert States
            if "light" in alloc.lower():
                for param in ['LED_BL_remain', 'LED_NL_remain']:
                    db_string = """INSERT INTO  """ + sql_table2 + """(timestamp,dev_group, device, parameter, value)
                                        VALUES('""" + str(d) + """',
                                               '""" + alloc + """',
                                               '""" + dev + """',
                                             '""" + param + """',
                                             '""" + str(4320) + """')"""
                    db.execute(db_string)
                for param in ['LED_BL_session', 'LED_NL_session', ]:
                    db_string = """INSERT INTO  """ + sql_table2 + """(timestamp,dev_group, device, parameter, value)
                                        VALUES('""" + str(d) + """',
                                                '""" + alloc + """',
                                               '""" + dev + """',
                                             '""" + param + """',
                                             '""" + str(0) + """')"""
                    db.execute(db_string)
            else:
                db_string = """INSERT INTO  """ + sql_table2 + """(timestamp,dev_group, device, parameter, value)
                                                        VALUES('""" + str(d) + """',
                                                                '""" + alloc + """',
                                                               '""" + dev + """',
                                                             '""" + 'AC_Day_Energy_session' + """',
                                                             '""" + str(0) + """')"""
                db.execute(db_string)
                db_string = """INSERT INTO  """ + sql_table2 + """(timestamp,dev_group, device, parameter, value)
                                                        VALUES('""" + str(d) + """',
                                                                '""" + alloc + """',
                                                               '""" + dev + """',
                                                             '""" + 'AC_Day_Energy_remain' + """',
                                                             '""" + str(1000) + """')"""
                db.execute(db_string)
