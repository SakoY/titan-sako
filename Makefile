.PHONY: run build lint format test

run:
	docker compose up --build

build:
	docker compose build

lint:
	ruff check app/ tests/

format:
	black app/ tests/

test:
	pytest tests/ -v
