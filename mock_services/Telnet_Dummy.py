import asyncio
import telnetlib3
import random

equivalency = {"System overview _AC Consumption L1_W[Combined]": "VenusGX/Ac/Consumption/L1/Power",
               "Solar Charger _PV power_[Combined]": "VenusGX/Dc/Pv/Power",
               "Battery Monitor _Discharged Energy_kWh[Combined]": "VenusGX/Dc/Battery/Power",  # negative
               "Battery Monitor _Charged Energy_kWh[Combined]": "VenusGX/Dc/Battery/Power",  # pozitive
               "System overview _Battery State of Charge_%[Combined]": "VenusGX/Dc/Battery/Soc"}

mac_to_device = {"Victron_VenusGX": "51:00:C0:A8:00:64",
                 "Streetlight_No_1": "C1:7D:8B:1B:05:D1",
                 "Streetlight_No_2": "C1:0B:D6:9B:F8:9F",
                 "Streetlight_No_3": "C1:01:D5:B2:52:26",
                 "Playground_No_1": "C1:06:7A:88:7B:87",
                 "Playground_No_2": "C1:21:A0:94:32:B9",
                 "Playground_No_3": "C1:34:8F:12:71:21",
                 "Playground_No_4": "C1:A6:B9:27:37:8E",
                 "Playground_No_5": "C1:D2:3C:72:22:02",
                 "Playground_AC_socket_No_1": "AF:00:D1:F2:00:77",
                 "Playground_AC_Socket_No_2": "AF:00:AD:73:59:32",
                 "Nursery_AC_Socket_1A_No_1": "AF:00:85:14:0F:83",
                 "Nursery_AC_Socket_1A_No_2": "AF:00:5A:55:F3:A1",
                 "Nursery_AC_Socket_1B": "AF:00:74:D1:F7:55",
                 "Nursery_AC_Socket_1C": "AF:00:92:9A:6C:E4",
                 "Nursery_1A_CPE_No_1": "C1:87:13:40:AC:87",
                 "Nursery_1A_CPE_No_2": "C1:6B:C3:2B:92:E9",
                 "Nursery_1B_CPE_No_3": "C1:78:4A:43:01:E9",
                 "Nursery_1B_CPE_No_4": "C1:9A:18:8C:9F:56",
                 "Nursery_1C_CPE_No_5": "C1:D6:90:D0:CF:A5",
                 "Nursery_1C_CPE_No_6": "C1:A2:8B:7A:EE:AD",
                 "Nursery_AC_Socket_2A_No_1": "AF:00:23:B4:83:68",
                 "Nursery_AC_Socket_2A_No_2": "AF:00:91:CB:2A:DF",
                 "Nursery_AC_Socket_2B": "AF:00:25:DD:5A:36",
                 "Nursery_AC_Socket_2C": "AF:00:D7:E3:83:3A",
                 "Nursery_2A_CPE_No_7": "C1:3D:A8:2C:E1:86",
                 "Nursery_2A_CPE_No_8": "C1:4D:1A:9E:F8:9B",
                 "Nursery_2B_CPE_No_9": "C1:0E:43:52:4D:2B",
                 "Nursery_2B_CPE_No_10": "C1:93:5D:B7:B3:CA",
                 "Nursery_2C_CPE_No_11": "C1:21:51:3B:B0:E3",
                 "Nursery_2C_CPE_No_12": "C1:F4:4D:9D:E8:21"
                 }

allocation = {
    "Nursery1_Lights": ["Nursery_1A_CPE_No_1","Nursery_1A_CPE_No_2", "Nursery_1B_CPE_No_3", "Nursery_1B_CPE_No_4",
                        "Nursery_1C_CPE_No_5", "Nursery_1C_CPE_No_6"],
    "Nursery1_Sockets": ["Nursery_AC_Socket_1A_No_1","Nursery_AC_Socket_1A_No_2",
                         "Nursery_AC_Socket_1B","Nursery_AC_Socket_1C"],
    "Nursery2_Lights": ["Nursery_2A_CPE_No_7","Nursery_2A_CPE_No_8",
                        "Nursery_2B_CPE_No_9", "Nursery_2B_CPE_No_10",
                        "Nursery_2C_CPE_No_11", "Nursery_2C_CPE_No_12"],
    "Nursery2_Sockets": ["Nursery_AC_Socket_2A_No_1", "Nursery_AC_Socket_2A_No_2",
                         "Nursery_AC_Socket_2B", "Nursery_AC_Socket_2C"],
    "Playground_Lights": ["Playground_No_1", "Playground_No_2",
                          "Playground_No_3", "Playground_No_4", "Playground_No_5"],
    "Playground_Sockets": ["Playground_AC_socket_No_1", "Playground_AC_Socket_No_2"],
    "Streetlights": ["Streetlight_No_1", "Streetlight_No_2", "Streetlight_No_3"]
}

# Need it in this format for the code
dev_alloc = {v: k for k, v in mac_to_device.items()}


