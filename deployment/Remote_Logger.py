import paho.mqtt.client as mqtt
import time
import datetime
import numpy as np
import sys
import os
# Own Imports
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from deployment.Data_Retreiver import Data_Retreiver


class RemoteLogger:

    def __init__(self, data, mqtt_address, mqtt_port, mqtt_username, mqtt_password):
        self.latest = "Created"
        self.data = data
        self.mqtt_address = mqtt_address
        self.mqtt_port = mqtt_port
        self.mqtt_username = mqtt_username
        self.mqtt_password = mqtt_password
        self.timeout_loop = 60
        self.initialise()
        self.latest = "Initialised"

    def initialise(self):
        self.device_name = self.get_dev_name()
        self.client = mqtt.Client(self.device_name)
        self.client.username_pw_set(self.mqtt_username, self.mqtt_password)
        self.client.on_publish = self.on_publish
        self.client.connect(self.mqtt_address, self.mqtt_port, self.timeout_loop)
        self.client.loop_start()

    def on_publish(self, client, userdata, mid):
        self.latest += " - Success with Mid: " + str(mid) + " at " + str(datetime.datetime.now()) + "\n"
        tries = 0
        while self.data.update_mid(mid) is None and tries<10:
            time.sleep(0.1)
            tries+=1


    def get_dev_name(self):
        return "Microgrid_Controller_1"

    def stop(self):
        self.client.disconnect()
        self.data.stop()

    def getLatest(self):
        return "Remote Logger: "+self.latest

    def do_step(self):
        df = self.get_messages()
        self.latest = "Empty Dataframe. Nothing to do."
        if df is not None:
            if len(df) > 0:
                for index, row in df.iterrows():
                    if row['message_id'] is None or row['timestamp'] < datetime.datetime.now(row['timestamp'].tzinfo) - datetime.timedelta(minutes=1) or \
                            np.isnan(row['message_id']):
                        log_id = row['id']
                        del row['id']
                        del row['transmitted']
                        del row['message_id']
                        row['timestamp'] = str(row['timestamp'])
                        msg = row.to_json()
                        ret = self.client.publish("microgrid/" + self.device_name, msg, qos=1)
                        self.latest = str(datetime.datetime.now())+" : Publishing message with Nulls:"+ str(list(row[row.isna()].index)) +"  with return:" + str(ret)
                        self.data.update_log(log_id, ret[1], False)
                        if ret[0] != 0:
                            self.latest =str(datetime.datetime.now()) + "Reinitialising - Conn Failed"
                            self.client.reinitialise()

    def get_messages(self):
        self.data.create_log(datetime.datetime.now())
        df = self.data.get_unsent_logs(datetime.datetime.now())
        return df
