.PHONY: help build up down logs test lint migrate seed clean setup rebuild

# Detect OS
ifeq ($(OS),Windows_NT)
	PYTHON := python
	SETUP_CMD := python scripts/setup.py
else
	PYTHON := python3
	SETUP_CMD := ./scripts/setup.sh
endif

help:
	@echo "Available commands:"
	@echo "  make build    - Build Docker images"
	@echo "  make up       - Start all services"
	@echo "  make down     - Stop all services"
	@echo "  make logs     - Follow logs"
	@echo "  make test     - Run tests"
	@echo "  make lint     - Run linters"
	@echo "  make migrate  - Run database migrations"
	@echo "  make seed     - Seed database with test data"
	@echo "  make setup    - Init/upgrade DB then seed"
	@echo "  make clean    - Clean up Docker volumes"

build:
	docker-compose build

up:
	docker-compose up -d
	docker-compose logs -f app

down:
	docker-compose down

logs:
	docker-compose logs -f

test:
	docker-compose run --rm app pytest tests/ -v --cov=src --cov-report=html

test-integration:
	docker-compose run --rm app pytest tests/integration/ -v

lint:
	docker-compose run --rm app flake8 src/ tests/
	docker-compose run --rm app black --check src/ tests/
	docker-compose run --rm app mypy src/

migrate:
	docker-compose run --rm app flask db upgrade

seed:
	docker-compose run --rm app python scripts/seed_data.py

setup:
	@echo "Running setup..."
	$(SETUP_CMD)

rebuild:
	@echo "Rebuilding from scratch..."
	docker-compose down -v
	docker-compose build --no-cache
	docker-compose up -d
	sleep 15
	$(SETUP_CMD)

clean:
	docker-compose down -v
	docker system prune -f

shell:
	docker-compose exec app flask shell

db-shell:
	docker-compose exec postgres psql -U sentinel -d sentinel

redis-cli:
	docker-compose exec redis redis-cli
