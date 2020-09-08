import json
from sqlalchemy import create_engine
from sqlalchemy_utils import database_exists, create_database
import os


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

#ToDo Add logging data init
sql_logging_data = json_data["sql_logging_data"]

devices = json_data["devices"]

if "Victron_VenusGX" in devices:
    del devices["Victron_VenusGX"]
allocation = json_data["allocation"]
forecast_sql = json_data["sql_forecast"]

print("Starting Initialisation...")

# Making intiial connection object with Database
db_string = "postgres://" + sql_user + ":" + sql_pw + "@" + sql_addr + ":" + sql_port + "/" + sql_db
db = create_engine(db_string)
if not database_exists(db.url):
    create_database(db.url)
# Make sure table exists and if not create it
db.execute(
    "CREATE TABLE IF NOT EXISTS " + sql_table + " (id SERIAL PRIMARY KEY, timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP, dev_group TEXT, device TEXT, parameter TEXT, value REAL)")

db.execute(
    "CREATE TABLE IF NOT EXISTS " + sql_table2 + " (id SERIAL PRIMARY KEY, timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP, dev_group TEXT, device TEXT, parameter TEXT, value REAL)")

db.execute("CREATE TABLE IF NOT EXISTS "+sql_table3+" (id SERIAL PRIMARY KEY, " + \
           "timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP, " + \
           "Nursery1_Lights INT , Nursery1_Sockets INT , Nursery2_Lights INT , Nursery2_Sockets INT , Playground_Lights INT , Playground_Sockets INT)")
db.execute("INSERT INTO "+sql_table3+" (Nursery1_Lights, Nursery1_Sockets, Nursery2_Lights, Nursery2_Sockets , "+ \
                                     "Playground_Lights, Playground_Sockets)  VALUES (1,2,3,4,5,6)")

# Make sure table exists and if not create it
df_string = "CREATE TABLE IF NOT EXISTS " + sql_aggregate + " (id SERIAL PRIMARY KEY, " + \
            "timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP, " + \
            "Battery_SoC REAL, Consumed_Energy REAL, Generated_Energy REAL, " + \
            "Charged_Energy REAL, System_Load REAL"
for d in devices:
    df_string += ", " + d + " REAL"
df_string += " )"
db.execute(df_string)

#Decision Store
df_string = "CREATE TABLE IF NOT EXISTS "+sql_decision+" (id SERIAL PRIMARY KEY, " + \
            "timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP, " + \
            "dev_group TEXT, device TEXT, state TEXT, group_est_energy_cons REAL, quota_param1 REAL, quota_param2 REAL)"
db.execute(df_string)

forecast_sql
df_string = "CREATE TABLE IF NOT EXISTS "+forecast_sql+" (id SERIAL PRIMARY KEY, " + \
            "timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP, " + \
            "battery_soc REAL, charged_energy REAL, consumed_energy REAL, " + \
            "generated_energy REAL, system_load REAL"
for d in devices:
    df_string += ", " + d + " REAL"
df_string += " )"
db.execute(df_string)

print("Initialisation Done.")