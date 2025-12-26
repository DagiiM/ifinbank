# ===============================================================================
# iFin Bank Verification System - Makefile
# ===============================================================================

.PHONY: help install dev run test lint clean docker-build docker-up docker-down docker-logs

PROVISIONING_DIR = provisioning

# Default target
help:
	@echo "iFin Bank Verification System - Available Commands"
	@echo ""
	@echo "ONE-STEP DEPLOYMENT:"
	@echo "  make deploy-dev   - Deploy development environment"
	@echo "  make deploy-prod  - Deploy production environment"
	@echo ""
	@echo "Development:"
	@echo "  make install     - Install dependencies"
	@echo "  make dev         - Start development server"
	@echo "  make run         - Alias for dev"
	@echo "  make test        - Run tests"
	@echo "  make lint        - Run linting"
	@echo "  make migrate     - Run database migrations"
	@echo "  make shell       - Open Django shell"
	@echo ""
	@echo "Docker:"
	@echo "  make docker-dev  - Start dev containers"
	@echo "  make docker-prod - Start production stack"
	@echo "  make docker-down - Stop containers"
	@echo "  make docker-logs - View container logs"
	@echo ""
	@echo "Maintenance:"
	@echo "  make seed        - Seed initial data"
	@echo "  make clean       - Clean temporary files"
	@echo "  make backup      - Backup database"

# ===============================================================================
# ONE-STEP DEPLOYMENT
# ===============================================================================

deploy-dev:
	@./deploy.sh dev

deploy-prod:
	@./deploy.sh prod

deploy-prod-no-gpu:
	@./deploy.sh prod --no-gpu


# ===============================================================================
# Development
# ===============================================================================

install:
	pip install -r requirements.txt

install-prod:
	pip install -r requirements.txt -r $(PROVISIONING_DIR)/requirements-prod.txt

dev:
	python manage.py runserver

run: dev

migrate:
	python manage.py makemigrations
	python manage.py migrate

shell:
	python manage.py shell

createsuperuser:
	python manage.py createsuperuser

test:
	python manage.py test

test-verbose:
	python manage.py test -v 2

test-coverage:
	coverage run manage.py test
	coverage report
	coverage html

lint:
	flake8 apps/
	isort --check-only apps/
	black --check apps/

format:
	isort apps/
	black apps/

seed:
	python manage.py seed_policies
	python manage.py sync_policies

# ===============================================================================
# Docker Development
# ===============================================================================

docker-dev:
	cd $(PROVISIONING_DIR) && docker-compose -f docker-compose.dev.yml up -d

docker-dev-build:
	cd $(PROVISIONING_DIR) && docker-compose -f docker-compose.dev.yml up -d --build

docker-dev-logs:
	cd $(PROVISIONING_DIR) && docker-compose -f docker-compose.dev.yml logs -f

docker-down:
	cd $(PROVISIONING_DIR) && docker-compose -f docker-compose.dev.yml down

# ===============================================================================
# Docker Production
# ===============================================================================

docker-build:
	cd $(PROVISIONING_DIR) && docker-compose build

docker-up:
	cd $(PROVISIONING_DIR) && docker-compose up -d

docker-prod: docker-build docker-up
	@echo "Production stack started"
	@echo "Run 'make docker-init' to initialize the database"

docker-init:
	cd $(PROVISIONING_DIR) && docker-compose exec web python manage.py migrate
	cd $(PROVISIONING_DIR) && docker-compose exec web python manage.py seed_policies
	cd $(PROVISIONING_DIR) && docker-compose exec web python manage.py sync_policies

docker-logs:
	cd $(PROVISIONING_DIR) && docker-compose logs -f

docker-stop:
	cd $(PROVISIONING_DIR) && docker-compose stop

docker-restart:
	cd $(PROVISIONING_DIR) && docker-compose restart

docker-status:
	cd $(PROVISIONING_DIR) && docker-compose ps

docker-shell:
	cd $(PROVISIONING_DIR) && docker-compose exec web python manage.py shell

docker-bash:
	cd $(PROVISIONING_DIR) && docker-compose exec web /bin/sh

# ===============================================================================
# Maintenance
# ===============================================================================

clean:
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type f -name "*.log" -delete
	rm -rf .pytest_cache
	rm -rf htmlcov
	rm -rf .coverage

backup:
	cd $(PROVISIONING_DIR) && ./scripts/backup.sh

collectstatic:
	python manage.py collectstatic --no-input

# ===============================================================================
# Provisioning Scripts
# ===============================================================================

deploy:
	cd $(PROVISIONING_DIR) && ./scripts/deploy.sh

ssl-dev:
	cd $(PROVISIONING_DIR) && ./scripts/ssl-generate.sh
