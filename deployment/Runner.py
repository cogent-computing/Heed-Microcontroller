import threading
import time
import sys
import json
# Import own Classes
from Controller import Controller
from Control_Enactor import Enactor
from Data_Retreiver import Data_Retreiver

from Data_Aggregator import Aggregator

from Forecaster import Forecaster
#from Forecaster_v2 import Forecaster

from Battery import Battery

from Local_Logger import LocalLogger
from WebsiteSpoof import MicrogridWebRetreiver

from Remote_Logger import RemoteLogger


# Define Thread that reads data from telnet and pushes it to PostgreSQL
class LoggerThread(threading.Thread):
    ##Misc
    error = None
    state = "Uninitialised"
    # Token to synchronize threads
    run_thread = True
    name = None

    def __init__(self, name, th_type, sampling, allocation, devices, group, device, sql_aggregate, sql_decision,
                 sql_forecast, sql_preference, sql_raw_energy, sql_raw_state, sql_addr, sql_port, sql_user, sql_pw,
                 sql_db, telnet_addr, telnet_port, sftp_location, sftp_port, sftp_username, sftp_password,
                 sftp_key_location, sftp_directory, mesh_user, mesh_pw, mqtt_address, mqtt_port, mqtt_username,
                 mqtt_password):

        super(LoggerThread, self).__init__()
        # Misc Thread elements
        self.name = name
        self.th_type = th_type
        self.state = "uninitialised"
        self.error = None

        # Devs and Alloc
        self.allocation = allocation
        self.devices = devices
        self.group = group
        self.device = device
        # Sampling
        self.sampling = sampling

        # SFTP
        self.sftp_location = sftp_location
        self.sftp_port = sftp_port
        self.sftp_username = sftp_username
        self.sftp_password = sftp_password
        self.sftp_key_location = sftp_key_location
        self.sftp_directory = sftp_directory

        # SQL
        self.sql_aggregate = sql_aggregate
        self.sql_decision = sql_decision
        self.sql_forecast = sql_forecast
        self.sql_preference = sql_preference
        self.sql_raw_energy = sql_raw_energy
        self.sql_raw_state = sql_raw_state

        # Settign Up SQL Credentials and details
        self.sql_addr = sql_addr
        self.sql_port = sql_port
        self.sql_user = sql_user
        self.sql_pw = sql_pw
        self.sql_db = sql_db

        # Telnet
        self.telnet_addr = telnet_addr
        self.telnet_port = telnet_port

        # Webs Spoof
        self.mesh_user = mesh_user
        self.mesh_pw = mesh_pw

        # MQTT
        self.mqtt_address = mqtt_address
        self.mqtt_port = mqtt_port
        self.mqtt_username = mqtt_username
        self.mqtt_password = mqtt_password

        # Initialise
        self.init_components()

    def init_components(self):
        self.state = "uninitialised"
        self.error = None
        try:
            devices_excl_sys = {x: self.devices[x] for x in self.devices if x != "Victron_VenusGX"}
            allocation_excl_sys = {x: self.allocation[x] for x in self.allocation if x != "System_Data"}
            if self.th_type == "Controller":
                enact = Enactor(devices_excl_sys, self.sftp_location, self.sftp_port, self.sftp_username,
                                self.sftp_password, self.sftp_key_location,
                                self.sftp_directory)
                data = Data_Retreiver(devices_excl_sys, self.sql_user, self.sql_pw, self.sql_addr, self.sql_port,
                                      self.sql_db)

                self.service = Controller(data, enact, allocation_excl_sys)
            elif self.th_type == "Aggregator":
                self.service = Aggregator(list(devices_excl_sys.keys()), self.sql_aggregate, self.sql_raw_energy,
                                          self.sql_addr, self.sql_port,
                                          self.sql_user, self.sql_pw, self.sql_db)
            elif self.th_type == "Forecaster":
                data = Data_Retreiver(devices_excl_sys, self.sql_user, self.sql_pw, self.sql_addr, self.sql_port,
                                      self.sql_db)
                self.service = Forecaster(Battery, data, self.devices)
            elif self.th_type == "LocalLogger":
                self.service = LocalLogger(self.group, self.device, self.devices[self.device], self.telnet_addr,
                                           self.telnet_port, self.sql_raw_energy, self.sql_raw_state,
                                           self.sql_addr, self.sql_port, self.sql_user, self.sql_pw, self.sql_db)
            elif self.th_type == "WebLogger":
                self.service = MicrogridWebRetreiver(self.group, self.device, self.devices[self.device],
                                                     self.sql_raw_energy, self.sql_raw_state, self.sql_addr,
                                                     self.sql_port, self.sql_user, self.sql_pw, self.sql_db,
                                                     self.mesh_user, self.mesh_pw)
            elif self.th_type == "RemoteLogger":
                data = Data_Retreiver(devices_excl_sys, self.sql_user, self.sql_pw, self.sql_addr, self.sql_port,
                                      self.sql_db)
                self.service = RemoteLogger(data, self.mqtt_address, self.mqtt_port, self.mqtt_username,
                                            self.mqtt_password)
        except Exception as ex:
            print("FAULT: Thread " + self.getName() + " Internal Error : "+ str(sys.exc_info()[0]))
            self.error = str(sys.exc_info()[0])
            self.state = "Error"

    def stop(self):
        try:
            print("Thread " + self.getName() + " Stopped by External")
            self.run_thread = False
            self.service.stop()
            self.state = "Stopped"
        except Exception as ex:
            print("FAULT: Thread " + self.getName() + " Internal Error : "+ str(sys.exc_info()[0]))
            self.error = str(sys.exc_info()[0])
            self.state = "Error"

    def getState(self):
        return self.state

    def getLatest(self):
        return self.service.getLatest()

    def getError(self):
        return self.error

    def run(self):
        if self.state != "Error":
            print("Thread " + self.getName() + " Started")
            self.state = "Running"
            try:
                while True:
                    self.service.do_step()
                    time.sleep(self.sampling)
            except Exception as ex:
                print("Thread " + self.getName() + " Internal Error")
                self.error = str(ex)
                self.state = "Error"


