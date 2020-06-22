import sys
import pandas as pd
import datetime
import time
import json
from sqlalchemy import create_engine
import os
import threading


# Define class that reads aggregates raw data and saves it
class Aggregator:

    def __init__(self,dev_list,sql_table,sql_table_raw,sql_addr,sql_port, sql_user, sql_pw, sql_db):

            self.dev_list = dev_list
            self.sql_table = sql_table
            self.sql_table_raw = sql_table_raw
            # Settign Up SQL Credentials and details

            # Making intiial connection object with Database
            db_string = "postgres://" + sql_user + ":" + sql_pw + "@" + sql_addr + ":" + sql_port + "/" + sql_db
            self.db = create_engine(db_string)

            # Make sure table exists and if not create it

            df_string = "CREATE TABLE IF NOT EXISTS " + self.sql_table + " (id SERIAL PRIMARY KEY, " + \
                        "timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP, " + \
                        "Battery_SoC REAL, Consumed_Energy REAL, Generated_Energy REAL, " + \
                        "Charged_Energy REAL, System_Load REAL"
            for d in self.dev_list:
                df_string += ", " + d + " REAL"
            df_string += " )"
            self.db.execute(df_string)

            self.latest = "Initialised"

    def stop(self):
        self.db.dispose()

    def getLatest(self):
        return "Aggregator: "+self.latest

    def do_step(self):
        self.latest=str(datetime.datetime.now()) + ":    Starting Routine"
        db_string = """SELECT bar.IntervDate FROM (SELECT DISTINCT(foo.date + interval '1' HOUR*foo.hour + interval '15' MINUTE * foo.minute) AS IntervDate FROM 
                    (SELECT DATE(timestamp) as date, 
                    extract(hour from timestamp) AS hour,
                    CASE WHEN extract(minutes from timestamp) BETWEEN 0 AND 14 THEN 0
                    WHEN extract(minutes from timestamp) BETWEEN 15 AND 29 THEN 1
                    WHEN extract(minutes from timestamp) BETWEEN 30 AND 44 THEN 2
                    ELSE 3 END AS minute
                    FROM """+self.sql_table_raw+""") AS foo) as bar
                     WHERE bar.IntervDate NOT IN (select timestamp from """+self.sql_table+""") 
                     ORDER BY bar.IntervDate ASC;"""

        #              WHERE IntervDate not in (select timestamp from aggregated_energy_data)"""

        # db_string = """select timestamp from aggregated_energy_data"""
        ret_outer = self.db.execute(db_string).fetchall()
        i = 0
        for row in ret_outer:
            try:
                if i + 1 != len(ret_outer):
                    i += 1
                    self.latest += "\n------------For Time "+str(row[0])+" \n"
                    # Get all data for row
                    db_string = "select * from raw_energy_data WHERE timestamp BETWEEN '%s' AND '%s' """ % (
                        row[0], row[0] + datetime.timedelta(minutes=14) + datetime.timedelta(seconds=59))
                    ret = self.db.execute(db_string)
                    df = pd.DataFrame(ret.fetchall())
                    df.columns = ret.keys()
                    df.index = df['timestamp']
                    df = df.drop("id", axis=1)

                    # # Check if all Available, if not add mean values
                    db_string = "SELECT foo.dev_group,foo.device,foo.parameter,AVG(foo.value) FROM (SELECT extract(hour from timestamp) as hour,dev_group,device,parameter,value FROM raw_energy_data) AS foo WHERE foo.hour = '%s' GROUP BY dev_group,device,parameter" % \
                                row[0].hour
                    ret2 = self.db.execute(db_string)
                    df_old_data = pd.DataFrame(ret2.fetchall())
                    self.latest += "Missing Value found for Row ["
                    for inner_key, row_inner in df_old_data.iterrows():
                        if len(df[(df['dev_group'] == row_inner[0]) & (df['device'] == row_inner[1]) & (
                                df['parameter'] == row_inner[2])]) == 0:
                            self.latest+=str(row_inner[0])+"-"+str(row_inner[1])+"-"+str(row_inner[2])+"; "
                            df_to_app = pd.DataFrame(
                                data={'timestamp': [df.sample(1)['timestamp'][0]], 'dev_group': [row_inner[0]],
                                      'device': [row_inner[1]], 'parameter': [row_inner[2]],
                                      'value': row_inner[3]})
                            df_to_app.index = df_to_app['timestamp']
                            df = df.append(df_to_app)
                    self.latest+="] "
                    df = df.groupby([
                        pd.Grouper(freq='15Min'),
                        pd.Grouper('dev_group'),
                        pd.Grouper('device'),
                        pd.Grouper('parameter')
                    ]).mean()
                    # df = pd.pivot_table(df, values='value', index=['timestamp'],columns=['dev_group','device','parameter'], aggfunc='first')
                    df.reset_index(inplace=True)
                    #print(df)
                    df_victron = df[df["dev_group"] == "System_Data"][['parameter', "value"]]
                    df_victron = df_victron.rename(columns={"parameter": "key"})
                    #print(df_victron)
                    df_victron.loc[df_victron['key'] == "VenusGX/Dc/Pv/Power", 'key'] = "generated_energy"
                    df_victron.loc[
                        df_victron['key'] == "VenusGX/Ac/Consumption/L1/Power", 'key'] = "consumed_energy"
                    df_victron.loc[df_victron['key'] == "VenusGX/Dc/Battery/Power", 'key'] = "charged_energy"
                    df_victron.loc[df_victron['key'] == "VenusGX/Dc/Battery/Soc", 'key'] = "battery_soc"

                    df_devs = df[df["dev_group"] != "System_Data"].groupby('device').mean()
                    df_devs.reset_index(inplace=True)
                    df_devs = df_devs.rename(columns={"device": "key"})

                    # print(df_devs)

                    col_lst = list(df_devs["key"].values)
                    for c in col_lst:
                        if "ac" not in c.lower():
                            df_devs.loc[df_devs['key'] == c, 'value'] = df_devs.loc[
                                                                            df_devs['key'] == c, 'value'] / 1000
                    df = df_victron.append(df_devs, ignore_index=True)

                    df = df.append({'key': 'system_load', 'value':
                        df_victron.loc[df_victron['key'] == "consumed_energy", 'value'].values[0] - df_devs[
                            'value'].sum(skipna=True)}, ignore_index=True)


                    col_list = "("
                    val_list = "("
                    for p in df['key'].values:
                        col_list += p + ", "
                        val_list += "%5.3f," % (df.loc[df['key'] == p, 'value'])
                    col_list += "timestamp)"
                    val_list += "'%s')" % (row[0])

                    db_string = """INSERT INTO  aggregated_energy_data """ + col_list + """ VALUES """ + val_list
                    self.db.execute(db_string)
                    self.latest += "\nDatabase updated for Entry"
            except IndexError as ex:
                #Usually IndexError: index 0 is out of bounds for axis 0 with size 0
                self.latest += "Usually IndexError: index 0 is out of bounds for axis 0 with size 0"
                pass