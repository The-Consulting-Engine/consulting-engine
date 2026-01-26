.PHONY: up down restart reset-db logs

up:
	docker compose up --build -d

down:
	docker compose down

restart: down up

reset-db:
	@echo "DESTRUCTIVE: Dropping DB volume and rebuilding. All data will be lost."
	docker compose down -v && docker compose up --build -d

logs:
	docker compose logs -f
