FROM local/core:latest

RUN pip install install flask_monitoringdashboard

ADD ./deployment/Battery.py /deployment/Battery.py
ADD ./simulation_evaluation/microgrid_simulator.py /simulation_evaluation/microgrid_simulator.py
ADD ./data/microgrid_processed_august.csv /data/microgrid_processed_august.csv
ADD ./Web_UI/index.py /Web_UI/index.py
ADD ./Web_UI/index_testing.py /Web_UI/index_testing.py
ADD ./config/runner_config.json /config/runner_config.json
ADD ./Web_UI/templates /Web_UI/templates
ADD ./Web_UI/static /Web_UI/static
ADD ./Web_UI/dashboard.conf /Web_UI/dashboard.conf
EXPOSE 80/tcp

#WORKDIR /Web_UI

#CMD [ "python","-u", "./Web_UI/index.py" ]
CMD [ "python","-u", "./Web_UI/index_testing.py" ]