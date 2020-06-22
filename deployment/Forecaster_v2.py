import sys
import pandas as pd
import datetime
import time
import json
from sqlalchemy import create_engine
import os
import threading
import statsmodels.api as sm
import pvlib
from pvlib import clearsky, atmosphere, solarposition
from pvlib.location import Location
from pvlib.iotools import read_tmy3
from pvlib.solarposition import get_solarposition

from deployment.Data_Retreiver import Data_Retreiver
from deployment.Battery import Battery

import warnings
warnings.filterwarnings('ignore')

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

        self.full_df = None

    def stop(self):
        self.data.stop()

    def getLatest(self):
        return "Forecaster : " + self.latest

    def get_forecast_dev(self,dev_df,forecast_period=48):

        dev = list(dev_df.columns)[0]
        print("Doing forecast for Dev :",dev)
        req_ts = max(dev_df.index)

        #Mock Resultdev = "system_load"
        # Best - 5824 - 107 secs SARIMA(1, 0, 2)       x(0, 2, 2, 24)     24
        # Best - 6074 - 5.7 secs SARIMA(1, 0, 0)       x(2, 1, 0, 24)     24

        df_hist = dev_df[dev].resample('1H').mean().to_frame()
        if dev == "consumed_energy":
            mod = sm.tsa.statespace.SARIMAX(df_hist[dev],
                                            order=(1, 0, 2),
                                            seasonal_order=(0, 2, 2, 24),
                                            enforce_stationarity=False,
                                            enforce_invertibility=False)
        else:
            mod = sm.tsa.statespace.SARIMAX(df_hist[dev],
                                            order=(1,0,0),
                                            seasonal_order=(2,1,0,24),
                                            enforce_stationarity=False,
                                            enforce_invertibility=False)
        results = mod.fit(disp=False,full_output=False)
        pred_uc = results.get_forecast(steps=forecast_period)
        df_ret = pd.DataFrame(pred_uc.predicted_mean)
        df_ret['timestamp'] = df_ret.index
        df_ret = df_ret.rename(columns={0: dev})
        return df_ret

    def get_forecast_generation(self,dev_df,forecast_period=48):
        req_ts = max(dev_df.index).replace( microsecond=0, second=0,minute=0)+datetime.timedelta(hours=1)
        dev = list(dev_df.columns)[0]
        days = pd.date_range(start=req_ts,end=req_ts + datetime.timedelta(hours=forecast_period-1),freq='1H')
        print("Doing forecast for Generation :", dev)

        # Pv Info
        lat = -2.483535
        long = 29.523457
        # https://www.daftlogic.com/sandbox-google-maps-find-altitude.htm
        height = 2139
        # typical temperature between 15 and 28 yearly, taking 22 as average
        typ_temp = 22
        # Efficienct
        effic = 0.155
        # Area m2
        area = 16.37
        # Surface
        surf_tilt = 15
        surf_az = 128  # It might be more like 119.5
        # effic-scalar
        scalar = 0.6

        tus = Location(lat, long, "Africa/Kigali", height, 'Kigeme')

        cs = tus.get_clearsky(days, model='ineichen')  # ineichen with climatology table by default
        sun_pos = get_solarposition(cs.index, lat, long, altitude=height, pressure=None, method='nrel_numpy', temperature=typ_temp)


        # \[I_{tot} = I_{beam} + I_{sky} + I_{ground}\]
        total_irrad = pvlib.irradiance.get_total_irradiance(surf_tilt, surf_az, sun_pos['zenith'], sun_pos['azimuth'],
                                                            cs['dni'], cs['ghi'], cs['dhi'], DNI_ET=None, AM=None,
                                                            albedo=0.13, surface_type="grass", model='isotropic',
                                                            model_perez='allsitescomposite1990')
        poa = total_irrad['poa_global'].to_frame()

        poa['timestamp'] = poa.index
        poa = poa.rename(columns={'poa_global': dev})
        return poa

    def do_step(self, forecast_period=48, curr_ts=datetime.datetime.now()):

        df = None
        offset = 0
        while df is None:
            #print("Retreiving Data with offeset: ",offset," days")
            df = self.data.retreive_filled_aggre(curr_ts-datetime.timedelta(days=offset),8)
            offset+=1
        if df is None:
            print("No values available:")
            return None
        #df.to_csv("in.csv")
        bat = Battery(state_of_charge=df['battery_soc'].values[0])
        devices = [ x for x in df.columns if x not in ['timestamp','battery_soc','generated_energy',
                                                        'charged_energy']] #COnsumed Energy and System load are treated as devices for the purpose of forecasting
        full_df = None
        for dev in devices:
            int_df = self.get_forecast_dev(df[dev].to_frame(),forecast_period=forecast_period)
            #print(int_df.size)
            #print(int_df.head(2))
            #print(int_df.tail(2))
            if full_df is None:
                full_df = int_df
            else:
                full_df = full_df.merge(int_df, on="timestamp", suffixes=(False, False))

        df_pv = self.get_forecast_generation(df['generated_energy'].to_frame(),forecast_period=forecast_period)
        #print(df_pv.size)
        #print(df_pv.head(2))
        #print(df_pv.tail(2))
        full_df = full_df.merge(df_pv, on="timestamp", suffixes=(False, False))

        full_df['charged_energy'] = full_df['generated_energy'] - full_df['consumed_energy']

        full_df['battery_soc'] = None
        for index,row in full_df.iterrows():
            if row['charged_energy'] > 0.0:
                bat.charge_battery(row['charged_energy'] / 1000.0)
            else:
                bat.discharge_battery(-row['charged_energy'] / 1000.0)
            full_df.loc[index,'battery_soc'] = bat.state_of_charge

        full_df.index = full_df['timestamp']

        with pd.option_context('display.max_rows', 5, 'display.max_columns', 5):
            self.latest = str(datetime.datetime.now()) +" : "+str(
                full_df[["system_load", "generated_energy", "consumed_energy"]].tail(1).to_json(orient='records'))
        self.full_df = full_df
        self.data.update_forecast(full_df)