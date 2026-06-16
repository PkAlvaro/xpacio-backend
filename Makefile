.PHONY: help dev dev-down test test-cov lint fmt migrate seed logs deploy deploy-full backup shell-api shell-db

COMPOSE_DEV  = docker compose
COMPOSE_PROD = docker compose -f docker-compose.prod.yml --env-file .env.prod
SSH          = ssh -i ~/.ssh/id_xpacio deploy@165.227.181.241
REMOTE_DIR   = /home/deploy/xpacio/xpacio-backend

help:
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-18s\033[0m %s\n", $$1, $$2}'

# ── Local dev ─────────────────────────────────────────────────────────────────

dev: ## Start all services locally (detached)
	$(COMPOSE_DEV) up -d --build

dev-down: ## Stop and remove local containers
	$(COMPOSE_DEV) down

dev-logs: ## Tail local logs (all services)
	$(COMPOSE_DEV) logs -f

# ── Tests ─────────────────────────────────────────────────────────────────────

test: ## Run test suite
	pytest tests/ -v

test-cov: ## Run tests with coverage report
	pytest tests/ -v --cov=app --cov-report=term-missing --cov-report=html

test-unit: ## Run only unit tests
	pytest tests/unit/ -v

test-integration: ## Run only integration tests
	pytest tests/integration/ -v

# ── Code quality ──────────────────────────────────────────────────────────────

lint: ## Run ruff linter
	ruff check app/ tests/

fmt: ## Auto-fix and format with ruff
	ruff check app/ tests/ --fix
	ruff format app/ tests/

# ── Database ──────────────────────────────────────────────────────────────────

migrate: ## Apply pending Alembic migrations (local)
	$(COMPOSE_DEV) exec api alembic upgrade head

migrate-new: ## Create a new migration (MSG=description required)
	$(COMPOSE_DEV) exec api alembic revision --autogenerate -m "$(MSG)"

seed: ## Run seed scripts (local)
	$(COMPOSE_DEV) exec api python -m app.seed
	$(COMPOSE_DEV) exec api python -m app.seed venues

# ── Shells ────────────────────────────────────────────────────────────────────

shell-api: ## Open shell in local API container
	$(COMPOSE_DEV) exec api bash

shell-db: ## Open psql in local DB container
	$(COMPOSE_DEV) exec db psql -U xpacio -d xpacio

# ── Production ────────────────────────────────────────────────────────────────

deploy: ## Deploy to production (incremental build)
	$(SSH) "cd $(REMOTE_DIR) && bash deploy.sh"

deploy-full: ## Deploy with full no-cache rebuild (use after dep changes)
	$(SSH) "cd $(REMOTE_DIR) && bash deploy.sh --full"

logs: ## Tail production API logs
	$(SSH) "cd $(REMOTE_DIR) && $(COMPOSE_PROD) logs api worker -f --tail=100"

ps: ## Show production container status
	$(SSH) "cd $(REMOTE_DIR) && $(COMPOSE_PROD) ps"

backup: ## Run DB backup on production
	$(SSH) "cd $(REMOTE_DIR) && bash scripts/backup.sh .env.prod"

setup-cron: ## Install cron jobs on production droplet (run once)
	$(SSH) "cd $(REMOTE_DIR) && bash scripts/setup_cron.sh"

migrate-prod: ## Apply migrations on production
	$(SSH) "cd $(REMOTE_DIR) && $(COMPOSE_PROD) exec -T api alembic upgrade head"

shell-prod-api: ## Open shell in production API container
	$(SSH) -t "cd $(REMOTE_DIR) && $(COMPOSE_PROD) exec api bash"

shell-prod-db: ## Open psql in production DB container
	$(SSH) -t "cd $(REMOTE_DIR) && $(COMPOSE_PROD) exec db psql -U \$$POSTGRES_USER -d \$$POSTGRES_DB"
