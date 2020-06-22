FROM local/core:latest

ADD ../../Web_UI/index.py /
ADD ../../Web_UI/index_testing.py /
ADD ../../config/runner_config.json /
ADD ../../Web_UI/templates /templates
ADD ../../Web_UI/static /static

EXPOSE 80/tcp

CMD [ "python","-u", "./index.py" ]
