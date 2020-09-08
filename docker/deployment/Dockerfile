FROM local/core:latest

ADD ./deployment/Battery.py /deployment/Battery.py
ADD ./deployment/Control_Enactor.py /deployment/Control_Enactor.py
ADD ./deployment/Controller.py /deployment/Controller.py
ADD ./deployment/Data_Aggregator.py /deployment/Data_Aggregator.py
ADD ./deployment/Data_Retreiver.py /deployment/Data_Retreiver.py
ADD ./deployment/Forecaster_v2.py /deployment/Forecaster_v2.py
ADD ./deployment/Forecaster.py /deployment/Forecaster.py
ADD ./deployment/Local_Logger.py /deployment/Local_Logger.py
ADD ./deployment/Remote_Logger.py /deployment/Remote_Logger.py
ADD ./deployment/Runner.py /deployment/Runner.py
ADD ./deployment/WebsiteSpoof.py /deployment/WebsiteSpoof.py
ADD ./config/private_sftp.ppk /config/private_sftp.ppk
ADD ./config/runner_config.json /config/runner_config.json

RUN mkdir /deployment/plans

CMD [ "python","-u", "./deployment/Runner.py" ]