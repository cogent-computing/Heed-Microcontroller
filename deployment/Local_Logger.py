import asyncio, telnetlib3
import re
import sys
import traceback

import datetime
import time
import json
from sqlalchemy import create_engine
import os
import threading


class CustomRoutine:
    device = None
    db = None
    table = None

    # Load Config Elements
    param_interest_power = ["LED[0-99]_P", "vRELAY[0-99]_LVL",
                            'VenusGX/Dc/Pv/Power',
                            'VenusGX/Ac/Consumption/L1/Power',
                            'VenusGX/Dc/Battery/Power',
                            'VenusGX/Dc/Battery/Soc'
                            ]

    param_interest_state = ["AC_Day_Energy_session", "AC_Day_Energy_remain",  # Socket Quota and state information
                            "LED_NL_session", "LED_NL_remain",
                            "LED_BL_session", "LED_BL_remain"]

    def __init__(self, group, dev_name, device, db, table, table2):
        self.device = device
        self.db = db
        self.table = table
        self.table2 = table2
        self.dev_name = dev_name
        self.group = group

    @asyncio.coroutine
    def mesh_reader(self, reader, writer):
        # print("Initilaising for Device:"+ str(self.device))
        while True:
            # read stream until '?' mark is found
            try:
                to_save = {}
                to_save2 = {}
                outp = yield from reader.read(1024)
                for row in outp.split("\n"):
                    for param in self.param_interest_power:
                        try:
                            x = re.search(param, row)
                            if x:
                                to_save[x.group()] = float(re.split(param, row)[1])
                        except ValueError as ex:
                            #print("Value error on Conversions: " + str(ex))
                            exc_type, exc_value, exc_tb = sys.exc_info()
                    for param in self.param_interest_state:
                        try:
                            x = re.search(param, row)
                            if x:
                                to_save2[x.group()] = float(re.split(param, row)[1])
                        except ValueError as ex:
                            #print("Value error on Conversions: " + str(ex))
                            exc_type, exc_value, exc_tb = sys.exc_info()
                            #pprint(traceback.format_exception(exc_type, exc_value, exc_tb))
                self.save_values(to_save, to_save2)
                # Check if Output is Right
                if not outp:
                    # End of File
                    return "A Okay"
                else:
                    # reply all questions with 'y'.
                    # writer.write('s get_vars C1:00:11:22:33:44:55\r\n')
                    writer.write('s get_vars ' + self.device + '\r\n')

                # display all server output
            except ConnectionAbortedError:
                # print("str(datetime.datetime.now())"+"Known - Normal ConnectionAbortedError on:"+str(self.group)+" Dev Name:"+str(self.dev_name))
                # "Happens at every instance so nothing here "
                return "ConnectionAbortedError - Normal"
            except ConnectionResetError:
                #print(str(datetime.datetime.now()) + "Known - Normal ConnectionResetError on: " + str(
                #    self.group) + " Dev Name:" + str(self.dev_name))
                return "ConnectionResetError - Normal"

    def save_values(self, vals, vals2):
        if len(vals) > 0:
            for val in vals:
                db_string = """INSERT INTO  """ + self.table + """(dev_group, device, parameter, value) 
                                    VALUES('""" + self.group + """', 
                                           '""" + self.dev_name + """', 
                                         '""" + val + """', 
                                         '""" + str(vals[val]) + """')"""
                self.db.execute(db_string)
            for val2 in vals2:
                db_string = """INSERT INTO  """ + self.table2 + """(dev_group, device, parameter, value) 
                                    VALUES('""" + self.group + """', 
                                           '""" + self.dev_name + """', 
                                         '""" + val2 + """', 
                                         '""" + str(vals2[val2]) + """')"""
                self.db.execute(db_string)


# Define Thread that reads data from telnet and pushes it to PostgreSQL
class LocalLogger:

    def __init__(self, group, dev_name, device, telnet_addr, telnet_port, sql_table_raw, sql_table_state,
                 sql_addr, sql_port, sql_user, sql_pw, sql_db):
        self.device = device
        self.dev_name = dev_name
        self.group = group

        # Set up Telnet Parameters
        self.telnet_addr = telnet_addr
        self.telnet_port = telnet_port

        self.sql_table = sql_table_raw
        self.sql_table2 = sql_table_state
        # Settign Up SQL Credentials and details
        sql_addr = sql_addr
        sql_port = sql_port
        sql_user = sql_user
        sql_pw = sql_pw
        sql_db = sql_db

        # Making intiial connection object with Database
        db_string = "postgres://" + sql_user + ":" + sql_pw + "@" + sql_addr + ":" + sql_port + "/" + sql_db
        self.db = create_engine(db_string)

        # Make sure table exists and if not create it
        self.db.execute(
            "CREATE TABLE IF NOT EXISTS " + self.sql_table + " (id SERIAL PRIMARY KEY, timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP, dev_group TEXT, device TEXT, parameter TEXT, value REAL)")

        self.db.execute(
            "CREATE TABLE IF NOT EXISTS " + self.sql_table2 + " (id SERIAL PRIMARY KEY, timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP, dev_group TEXT, device TEXT, parameter TEXT, value REAL)")

        self.state = "Initialised"

    def stop(self):
        self.db.dispose()

    def getLatest(self):
        return  "LocalLogger : "+self.group + " : " + self.dev_name + " : "+self.latest

    def getGroupName(self):
        return self.group

    def getDevice(self):
        return self.device

    def getDevName(self):
        return self.dev_name

    def do_step(self):
        # device, db, table):
        routine = CustomRoutine(self.group, self.dev_name, self.device, self.db, self.sql_table,
                                self.sql_table2)
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        coro = telnetlib3.open_connection(self.telnet_addr, self.telnet_port, shell=routine.mesh_reader)
        reader, writer = loop.run_until_complete(coro)
        loop.run_until_complete(writer.protocol.waiter_closed)
        self.latest  = str(datetime.datetime.now())+" Async Routine Complete. "
