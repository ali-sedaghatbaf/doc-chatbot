##@ Subcommands
help:  ## Display this help
	@awk 'BEGIN {FS = ":.*##"; printf "\nUsage:\n  make \033[36m\033[0m\n"} /^[\/0-9a-zA-Z_-]+:.*?##/ { printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2 } /^##@/ { printf "\n\033[1m%s\033[0m\n", substr($$0, 5) } ' $(MAKEFILE_LIST)

##@ Installation
install-base: ## Install and upgrade uv
	python3 -m pip install -U pip uv

install:: install-base ## Install dependencies needed for a production environment
	@echo "Installing dependencies..."
	uv install --only main

install-dev:: install-base ## Install dependencies needed for a local/development environment
	@echo "Installing dependencies..."
	uv install --with dev,test

install-ci: ## Install dependencies needed for a CI environment
	@echo "Installing dependencies..."
	uv install --only dev,test

install-docs: ## Install dependencies needed for publishing documentation to KEP portal
	@echo "Installing dependencies..."
	uv install --only docs

lock:: ## Lock dependencies
	uv lock

##@ Clean up
clean-build: ## Delete the Python build files and folders
	rm -fr build/
	rm -fr dist/
	rm -fr *.egg-info
	rm -fr *.spec
	rm -fr .ipynb_checkpoints/

clean-pyc: ## Delete the Python intermediate execution files
	find . -name '*~' -exec rm -f {} +
	find . -name '*.log*' -delete
	find . -name '*_cache' -exec rm -rf {} +
	find . -name '*.egg-info' -exec rm -rf {} +
	find . -name '*.pyc' -exec rm -f {} +
	find . -name '*.pyo' -exec rm -f {} +
	find . -name '__pycache__' -exec rm -rf {} +
	find . -name '*.ipynb' -exec rm -f {} +

clean-env:  ## Delete python virtual environment
	uv env remove --all

clean: clean-build clean-pyc ## Delete all intermediate files

clean-all: clean clean-env ## Delete all intermediate files and python virtual environment

##@ Development
run: ## Run the FastAPI server
	uv run streamlit run main.py

test-unit-list: ## List all tests not marked as functional or integration
	uv run pytest -m "not functional and not integration" --collect-only
test-integration-list: ## List all integration tests
	uv run pytest -m "integration" --collect-only
test-functional-list: ## List all functional tests
	uv run pytest -m "functional" --collect-only
test-unit: ## Run tests
	uv run pytest -m "not functional and not integration"

##@ Code checks and formatting
format:: ## Format your code with isort and black
	uv run autoflake --remove-all-unused-imports --in-place --recursive .
	uv run isort .
	uv run black .

mypy:: ## Run mypy check
	uv run mypy .

lint:: ## Run all code checks
	uv run flake8 src main.py
	uv run black --check .
	uv run isort . -c

##@ Check service settings
grond-validate: ## Validate service metadata
	grond service validate-metadata service-metadata.json

##@ Variables for Jenkins
print-tag: ## Print the tag of the branch which will be used for deployments
	@echo $(TAG)

print-image: ## Print the tag of the branch which will be used for deployments
	@echo $(DOCKER_IMAGE_NAME)

print-image-location: ## Print the path of the image in artifactory
	@echo ${ARTIFACTORY_DOCKER_REGISTRY}/${ARTIFACTORY_NAMESPACE}/${DOCKER_IMAGE_NAME}

print-commit-hash: ## Print the commit hash of the branch which will be used for deployments
	@echo $(COMMIT_HASH)

docker-file-changed: ## Check if Dockerfile has been changed
	@git diff origin/main --name-only | grep -q 'Dockerfile' && echo true || echo false

##@ Documentation
docs-to-kep: ## Update API documentation in KEP portal
	KEP_PORTAL_USERNAME=$(KEP_PORTAL_USERNAME) KEP_PORTAL_PASSWORD=$(KEP_PORTAL_PASSWORD) uv run python scripts/docs_to_kep.py

##@ Build/Artifactory
# Artifactory
ARTIFACTORY_NAMESPACE = regulatory-library-tarc
ARTIFACTORY_REPO?= l-docker-regulatory-library-tarc-production
ARTIFACTORY_DOCKER_REGISTRY = $(ARTIFACTORY_REPO).artifactory.klarna.net
DOCKER_IMAGE_NAME ?= tarc-api
TAG ?= $(shell git rev-parse --short HEAD)
COMMIT_HASH ?= $(shell git rev-parse HEAD)
# These are meant to be used in Jenkins
# Naming convention is to match that of environment variables from Jenkins credentials for convenience
ARTIFACTORY_USR ?= override
ARTIFACTORY_PSW ?= override

docker-image: ## Build Docker image
	docker build -t ${ARTIFACTORY_DOCKER_REGISTRY}/${ARTIFACTORY_NAMESPACE}/${DOCKER_IMAGE_NAME}:${TAG} -t ${DOCKER_IMAGE_NAME}:${TAG} .

docker-run: docker-image ## Build and run Docker image
	docker run  --rm --env-file .env ${DOCKER_IMAGE_NAME}:${TAG}
	docker run  --rm --env-file .env ${DOCKER_IMAGE_NAME}:${TAG}