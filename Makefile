.PHONY: help install test lint format type-check security clean run dev-setup
.DEFAULT_GOAL := help

help: ## Show this help message
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Targets:'
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  %-15s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

install: ## Install dependencies
	pip install -r requirements.txt

dev-setup: install ## Setup development environment
	pre-commit install
	@echo "Development environment setup complete!"

test: ## Run tests
	pytest -v --cov=. --cov-report=html --cov-report=term-missing

test-watch: ## Run tests in watch mode
	pytest -f --tb=short

lint: ## Run linting
	flake8 .
	pylint **/*.py

format: ## Format code
	black .
	isort .

format-check: ## Check code formatting
	black --check .
	isort --check-only .

type-check: ## Run type checking
	mypy .

security: ## Run security checks
	bandit -r . -c pyproject.toml

pre-commit: ## Run all pre-commit hooks
	pre-commit run --all-files

clean: ## Clean up temporary files
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	rm -rf .coverage htmlcov/ .pytest_cache/ .mypy_cache/

run: ## Run the trading bot
	python main.py

run-tests-only: ## Run only the essential tests (no coverage)
	pytest tests/ -v --tb=short

check-all: format-check lint type-check security test ## Run all checks

build: ## Prepare for deployment
	@echo "Running all checks before build..."
	make check-all
	@echo "Build checks passed!"

docker-build: ## Build Docker image
	docker build -t trading-bot .

docker-run: ## Run Docker container
	docker run --env-file .env trading-bot

metrics: ## Show current metrics (if bot is running)
	@python -c "
try:
    from monitoring.metrics import get_metrics
    import json
    metrics = get_metrics()
    data = metrics.get_dashboard_data()
    print(json.dumps(data, indent=2))
except Exception as e:
    print(f'Error: {e}')
    print('Make sure the bot is running or metrics are available')
"

health: ## Show health status
	@python -c "
try:
    from monitoring.metrics import get_metrics
    import json
    metrics = get_metrics()
    health = metrics.collector.get_health_status()
    print(json.dumps(health, indent=2))
except Exception as e:
    print(f'Error: {e}')
"