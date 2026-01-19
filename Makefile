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
	python policylens/manage.py migrate

run:
	python policylens/manage.py runserver 0.0.0.0:8000
