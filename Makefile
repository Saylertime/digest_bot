.PHONY: up down

CURRENT_HOSTNAME := $(shell hostname)

ifeq ($(CURRENT_HOSTNAME), 1738991-cy22118.twc1.net)
    COMPOSE_FILE = docker-compose_prod.yml
else
    COMPOSE_FILE = docker-compose_local.yml
endif

up:
	docker compose -f $(COMPOSE_FILE) up

build:
	docker compose -f $(COMPOSE_FILE) up --build

down:
	docker compose -f $(COMPOSE_FILE) down

bash:
	docker exec -it bot_digest bash

pg_bash:
	docker exec -it postgres_digest /bin/sh -c "psql -h postgres -U sayler -d postgres"

logs_report:
	docker logs postgres_digest

debug:
	@echo "Current Hostname: $(CURRENT_HOSTNAME)"
	@echo "Using Compose File: $(COMPOSE_FILE)"
