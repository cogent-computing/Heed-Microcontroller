#!flask/bin/python
from flask import Flask, Response, request, render_template
import json
from sqlalchemy import create_engine
from flask_cors import CORS;
import datetime
import random

app = Flask(__name__);
CORS(app);


@app.route('/read_state/v1', methods=['GET'])
def read_state():
    resp = {
        "battery state of charge (percentage)": round(random.uniform(5.0, 100.0), 1),
        "battery energy available (kwh)": round(random.uniform(1.0, 9.7), 2),
        "system state (charging)": random.choice([True, False]),
        "power consumption (kw)": round(random.uniform(0.1, 2.0), 3),
        "solar pv power generation (kw)": round(random.uniform(0.1, 5.0), 3),
        "solar pv energy generation 24h (kwh)": round(random.uniform(1.5, 5.9), 2),
        "solar pv energy generation 30days (kwh)": round(random.uniform(130.8, 200.1), 2),
        "energy consumption 24h (kwh)": round(random.uniform(0.8, 7.6), 2),
        "energy consumption 30days (kwh)": round(random.uniform(60.8, 200.1), 2)
    }

    return Response(json.dumps(resp), 200, content_type='application/json; charset=utf-8')


@app.route('/read_state/v2', methods=['GET'])
def read_state_v2():
    resp = {
        "system_state": [  # Format of [Quantity, Unit, Text] where Unit and Text will remain the same
            [round(random.uniform(5.0, 100.0), 1), "%", "battery state of charge (percentage)"],
            [round(random.uniform(1.0, 9.7), 2),"kWh", "battery energy available (kwh)"],
            [random.choice([True, False]), "","system state (charging)"],
            [round(random.uniform(0.1, 2.0), 3), "kW","power consumption (kw)"],
            [round(random.uniform(0.1, 5.0), 3),"kW", "solar pv power generation (kw)"],
            [round(random.uniform(1.5, 5.9), 2), "kWh","solar pv energy generation 24h (kwh)"],
            [round(random.uniform(130.8, 200.1), 2), "kWh","solar pv energy generation 30days (kwh)"],
            [round(random.uniform(0.8, 7.6), 2),"kWh", "energy consumption 24h (kwh)"],
            [round(random.uniform(60.8, 200.1), 2),"kWh","energy consumption 30days (kwh)"]
        ],
        "priorities": {
            "0": ["Nursery 1 - Lights", "lights"],
            "1": ["Nursery 2 - Lights", "lights"],
            "2": ["Playground - Lights", "lights"],
            "3": ["Nursery 1 - Sockets", "sockets"],
            "4": ["Nursery 2 - Sockets", "sockets"],
            "5": ["Playground - Sockets","sockets"]
        }
    }

    return Response(json.dumps(resp), 200, content_type='application/json; charset=utf-8')


@app.route('/update_priorities', methods=['POST'])
def update_priorities():
    response = request.get_json()
    print(response)
    return Response({"success": "Data Submitted Successfully."}, 200, content_type='application/json; charset=utf-8')

@app.route("/")
def template_test():
    return render_template('index.html')


if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True, port=80)
