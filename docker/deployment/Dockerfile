FROM local/core_v2:latest

ADD ../../deployment/Battery.py /
ADD ../../deployment/Control_Enactor.py /
ADD ../../deployment/Controller.py /
ADD ../../deployment/Data_Aggregator.py /
ADD ../../deployment/Data_Retreiver.py /
ADD ../../deployment/Forecaster_v2.py /
ADD ../../deployment/Forecaster.py /
ADD ../../deployment/Local_Logger.py /
ADD ../../deployment/Remote_Logger.py /
ADD ../../deployment/Runner.py /
ADD ../../deployment/WebsiteSpoof.py /
ADD ../../config/private_sftp.ppk /
ADD ../../config/runner_config.json /

RUN mkdir plans

CMD [ "python","-u", "./Runner.py" ]