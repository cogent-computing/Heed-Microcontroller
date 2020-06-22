#!flask/bin/python
from flask import Flask, Response, request, render_template
import json
from sqlalchemy import create_engine
from flask_cors import CORS;
import datetime

app = Flask(__name__);
CORS(app);

#Docker and Local Run
try:
    with open('runner_config.json') as json_file:
        json_data = json.load(json_file)
except FileNotFoundError as Ex:
    print("File not found looking in local run")
    with open('../config/runner_config.json') as json_file:
        json_data = json.load(json_file)

sql_table_aggre = json_data["sql_aggregate"]
sql_table_raw = json_data["sql_raw_energy"]
sql_table_forecast = json_data["sql_forecast"]
sql_table_preference = json_data["sql_preference"]

# Settign Up SQL Credentials and details
sql_user = json_data["sql_user"]
sql_pw = json_data["sql_pw"]
sql_db = json_data["sql_db"]
sql_addr = json_data["sql_addr"]
sql_port = json_data["sql_port"]

# Making intiial connection object with Database
db_string = "postgres://" + sql_user + ":" + sql_pw + "@" + sql_addr + ":" + sql_port + "/" + sql_db
db = create_engine(db_string)


def get_priorities():
    label_eqiv = {"nursery1_lights": ["Nursery 1 - Lights", "lights"],
                  "nursery2_lights": ["Nursery 2 - Lights", "lights"],
                  "playground_lights": ["Playground - Lights", "lights"],
                  "nursery1_sockets": ["Nursery 1 - Sockets", "sockets"],
                  "nursery2_sockets": ["Nursery 2 - Sockets", "sockets"],
                  "playground_sockets": ["Playground - Sockets", "sockets"]}

    db_string = """ SELECT * FROM """ + sql_table_preference + """ ORDER BY timestamp DESC LIMIT 1 """
    ret = db.execute(db_string)
    ret_all = ret.fetchone()
    if len(ret_all) == 0:
        print("No Data Available for priorities at: ", datetime.datetime.now())
        priorities = {
            "0": ["Nursery 1 - Lights", "lights"],
            "1": ["Nursery 2 - Lights", "lights"],
            "2": ["Playground - Lights", "lights"],
            "3": ["Nursery 1 - Sockets", "sockets"],
            "4": ["Nursery 2 - Sockets", "sockets"],
            "5": ["Playground - Sockets", "sockets"]
        }
    else:
        priorities = {}
        dict_all = dict(ret_all)
        for v in label_eqiv:
            priorities[dict_all[v]] = label_eqiv[v]
    return priorities


priorities = get_priorities()


