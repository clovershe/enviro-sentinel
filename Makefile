.PHONY: install run simulate lint format test docker-up docker-down

install:
	python3 -m pip install -e ".[dev]"

run:
	uvicorn iot_platform.main:app --reload --port 8000

simulate:
	iot-simulator --transport http --scenario normal

lint:
	ruff check .
	ruff format --check .

format:
	ruff check --fix .
	ruff format .

test:
	pytest --cov=iot_platform --cov-report=term-missing --cov-fail-under=65

docker-up:
	docker compose up --build

docker-down:
	docker compose down
