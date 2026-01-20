# path: Makefile
.PHONY: format lint test migrate run

format:
	python -m black .
	python -m ruff check . --fix

lint:
	python -m black . --check
	python -m ruff check .

test:
	pytest -q

migrate:
	python manage.py migrate

run:
	python manage.py runserver 0.0.0.0:8000
