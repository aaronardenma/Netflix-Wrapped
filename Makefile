SHELL := /bin/bash

BACKEND_DIR := backend
FRONTEND_DIR := frontend
PYTHON := ./.venv/bin/python
PIP := ./.venv/bin/pip
MANAGE := $(PYTHON) manage.py
RQ_QUEUE := recaps
BACKEND_URL := http://localhost:8000

.PHONY: help setup setup-dev redis-start redis-stop redis-restart redis-status \
	migrate migrations server server-json worker frontend backend backend-dev \
	backend-json dev dev-json health test check shell

help:
	@printf '%s\n' \
		'Netflix Wrapped backend commands' \
		'' \
		'  make setup          Install backend Python dependencies' \
		'  make setup-dev      Install backend runtime + notebook/dev dependencies' \
		'  make redis-start    Start Redis as a Homebrew service' \
		'  make redis-stop     Stop the Redis service' \
		'  make redis-restart  Restart the Redis service' \
		'  make redis-status   Check Redis connectivity' \
		'  make migrate        Apply Django migrations' \
		'  make migrations     Generate Django migrations' \
		'  make server         Start the Django development server' \
		'  make server-json    Start Django with JSON request logs' \
		'  make worker         Start the RQ recap worker' \
		'  make frontend       Start the Vite development server' \
		'  make backend        Start Redis, RQ, and Django together' \
		'  make backend-json   Start Redis, RQ, and Django with JSON logs' \
		'  make dev            Start Redis, RQ, Django, and Vite together' \
		'  make dev-json       Start the full dev stack with JSON backend logs' \
		'  make health         Check backend database/cache/RQ health' \
		'  make test           Run backend tests' \
		'  make check          Run Django system checks' \
		'  make shell          Open the Django shell'

setup:
	@cd "$(BACKEND_DIR)" && $(PIP) install -r requirements.txt

setup-dev:
	@cd "$(BACKEND_DIR)" && $(PIP) install -r requirements-dev.txt

redis-start:
	@command -v redis-server >/dev/null || { \
		echo "Redis is not installed. Run: brew install redis"; \
		exit 1; \
	}
	@brew services start redis

redis-stop:
	@brew services stop redis

redis-restart:
	@brew services restart redis

redis-status:
	@redis-cli ping

migrate:
	@cd "$(BACKEND_DIR)" && $(MANAGE) migrate

migrations:
	@cd "$(BACKEND_DIR)" && $(MANAGE) makemigrations

server:
	@cd "$(BACKEND_DIR)" && $(MANAGE) runserver

server-json:
	@cd "$(BACKEND_DIR)" && LOG_FORMAT=json $(MANAGE) runserver

worker:
	@cd "$(BACKEND_DIR)" && $(MANAGE) rqworker $(RQ_QUEUE)

frontend:
	@cd "$(FRONTEND_DIR)" && npm run dev

backend: backend-dev

backend-json: redis-start
	@echo "Starting RQ worker and Django server with JSON logs..."
	@cd "$(BACKEND_DIR)" && { \
		$(MANAGE) rqworker $(RQ_QUEUE) & \
		worker_pid=$$!; \
		trap 'kill $$worker_pid 2>/dev/null || true' EXIT INT TERM; \
		LOG_FORMAT=json $(MANAGE) runserver; \
	}

backend-dev: redis-start
	@echo "Starting RQ worker and Django server..."
	@cd "$(BACKEND_DIR)" && { \
		$(MANAGE) rqworker $(RQ_QUEUE) & \
		worker_pid=$$!; \
		trap 'kill $$worker_pid 2>/dev/null || true' EXIT INT TERM; \
		$(MANAGE) runserver; \
	}

dev: redis-start
	@echo "Starting RQ worker, Django server, and Vite..."
	@{ \
		cd "$(BACKEND_DIR)" && $(MANAGE) rqworker $(RQ_QUEUE) & \
		worker_pid=$$!; \
		cd "$(BACKEND_DIR)" && $(MANAGE) runserver & \
		server_pid=$$!; \
		cd "$(FRONTEND_DIR)" && npm run dev & \
		frontend_pid=$$!; \
		trap 'kill $$worker_pid $$server_pid $$frontend_pid 2>/dev/null || true' EXIT INT TERM; \
		wait $$worker_pid $$server_pid $$frontend_pid; \
	}

dev-json: redis-start
	@echo "Starting RQ worker, Django server with JSON logs, and Vite..."
	@{ \
		cd "$(BACKEND_DIR)" && $(MANAGE) rqworker $(RQ_QUEUE) & \
		worker_pid=$$!; \
		cd "$(BACKEND_DIR)" && LOG_FORMAT=json $(MANAGE) runserver & \
		server_pid=$$!; \
		cd "$(FRONTEND_DIR)" && npm run dev & \
		frontend_pid=$$!; \
		trap 'kill $$worker_pid $$server_pid $$frontend_pid 2>/dev/null || true' EXIT INT TERM; \
		wait $$worker_pid $$server_pid $$frontend_pid; \
	}

health:
	@curl -sS "$(BACKEND_URL)/api/observability/health/"
	@printf '\n'

test:
	@cd "$(BACKEND_DIR)" && $(MANAGE) test api

check:
	@cd "$(BACKEND_DIR)" && $(MANAGE) check

shell:
	@cd "$(BACKEND_DIR)" && $(MANAGE) shell