@asyncio.coroutine
def shell(reader, writer):
    writer.write('\r\nHello\r\n')
    inp = yield from reader.read(1024)
    if inp.split(" ")[0].strip() == "s" and inp.split(" ")[1].strip() == "get_vars" and len(inp.split(" ")) == 3:
        if inp.split(" ")[2].strip() in dev_alloc.keys():
            dev_name = dev_alloc[inp.split(" ")[2].strip()]
            print("Device: " + dev_alloc[inp.split(" ")[2].strip()] + " found with Mac: " + inp.split(" ")[2].strip())
            if "AC" in dev_name:
                print("Socket Data")
                writer.write('\r\nvRELAY1_LVL	 ' + str(random.randint(0, 100)) + '\n' + \
                             'cRELAY1_EN	1\n' + \
                             'cRELAY1_VALID	1\n' + \
                             'vRELAY1_MAX_LVL	50000\n' + \
                             'vRELAY1_STATUS	USED\n' + \
                             'AC_Day_Energy_unit	5\n' + \
                             'AC_Day_Energy_rangehi	50000\n' + \
                             'AC_Day_Energy_rangelo	1\n' + \
                             'AC_Day_Energy_total	1000\n' + \
                             'AC_Day_Energy_session	0\n' + \
                             'AC_Day_Energy_tag	1578369601\n' + \
                             'AC_Day_Energy_remain	999\n' + \
                             'uptime	151002\n' + \
                             'vRELAY1_V	230300\n' + \
                             'vRELAY1_I	0\n' + \
                             'vRELAY1_VA	0\n' + \
                             'vRELAY1_PF	0\n' + \
                             'vRELAY1_LIMIT	50000\r\n'
                             )
            elif "Victron_VenusGX" in dev_name:
                print("Victron Data")
                writer.write('\r\nVenusGX/Ac/PvOnGenset/L2/Power	0\n' + \
                             'VenusGX/Dc/Pv/Power	' + str(random.randint(0, 500)) + '\n' + \
                             'VenusGX/Ac/Consumption/L1/Power	' + str(random.randint(0, 700)) + '\n' + \
                             'VenusGX/Ac/Consumption/L2/Power	0\n' + \
                             'VenusGX/Dc/Battery/Power	' + str(random.randint(-500, 500)) + '\n' + \
                             'VenusGX/Dc/Battery/Soc	' + str(random.randint(40, 99)) + '\n' + \
                             'VenusGX/Relay/0/State	0:Open\r\n')
            else:
                print("Light CPE Data")
                writer.write('\r\nLED3_lvl	0\n' + \
                             'LED1_lvl	' + str(random.randint(0, 15000)) + '\n' + \
                             'TV1_targ_v	9000\n' + \
                             'LED1_P	' + str(random.randint(0, 15000)) + '\n' + \
                             'LED2_max_lvl   190\n' + \
                             'LED_BL_unit	8\n' + \
                             'LED3_lvl	0\n' + \
                             'LED_BL_rangehi	190\n' + \
                             'LED2_lvl	0\n' + \
                             'LED3_max_lvl	190\n' + \
                             'LED1_P	' + str(random.randint(0, 15000)) + '\n' + \
                             'LED2_max_lvl	190\n' + \
                             'LED_BL_unit  8\n' + \
                             'LED_BL_rangehi 10\n' + \
                             'LED_BL_rangelo 0\n' + \
                             'LED_BL_total 4320\n' + \
                             'LED_BL_session 0\n' + \
                             'LED_BL_tag 1569988801\n' + \
                             'LED_BL_remain 4320\n' + \
                             'LED1_limit	190\n' + \
                             'uptime	1005489\n' + \
                             'LED3_lvl	0\n' + \
                             'LED2_P	' + str(random.randint(0, 15000)) + '\n' + \
                             'LED3_P	' + str(random.randint(0, 15000)) + '\n' + \
                             'LED_NL_rangehi	10\n' + \
                             'LED1_lvl	160\n' + \
                             'LED1_P	' + str(random.randint(0, 15000)) + '\n' + \
                             'LED2_limit	190\n' + \
                             'LED1_lvl	0\n' + \
                             'LED_NL_unit  8\n' + \
                             'LED_NL_rangehi 10\n' + \
                             'LED_NL_rangelo 0\n' + \
                             'LED_NL_total 4320\n' + \
                             'LED_NL_session 0\n' + \
                             'LED_NL_tag 1569988801\n' + \
                             'LED_NL_remain 4320\n' + \
                             'LED1_limit	190\n' + \
                             'LED2_max_lvl	190\n' + \
                             'LED2_max_lvl	190\n' + \
                             'LED3_P	' + str(random.randint(0, 15000)) + '\r\n')
        else:
            print("Device not found with MAC: " + inp.split(" ")[2])
            writer.write('\r\nDevice Not Found\r\n')
        yield from writer.drain()
    writer.close()


loop = asyncio.get_event_loop()
coro = telnetlib3.create_server(port=6023, shell=shell)
server = loop.run_until_complete(coro)
loop.run_until_complete(server.wait_closed())
