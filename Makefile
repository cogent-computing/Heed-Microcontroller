RUNTEST=python -m unittest -v -b

ALLMODULES=$(patsubst %.py, %.py, $(wildcard tests/test_*.py))

help:
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}'

install: ## Install all of the python requirements for running any part of the code
	@echo  "Install Requirements..."
	pip install -r requirements.txt

test: ## UnitTests for all the deployment modules
	@echo  "Running Tests..."
	${RUNTEST} ${ALLMODULES}

% : test_%.py
	${RUNTEST} test_$@


docker_build: ## Building the docker containers that can be used to deploy the microcontroller and interface
	@echo  "Building Containers..."
    #TODO

docker_run ## Deploying the docker containers that were built using docker_build
  	@echo  "Deploying Containers..."
    #TODO

.PHONY: help install test

.DEFAULT_GOAL := help