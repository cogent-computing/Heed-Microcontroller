var LANG = 'en';

const TRANS = {
    'en': {
        "_lang": "English",
        "N/A": "---",

        "Nursery 1 - Lights": "Nursery 1",
        "Nursery 1 - Sockets": "Nursery 1",
        "Nursery 2 - Lights": "Nursery 2",
        "Nursery 2 - Sockets": "Nursery 2",
        "Playground - Lights": "Playground",
        "Playground - Sockets": "Playground",
        
        "battery state of charge (percentage)": "Battery state of charge",
        "power consumption (kw)": "Power consumption",
        "battery energy available (kwh)": "Battery energy available",
        "solar pv power generation (kw)": "Solar PV power generation",
        "solar pv energy generation 24h (kwh)": "Solar PV energy generation over 24 hours",
        "solar pv energy generation 30days (kwh)": "Solar PV energy generation over 30 days",
        "energy consumption 24h (kwh)": "Energy consumption over 24 hours",
        "energy consumption 30days (kwh)": "Energy consumption over 30 days",
        "forecasted energy consumption 24h (kwh)":"Forecasted energy consumption over 24 hours",
        "forecasted energy generation 24h (kwh)":"Forecasted Solar PV energy generation over 24 hours",

        "_HELP_battery state of charge (percentage)":
            "Battery state of charge (%): Percentage of battery energy available for use",
        "_HELP_power consumption (kw)":
            "Power consumption (kW): Current energy use (kilowatts)",
        "_HELP_battery energy available (kwh)":
            "Battery energy available (kWh): Kilowatt hours of battery energy available for use",
        "_HELP_solar pv power generation (kw)":
            "Solar PV power generation (kW): Current solar PV generation (kilowatts)",
        "_HELP_solar pv energy generation 24h (kwh)":
            "Solar PV energy generation over 24 hours (kWh): Total solar PV generation over last 24 hours (kilowatt hours)",
        "_HELP_solar pv energy generation 30days (kwh)":
            "Solar PV energy generation over 30 days (kWh): Average solar PV generation over last 30 days (kilowatt hours)",
        "_HELP_energy consumption 24h (kwh)":
            "Energy consumption over 24 hours (kWh): Total energy use over last 24 hours (kilowatt hours)",
        "_HELP_energy consumption 30days (kwh)":
            "Energy consumption over 30 days (kWh): Average energy use over last 30 days (kilowatt hours)",
        "_HELP_forecasted energy consumption 24h (kwh)":
            "Forecasted energy consumption over 24 hours: Total predicted energy use for the next 24 hours (kilowatt hours)",
        "_HELP_forecasted energy generation 24h (kwh)":
            "Forecasted Solar PV energy generation over 24 hours: Total predicted PV generation for the next 24 hours (kilowatt hours)",


        "_HELP_PRIO": "Drag the location/load boards to set load priority",
        "_HELP_METRIC": "Press the metric selection button to choose the metric to display",
    },
    'rw': {
        "_lang": "Kinyarwanda",
        "N/A": "---",
        "Priority Level": "Urwego rwibanze",
        "High": "Hejuru",
        "Low": "Hasi",
        "Help": "Ubufasha",
        
        "Nursery 1 - Lights": "Mashuri y'incuke 1",
        "Nursery 1 - Sockets": "Mashuri y'incuke 1",
        "Nursery 2 - Lights": "Mashuri y'incuke 2",
        "Nursery 2 - Sockets": "Mashuri y'incuke 2",
        "Playground - Lights": "Kibuga",
        "Playground - Sockets": "Kibuga",
        
        "system state (charging)": "Sisitemu Leta",
        "power consumption (kw)": "Gukoresha ingufu",
        "battery state of charge (percentage)": "Imiterere ya Bateri",
        "battery energy available (kwh)": "Ingufu za bateri zirahari",
        "solar pv power generation (kw)": "Imirasire y'izuba PV",
        "solar pv energy generation 24h (kwh)": "Imirasire y'izuba PV mu masaha 24",
        "solar pv energy generation 30days (kwh)": "Imirasire y'izuba PV muminsi 30",
        "energy consumption 24h (kwh)": "Gukoresha ingufu mu masaha 24",
        "energy consumption 30days (kwh)": "Gukoresha ingufu muminsi 30",
        "forecasted energy consumption 24h (kwh)":"Gukoresha ingufu mumasaha 24 ari imbere",
        "forecasted energy generation 24h (kwh)":"Imirasire y'izuba biteganijwe PV mu masaha 24",

        "_HELP_battery state of charge (percentage)":
            "Imiterere ya Bateri (%): Ijanisha ryingufu za bateri ziboneka kugirango ukoreshwe",
        "_HELP_power consumption (kw)":
            "Gukoresha ingufu (kW): Gukoresha ingufu zubu (kilowatts)",
        "_HELP_battery energy available (kwh)":
            "Ingufu za Bateri ziraboneka (kWh): Amasaha ya kilowatt yingufu za batiri ziboneka gukoreshwa",
        "_HELP_solar pv power generation (kw)":
            "Amashanyarazi akomoka ku mirasire y'izuba (kW): Imirasire y'izuba ya PV (kilowatts)",
        "_HELP_solar pv energy generation 24h (kwh)":
            "Amashanyarazi akomoka ku mirasire y'izuba mu masaha 24 (kWh): Amashanyarazi akomoka ku mirasire y'izuba mu masaha 24 ashize (amasaha kilowatt)",
        "_HELP_solar pv energy generation 30days (kwh)":
            "Amashanyarazi akomoka ku mirasire y'izuba mu minsi 30 (kWh): Impuzandengo y'izuba rya PV mu minsi 30 ishize (amasaha kilowatt)",
        "_HELP_energy consumption 24h (kwh)":
            "Gukoresha ingufu mu masaha 24 (kWh): Gukoresha ingufu zose mumasaha 24 ashize (amasaha kilowatt)",
        "_HELP_energy consumption 30days (kwh)":
            "Gukoresha ingufu muminsi 30 (kWh): Ikigereranyo cyo gukoresha ingufu muminsi 30 ishize (amasaha kilowatt)",
        "_HELP_forecasted energy consumption 24h (kwh)":
            "Gukoresha ingufu mumasaha 24 ari imbere: Gukoresha ingufu mu masaha 24 ari imbere (kilowatt)",
        "_HELP_forecasted energy generation 24h (kwh)":
            "Imirasire y'izuba biteganijwe PV mu masaha 24: Imirasire y'izuba mu masaha 24 ari imbere (amasaha ya kilowatt)",
        
        "_HELP_PRIO": "Kurura ikibanza / imizigo kugirango ushireho umutwaro wibanze",
        "_HELP_METRIC": "Kanda buto yo guhitamo buto kugirango uhitemo ibipimo byo kwerekana",
    }
};

function L(key, lang)
{
    lang = lang || LANG;
    return TRANS[lang][key] || (lang == 'en' ? key : ('(' + lang + ') ' + key));
}
