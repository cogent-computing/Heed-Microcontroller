

ALLMODULES=$(patsubst %.py, %.py, $(wildcard tests/test_*.py))

PYTHON = python3 #python/python3
PIP = pip3 #pip/pip3

RUNTEST=${PYTHON} -m unittest -v -b

help:
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}'

install: ## Install all of the python requirements for running any part of the code
	@echo  "Install Requirements..."
	${PIP} install -r requirements.txt

test: ## UnitTests for all the deployment modules
	@echo  "Running Tests..."
	${RUNTEST} ${ALLMODULES}

% : test_%.py
	${RUNTEST} test_$@

initialise_db: ## Initialising the set database with data
	@echo  "Initialising DB Containers..."
	${PYTHON} ./initialisation/initialise_db.py
	${PYTHON} ./initialisation/populate_historic.py 
    

docker_build: ## Building the docker containers that can be used to deploy the microcontroller and interface
	@echo  "Building Containers..."
	docker build -t local/core:latest -f ./docker/core/Dockerfile .
	docker build -t local/mgrid_controller:latest -f ./docker/deployment/Dockerfile .
	docker build -t local/web_control:latest -f ./docker/interface/Dockerfile .
	docker build -t local/dummy_web_control:latest -f ./docker/interface_simulated/Dockerfile .


docker_run: docker_build ## Deploying the docker containers that were built using docker_build. If containers exists will skip.
	@echo  "Deploying Containers..."
	docker start heed-postgres || ( docker run --restart=always --name heed-postgres -e POSTGRES_PASSWORD=energy -p 5432:5432 -d postgres && sleep 15 && \
	${PYTHON} ./initialisation/initialise_db.py && \
	${PYTHON} ./initialisation/populate_historic.py )
	docker start Web_UI || docker run  -p 80:80 --name Web_UI --restart=always -d local/web_control:latest
	docker start MGrid_Controller || docker run  --restart=always  --name MGrid_Controller -d local/mgrid_controller:latest

docker_run_simulated: docker_build ## Deploying the docker container that has the interface and simualted data for visualisation purposes
	@echo  "Deploying Simulated Web Interface..."
	docker start heed-postgres || ( docker run --restart=always --name heed-postgres -e POSTGRES_PASSWORD=energy -p 5432:5432 -d postgres && sleep 15 && \
	${PYTHON} ./initialisation/initialise_db.py && \
	${PYTHON} ./initialisation/populate_historic.py )
	docker start Web_UI_Sim || docker run  --restart=always -p 85:80 --name Web_UI_Sim --restart=always -d local/dummy_web_control:latest

.PHONY: help install test

.DEFAULT_GOAL := help