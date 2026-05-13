.PHONY: help install test lint type-check clean docker-build docker-run ci

help:
	@echo "ZenAgent Development Commands"
	@echo "============================="
	@echo "make install        - Install dependencies"
	@echo "make test           - Run all tests"
	@echo "make test-unit      - Run unit tests"
	@echo "make test-e2e       - Run end-to-end tests"
	@echo "make lint           - Run linters"
	@echo "make type-check     - Run type checker"
	@echo "make format         - Format code"
	@echo "make clean          - Clean cache files"
	@echo "make docker-build   - Build Docker image"
	@echo "make docker-run     - Run Docker container"
	@echo "make ci             - Run full CI locally"

install:
	pip install -e .[dev]
	pre-commit install

test:
	pytest tests/ -v --cov=packages

test-unit:
	pytest tests/unit/ -v

test-e2e:
	pytest tests/e2e/ -v

test-benchmark:
	pytest tests/ -k benchmark --benchmark-only

lint:
	ruff check .
	ruff format --check .

format:
	ruff check --fix .
	ruff format .

	type-check: mypy
	mypy packages/ --ignore-missing-imports

clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	rm -rf .pytest_cache .mypy_cache .ruff_cache
	rm -rf htmlcov/ .coverage coverage.xml
	rm -rf dist/ build/ *.egg

docker-build:
	docker build -t zenagent/zenagent:latest .

docker-run:
	docker run -p 8000:8000 --rm zenagent/zenagent:latest

docker-run-dev:
	docker-compose up -d

ci: lint type-check test

# Git hooks
hooks:
	pre-commit install

# Development server
dev:
	uvicorn zenagent:app --reload --host 0.0.0.0 --port 8000

# Redis for local development
redis:
	redis-server --daemonize yes

.DEFAULT_GOAL := help
