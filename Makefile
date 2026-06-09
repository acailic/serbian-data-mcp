.PHONY: help install test check lint format type-check security clean dev

help: ## Show this help message
	@echo "Available commands:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

install: ## Install dependencies
	uv sync --dev

test: ## Run tests with coverage
	uv run pytest --cov=src --cov-report=html --cov-report=term-missing -v

test-quick: ## Run tests without coverage
	uv run pytest -v

test-unit: ## Run only unit tests
	uv run pytest tests/test_*.py -v

test-integration: ## Run only integration tests
	uv run pytest tests/test_integration.py -v

lint: ## Run linting checks
	@echo "Running ruff linting..."
	@uv run ruff check src/ tests/

format: ## Format code with ruff
	@echo "Formatting code..."
	@uv run ruff format src/ tests/

format-check: ## Check code formatting
	@echo "Checking code formatting..."
	@uv run ruff format --check src/ tests/

type-check: ## Run type checking with pyright
	@echo "Running type checks..."
	@uv run pyright src/

security: ## Run security checks with bandit
	@echo "Running security checks..."
	@uv run bandit -r src/

check: lint format-check type-check security ## Run all quality checks
	@echo "✅ All quality checks passed!"

check-quick: lint format-check ## Run quick checks (no type checking)
	@echo "✅ Quick checks passed!"

clean: ## Clean up generated files
	rm -rf .venv
	rm -rf .pytest_cache
	rm -rf .ruff_cache
	rm -rf htmlcov
	rm -rf .coverage
	rm -rf coverage.xml
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

dev: ## Install dependencies and set up development environment
	uv sync --dev
	@echo "✅ Development environment ready!"
	@echo "Run 'make test' to run tests"
	@echo "Run 'make check' to run quality checks"

all: install test check ## Install dependencies, run tests, and check quality
	@echo "✅ All checks completed successfully!"
