from http import cookiejar
from urllib import request, parse, error as urlError
import base64
from urllib.error import URLError

import pandas as pd
import io
import re
import datetime
from sqlalchemy import create_engine
import time

class MeshDataSpoofer(object):

    def __init__(self, login, password):
        """ Start up... """
        self.login = login
        self.password = password

        self.cj = cookiejar.CookieJar()
        self.opener = request.build_opener(
            request.HTTPRedirectHandler(),
            request.HTTPHandler(debuglevel=0),
            request.HTTPSHandler(debuglevel=0),
            request.HTTPCookieProcessor(self.cj)
        )

        # Auth
        # print(('%s:%s' % (login, password)).encode("utf-8"))
        base64string = base64.b64encode(('%s:%s' % (login, password)).encode("utf-8"))
        auth_str = str(base64string)[2:-1]
        # print(auth_str)

        self.opener.addheaders = [
            ('User-agent', ('Mozilla/4.0 (compatible; MSIE 6.0; '
                            'Windows NT 5.2; .NET CLR 1.1.4322)')),
            ("Authorization", "Basic %s" % auth_str)
        ]
        # print([
        #     ('User-agent', ('Mozilla/4.0 (compatible; MSIE 6.0; '
        #                     'Windows NT 5.2; .NET CLR 1.1.4322)')),
        #     ("Authorization","Basic %s" % auth_str)
        # ])

    def retreiveFiles(self, location, device, file):
        loc_text = location + device + "/" + file
        response = self.opener.open(loc_text)
        df = pd.read_csv(io.StringIO(response.read().decode('utf-8')), error_bad_lines=True, header=0,
                         names=['Timestamp', 'Key', 'Value'], index_col=None)
        df['Timestamp'] = pd.to_numeric(df['Timestamp'], downcast='float')
        df.index = pd.to_datetime(df['Timestamp'], unit='s', errors='raise')
        df = df.drop(columns=['Timestamp'], axis=1)
        return df


class MicrogridWebRetreiver:


    param_interest_power = ["LED[0-99]_P", "vRELAY[0-99]_LVL",
                            'VenusGX/Dc/Pv/Power',
                            'VenusGX/Ac/Consumption/L1/Power',
                            'VenusGX/Dc/Battery/Power',
                            'VenusGX/Dc/Battery/Soc'
                            ]

    param_interest_state = ["AC_Day_Energy_session", "AC_Day_Energy_remain",  # Socket Quota and state information
                            "LED_NL_session", "LED_NL_remain",
                            "LED_BL_session", "LED_BL_remain"]

    def __init__(self, group, dev, mac,sql_raw_energy, sql_raw_state, sql_addr, sql_port, sql_user, sql_pw, sql_db, mesh_user, mesh_pw,mesh_addr):

        self.group = group
        self.dev = dev
        self.mac = mac

        self.sql_addr = sql_addr
        self.sql_port = sql_port
        self.sql_user = sql_user
        self.sql_pw = sql_pw
        self.sql_db = sql_db

        self.sql_raw_energy = sql_raw_energy
        self.sql_raw_state = sql_raw_state

        self.wb = MeshDataSpoofer(mesh_user, mesh_pw)
        # Making intiial connection object with Database
        db_string = "postgres://" + sql_user + ":" + sql_pw + "@" + sql_addr + ":" + sql_port + "/" + sql_db
        self.db = create_engine(db_string)
        self.latest = str(datetime.datetime.now())+ "Init Done"
        self.mesh_addr = mesh_addr
    def save_values(self, vals, vals2):
        if len(vals) > 0:
            for val in vals:
                db_string = """ insert into """ + self.sql_raw_energy + """ (timestamp, dev_group, device, parameter, value)
                                select '""" + str(vals[val][1]) + """',
                                            '""" + self.group + """', 
                                           '""" + self.dev + """', 
                                         '""" + val + """', 
                                         '""" + str(vals[val][0]) + """'
                                where not exists (
                                    SELECT timestamp, dev_group, device, parameter, value FROM raw_energy_data
                                     WHERE timestamp='""" + str(vals[val][1]) + """' AND 
                                     dev_group = '""" + self.group + """' AND  device =  '""" + self.dev + """' AND 
                                     parameter = '""" + val + """'
                                );
                                """
                self.db.execute(db_string)
            for val2 in vals2:
                db_string = """ insert into """ + self.sql_raw_state + """ (timestamp, dev_group, device, parameter, value)
                                select '""" + str(vals2[val2][1]) + """',
                                            '""" + self.group + """', 
                                           '""" + self.dev + """', 
                                         '""" + val2 + """', 
                                         '""" + str(vals2[val2][0]) + """'
                                where not exists (
                                    SELECT timestamp, dev_group, device, parameter, value FROM raw_energy_data
                                     WHERE timestamp='""" + str(vals2[val2][1]) + """' AND 
                                     dev_group = '""" + self.group + """' AND  device =  '""" + self.dev + """' AND 
                                     parameter = '""" + val2 + """'
                                );
                                """
                self.db.execute(db_string)

    def querry_device(self):
        mac = self.mac.replace(":", "")
        file = datetime.datetime.now().strftime("%d-%m-%Y.csv")
        # print("Querrying for: ", group, " ", device, " ", mac, " ",file)
        df = self.wb.retreiveFiles(self.mesh_addr, mac, file)
        to_save = {}
        to_save2 = {}
        mock_ts = None
        for k in df['Key'].unique():
            for param in self.param_interest_power:
                x = re.search(param, k)
                if x:
                    to_save[x.group()] = [float(df[df['Key'] == k]['Value'].iat[-1]), df[df['Key'] == k].index[-1]]
                    mock_ts =  df[df['Key'] == k].index[-1]
            for param in self.param_interest_state:
                x = re.search(param, k)
                if x:
                    to_save2[x.group()] = [float(df[df['Key'] == k]['Value'].iat[-1]), df[df['Key'] == k].index[-1]]
                    mock_ts = df[df['Key'] == k].index[-1]
        self.save_values(to_save, to_save2)

        self.latest = str(datetime.datetime.now())+" Values read and saved with mock-ts: "+str(mock_ts)

    def stop(self):
        self.db.dispose()

    def getLatest(self):
        return  "WebSpoof : "+self.group + " : " + self.dev + " : "+self.latest

    def do_step(self):
        try:
            self.querry_device()
        except urlError.HTTPError as ex:
            self.latest = " ERROR: "+str(datetime.datetime.now())+" Unexpected exception for "+str(self.group)+ " "+str(self.dev)+" : "
            self.latest +="Exception: " + str(ex)
        except URLError as ex:
            self.latest = " ERROR: "+str(datetime.datetime.now())+" Unexpected exception for "+str(self.group)+ " "+str(self.dev)+" : "
            self.latest +="Exception: " + str(ex)