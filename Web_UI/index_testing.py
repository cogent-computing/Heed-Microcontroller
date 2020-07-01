#!flask/bin/python
from flask import Flask, Response, request, render_template
import json
from sqlalchemy import create_engine
from flask_cors import CORS;
import pandas as pd
from deployment.Battery import Battery
from simulation_evaluation.microgrid_simulator import ControllEnvironment
import datetime
import random

app = Flask(__name__);
CORS(app);

#Test

priorities = None

class DataFaker:
    def __init__(self,day=None,hour=None,battery_power=21.1,
                                            battery_max_discharge=40.0, pv_scale=1.0):
        self.day = day
        self.hour = hour
        #Sort Day
        if day is None:
            self.day = 1
        self.hour = hour
        if self.hour is None:
            self.test_hour = datetime.datetime.now().hour
        else:
            self.test_hour = self.hour
        self.battery_power = battery_power
        self.battery_max_discharge =  battery_max_discharge
        self.pv_scale = pv_scale

        self.test_env = ControllEnvironment(day_nr=self.day,actual_hour=self.test_hour, battery_power=self.battery_power,
                                            battery_max_discharge=self.battery_max_discharge, pv_scale=self.pv_scale,
                                            priorities=[1,2,3,4,5,6,7])

    def get_values(self):

        if self.hour is None:
            #RealTime-Faker
            if self.test_hour != datetime.datetime.now().hour:
                self.test_hour = datetime.datetime.now().hour
                self.test_env = ControllEnvironment(day_nr=self.day, actual_hour=self.test_hour, battery_power=self.battery_power,
                                                    battery_max_discharge=self.battery_max_discharge,
                                                    pv_scale=self.pv_scale, priorities=[1, 2, 3, 4, 5, 6, 7])
        else:
            #Fixed Hour Values - Add small variations - Normal variations are around 1% (from some simple analysis)
            pass

        start_scenario = self.test_env.get_starting_scenario()

        #Battery State of Charge
        bat_soc = start_scenario[start_scenario.index.hour==self.test_hour]['Battery_SoC'].values[0]

        #DateTime
        curr_dt = start_scenario[start_scenario.index.hour==self.test_hour].index.values[0]
        day  = start_scenario[start_scenario.index.hour==self.test_hour].index.day.values[0]

        #Gens ETc.
        gen_energy = sum(start_scenario[start_scenario.index>=curr_dt]["Generated_Energy"])/1000.0
        cons_energy = sum(start_scenario[start_scenario.index>=curr_dt]["Consumed_Energy"])/1000.0
        system_load = sum(start_scenario[start_scenario.index>=curr_dt]["System_Load"])/1000.0
        bat = Battery(state_of_charge=bat_soc, battery_capacity=self.battery_power,
                      max_discharge=self.battery_max_discharge)
        #Remaining Energy
        remaining_energy = gen_energy - system_load + bat.get_discharge_capacity_left()

        #Generation
        gen = start_scenario[start_scenario.index.hour == self.test_hour]['Generated_Energy'].values[0]/1000.0
        #Consumption
        cons = start_scenario[start_scenario.index.hour == self.test_hour]['Consumed_Energy'].values[0]/1000.0

        #CHarging
        charging = False
        if gen - cons > 0.0:
            charging = True
        resp = {
            "battery state of charge (percentage)":
                [round(bat_soc, 1), "%"],
            "battery energy available (kwh)":
                [round(remaining_energy, 2),"kWh"],
            "system state (charging)":
                [charging,""],
            "power consumption (kw)":
                [ round(cons, 3),"kW"],
            "solar pv power generation (kw)":
                [round(gen, 3),"kW"],
            "solar pv energy generation 24h (kwh)":
                [round(gen_energy, 2),"kWh"],
            "solar pv energy generation 30days (kwh)":
                [ round(gen_energy*day, 2),"kWh"],
            "energy consumption 24h (kwh)":
                [round(cons_energy),"kWh"],
            "energy consumption 30days (kwh)":
                [round(cons_energy*day, 2),"kWh"]
        }
        return resp

dataF = DataFaker()

@app.route('/read_state/v1', methods=['GET'])
def read_state():
    global dataF
    vals = dataF.get_values()
    resp = {}
    for val in vals:
        resp[val] = vals[val][0]

    return Response(json.dumps(resp), 200, content_type='application/json; charset=utf-8')


@app.route('/read_state/v2', methods=['GET'])
def read_state_v2():
    global priorities
    global dataF
    vals = dataF.get_values()
    resp = {}
    resp["system_state"]=[]
    for val in vals:
        resp["system_state"].append([vals[val][0],vals[val][1],val])

        if priorities is None:
            resp["priorities"] ={
                "0": ["Nursery 1 - Lights", "lights"],
                "1": ["Nursery 2 - Lights", "lights"],
                "2": ["Playground - Lights", "lights"],
                "3": ["Nursery 1 - Sockets", "sockets"],
                "4": ["Nursery 2 - Sockets", "sockets"],
                "5": ["Playground - Sockets","sockets"]
            }
        else:
            resp["priorities"] = priorities

    return Response(json.dumps(resp), 200, content_type='application/json; charset=utf-8')


@app.route('/update_priorities', methods=['POST'])
def update_priorities():
    global priorities
    response = request.get_json()
    print(response)
    priorities={}
    for prior in response['priorities']:
        if "Sockets" in response['priorities'][prior]:
            priorities[prior] = [response['priorities'][prior],"sockets"]
        else:
            priorities[prior] = [response['priorities'][prior],"lights"]
    return Response({"success": "Data Submitted Successfully."}, 200, content_type='application/json; charset=utf-8')

@app.route("/")
def template_test():
    return render_template('index.html')


if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True, port=80)