@app.route('/read_state/v1', methods=['GET'])
def read_state():
    # monthly consumption and generation values
    db_string = """ SELECT SUM(consumed_energy) AS consumed_total, SUM(generated_energy) AS generated_total FROM 
            """ + sql_table_aggre + """ WHERE "timestamp" >= date_trunc('month', CURRENT_DATE)"""
    ret_month = db.execute(db_string).fetchall()

    # daily feneration and consumption values
    db_string = """ SELECT SUM(consumed_energy) AS consumed_total, SUM(generated_energy) AS generated_total FROM 
                """ + sql_table_aggre + """ WHERE "timestamp" >= date_trunc('day', CURRENT_DATE)"""
    ret_24h = db.execute(db_string).fetchall()

    # current PV
    db_string = """ SELECT value FROM """ + sql_table_raw + """ WHERE parameter='VenusGX/Dc/Pv/Power' 
                ORDER BY "timestamp" DESC LIMIT 1"""
    ret_pv = db.execute(db_string).fetchall()

    # current SOC
    db_string = """ SELECT value FROM """ + sql_table_raw + """ WHERE parameter='VenusGX/Dc/Battery/Soc' 
                ORDER BY "timestamp" DESC LIMIT 1"""
    ret_soc = db.execute(db_string).fetchall()

    # current Consumption
    db_string = """ SELECT value FROM """ + sql_table_raw + """ WHERE parameter='VenusGX/Ac/Consumption/L1/Power' 
                ORDER BY "timestamp" DESC LIMIT 1"""
    ret_cons = db.execute(db_string).fetchall()

    # System State - Charging Not Charging
    db_string = """ SELECT value FROM """ + sql_table_raw + """ WHERE parameter='VenusGX/Dc/Battery/Power' 
                ORDER BY "timestamp" DESC LIMIT 1"""
    ret_charge = db.execute(db_string).fetchall()
    charging = False
    if float(ret_charge[0][0]) > 0.0:
        charging = True

    # Energy Avialable - Dummy placeholder
    avail_energy = (float(ret_soc[0][0]) - 40.0) / 100.0 * 21.1
    if avail_energy < 0:
        avail_energy = 0.0

    resp = {
        "battery state of charge (percentage)": float(ret_soc[0][0]),
        "battery energy available (kwh)": avail_energy,
        "system state (charging)": charging,
        "power consumption (kw)": float(ret_cons[0][0]) / 1000.0,
        "solar pv power generation (kw)": float(ret_pv[0][0]) / 1000.0,
        "solar pv energy generation 24h (kwh)": float(ret_24h[0][1]) / 1000.0,
        "solar pv energy generation 30days (kwh)": float(ret_month[0][1]) / 1000.0,
        "energy consumption 24h (kwh)": float(ret_24h[0][0]) / 1000.0,
        "energy consumption 30days (kwh)": float(ret_month[0][0]) / 1000.0
    }

    return Response(json.dumps(resp), 200, content_type='application/json; charset=utf-8')