if __name__ == "__main__":
    # Init Thread
    threads = []
    with open('runner_config.json') as json_file:
        json_data = json.load(json_file)

    if json_data["run_type"] == "WebLogger":
        sampling_dev = json_data["sampling_dev_v1"]  # Every 10 mins
    else:
        sampling_dev = json_data["sampling_dev_v2"]  # every 15 seconds
# Create Thread for Aggregator
threads.append(
    LoggerThread("Data Aggregator", "Aggregator", json_data["sampling_major"], json_data["allocation"],
                 json_data["devices"], None, None, json_data["sql_aggregate"],
                 json_data["sql_decision"], json_data["sql_forecast"], json_data["sql_preference"],
                 json_data["sql_raw_energy"], json_data["sql_raw_state"], json_data["sql_addr"], json_data["sql_port"],
                 json_data["sql_user"], json_data["sql_pw"],
                 json_data["sql_db"], json_data["telnet_addr"], json_data["telnet_port"], json_data["sftp_location"],
                 json_data["sftp_port"], json_data["sftp_username"], json_data["sftp_password"],
                 json_data["sftp_key_location"], json_data["sftp_directory"], json_data["mesh_user"],
                 json_data["mesh_pw"], json_data["mesh_files"], json_data["mesh_addr"],json_data["mqtt_address"], json_data["mqtt_port"], json_data["mqtt_username"],
                 json_data["mqtt_password"]))

# Create Thread for Forecaster
threads.append(
    LoggerThread("Data Forecaster", "Forecaster", json_data["sampling_major"], json_data["allocation"],
                 json_data["devices"], None, None, json_data["sql_aggregate"],
                 json_data["sql_decision"], json_data["sql_forecast"], json_data["sql_preference"],
                 json_data["sql_raw_energy"], json_data["sql_raw_state"], json_data["sql_addr"], json_data["sql_port"],
                 json_data["sql_user"], json_data["sql_pw"],
                 json_data["sql_db"], json_data["telnet_addr"], json_data["telnet_port"], json_data["sftp_location"],
                 json_data["sftp_port"], json_data["sftp_username"], json_data["sftp_password"],
                 json_data["sftp_key_location"], json_data["sftp_directory"], json_data["mesh_user"],
                 json_data["mesh_pw"],json_data["mqtt_address"], json_data["mqtt_port"], json_data["mqtt_username"],
                 json_data["mqtt_password"]))