@app.route('/read_state/v2', methods=['GET'])
def read_state_v2():
    # monthly consumption and generation values
    db_string = """ SELECT SUM(consumed_energy) AS consumed_total, SUM(generated_energy) AS generated_total FROM 
                """ + sql_table_aggre + """ WHERE "timestamp" >= date_trunc('month', CURRENT_DATE)"""
    ret_month = db.execute(db_string).fetchall()
    try:
        ret_month_1 = round(float(ret_month[0][0]) / 1000.0, 3)
        ret_month_2 = round(float(ret_month[0][1]) / 1000.0, 3)
    except TypeError:
        print("Consumption Aggre Null so setting it to -1.0")
        ret_month_1=-1.0
        ret_month_2=-1.0

    # daily feneration and consumption values
    db_string = """ SELECT SUM(consumed_energy) AS consumed_total, SUM(generated_energy) AS generated_total FROM 
                    """ + sql_table_aggre + """ WHERE "timestamp" >= date_trunc('day', CURRENT_DATE)"""
    ret_24h = db.execute(db_string).fetchall()
    try:
        ret_24h_1 = round(float(ret_24h[0][0]) / 1000.0, 3)
        ret_24h_2 = round(float(ret_24h[0][1]) / 1000.0, 3)
    except TypeError:
        print("PV Generation Aggre Null so setting it to -1.0")
        ret_24h_1=-1.0
        ret_24h_2=-1.0

    # current PV
    db_string = """ SELECT value FROM """ + sql_table_raw + """ WHERE parameter='VenusGX/Dc/Pv/Power' 
                    ORDER BY "timestamp" DESC LIMIT 1"""
    ret_pv = db.execute(db_string).fetchall()
    try:
        pv_gen = round(float(ret_pv[0][0]) / 1000.0, 3)
    except TypeError:
        print("PV Generation Null so setting it to -1.0")
        pv_gen=-1.
    except IndexError:
        print("PV Generation Null so setting it to -1.0")
        pv_gen=-1.0

    # current SOC
    db_string = """ SELECT value FROM """ + sql_table_raw + """ WHERE parameter='VenusGX/Dc/Battery/Soc' 
                    ORDER BY "timestamp" DESC LIMIT 1"""
    ret_soc = db.execute(db_string).fetchall()
    try:
        bat_soc = round(float(ret_soc[0][0]), 0)
        # Energy Avialable - Dummy placeholder - Need to update with forecast
        avail_energy = (float(ret_soc[0][0]) - 40.0) / 100.0 * 21.1
        if avail_energy < 0:
            avail_energy = 0.0
    except TypeError:
        print("Battery_SoC and Avail Energy Null so setting it to -1.0")
        bat_soc=-1.0
        avail_energy=-1.0
    except IndexError:
        print("Battery_SoC and Avail Energy Null so setting it to -1.0")
        bat_soc=-1.0
        avail_energy=-1.0

    # current Consumption
    db_string = """ SELECT value FROM """ + sql_table_raw + """ WHERE parameter='VenusGX/Ac/Consumption/L1/Power' 
                    ORDER BY "timestamp" DESC LIMIT 1"""
    ret_cons = db.execute(db_string).fetchall()
    try:
        curr_cons = round(float(ret_cons[0][0]) / 1000.0, 3)
    except TypeError:
        print("Consumption Null so setting it to -1.0")
        curr_cons=-1.0
    except IndexError:
        print("Consumption Null so setting it to -1.0")
        curr_cons=-1.0

    # System State - Charging Not Charging
    db_string = """ SELECT value FROM """ + sql_table_raw + """ WHERE parameter='VenusGX/Dc/Battery/Power' 
                    ORDER BY "timestamp" DESC LIMIT 1"""
    ret_charge = db.execute(db_string).fetchall()
    charging = False
    try:
        if float(ret_charge[0][0]) > 0.0:
            charging = True
    except TypeError:
        print("Charging Null so setting it to -1.0")
        curr_cons=0.0
    except IndexError:
        print("Charging Null so setting it to -1.0")
        curr_cons=0.0

    resp = {
        "system_state": [  # Format of [Quantity, Unit, Text] where Unit and Text will remain the same
            [bat_soc, "%", "battery state of charge (percentage)"],
            [round(avail_energy, 3), "kWh", "battery energy available (kwh)"],
            [charging, "", "system state (charging)"],
            [curr_cons, "kW", "power consumption (kw)"],
            [pv_gen, "kW", "solar pv power generation (kw)"],
            [ret_24h_2, "kWh", "solar pv energy generation 24h (kwh)"],
            [ret_month_2, "kWh", "solar pv energy generation 30days (kwh)"],
            [ret_24h_1, "kWh", "energy consumption 24h (kwh)"],
            [ret_month_1, "kWh", "energy consumption 30days (kwh)"]
        ],
        "priorities": get_priorities()
    }

    return Response(json.dumps(resp), 200, content_type='application/json; charset=utf-8')


@app.route('/update_priorities', methods=['POST'])
def update_priorities():
    global priorities
    response = request.get_json()['priorities']
    print(response)
    print(response.values())
    prior_list = [x[0] for x in list(priorities.values())]
    print(prior_list)
    if len([x for x in response.values() if x not in prior_list]) > 0:
        print({"failure": "The devices that were sent back are not the known ones"})
        return Response({"failure": "The devices that were sent back are not the known ones"}, 422,
                        content_type='application/json; charset=utf-8')

    # Update Priorities
    for resp in response:
        if "ights" in response[resp]:
            priorities[resp] = [response[resp], 'lights']
        else:
            priorities[resp] = [response[resp], 'sockets']

    dev_list = "("
    val_list = "("
    for r in response:
        dev_list += response[r].replace(" ", "").replace("-", "_").lower() + ", "
        val_list += str(r) + ", "

    dev_list += " timestamp)"
    val_list += "'%s')" % (datetime.datetime.now())

    db_string = """INSERT INTO  """ + sql_table_preference + """ """ + dev_list + """ 
                                        VALUES """ + val_list
    print(db_string)
    db.execute(db_string)

    return Response({"success": "Data Submitted Successfully."}, 200, content_type='application/json; charset=utf-8')


@app.route("/")
def template_test():
    return render_template('index.html')


if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=False, port=80)