# Create Thread for Controller
threads.append(
    LoggerThread("Microgrid Controller", "Controller", json_data["sampling_major"], json_data["allocation"],
                 json_data["devices"], None, None, json_data["sql_aggregate"],
                 json_data["sql_decision"], json_data["sql_forecast"], json_data["sql_preference"],
                 json_data["sql_raw_energy"], json_data["sql_raw_state"], json_data["sql_addr"], json_data["sql_port"],
                 json_data["sql_user"], json_data["sql_pw"],
                 json_data["sql_db"], json_data["telnet_addr"], json_data["telnet_port"], json_data["sftp_location"],
                 json_data["sftp_port"], json_data["sftp_username"], json_data["sftp_password"],
                 json_data["sftp_key_location"], json_data["sftp_directory"], json_data["mesh_user"],
                 json_data["mesh_pw"],json_data["mqtt_address"], json_data["mqtt_port"], json_data["mqtt_username"],
                 json_data["mqtt_password"]))

# Create Threads for Logger - Web or Local
for group in json_data["allocation"]:
    for dev in json_data["allocation"][group]:
        time.sleep(1)  # Gives a delay between local querries
        threads.append(
            LoggerThread("Raw Data Logger - " + group + " - " + dev, json_data["run_type"], sampling_dev, json_data["allocation"],
                 json_data["devices"], group, dev, json_data["sql_aggregate"],
                 json_data["sql_decision"], json_data["sql_forecast"], json_data["sql_preference"],
                 json_data["sql_raw_energy"], json_data["sql_raw_state"], json_data["sql_addr"], json_data["sql_port"],
                 json_data["sql_user"], json_data["sql_pw"],
                 json_data["sql_db"], json_data["telnet_addr"], json_data["telnet_port"], json_data["sftp_location"],
                 json_data["sftp_port"], json_data["sftp_username"], json_data["sftp_password"],
                 json_data["sftp_key_location"], json_data["sftp_directory"], json_data["mesh_user"],
                 json_data["mesh_pw"],json_data["mqtt_address"], json_data["mqtt_port"], json_data["mqtt_username"],
                 json_data["mqtt_password"]))

# Create Thread for Controller
threads.append(
    LoggerThread("Coventry Remote Logger", "RemoteLogger", json_data["sampling_logger"], json_data["allocation"],
                 json_data["devices"], None, None, json_data["sql_aggregate"],
                 json_data["sql_decision"], json_data["sql_forecast"], json_data["sql_preference"],
                 json_data["sql_raw_energy"], json_data["sql_raw_state"], json_data["sql_addr"], json_data["sql_port"],
                 json_data["sql_user"], json_data["sql_pw"],
                 json_data["sql_db"], json_data["telnet_addr"], json_data["telnet_port"], json_data["sftp_location"],
                 json_data["sftp_port"], json_data["sftp_username"], json_data["sftp_password"],
                 json_data["sftp_key_location"], json_data["sftp_directory"], json_data["mesh_user"],
                 json_data["mesh_pw"],json_data["mqtt_address"], json_data["mqtt_port"], json_data["mqtt_username"],
                 json_data["mqtt_password"]))

# Start Threads
for th in threads:
    th.start()

# Initialis Sleep
time.sleep(60)

try:
    # Idle
    while True:
        # Check Threads
        print("------------------- Checking Thread Health -----------------")
        for id_th, th in enumerate(threads):
            if th.getState() != "Running":
                print(
                    "------  For Broken Thread " + th.getName() + " not Running with State: " + th.getState())
                print("Error:")
                print(th.getError())
                th.stop()
                # ReInitialise
                threads[id_th].init_components()
            else:
                print("------ For Running Thread: ", th.getName(), "\n", th.getLatest())
        time.sleep(60*5)  # Hourly is fine

except Exception as ex:
    print("Unexpected error:", sys.exc_info()[0])
    # Close Thread
    for th in threads:
        th.stop()

    # Join Threads
    for th in threads:
        th.join()

print("Finished all and Connection Closed")
