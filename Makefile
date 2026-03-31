ruff:
	ruff format app tests main.py

isort:
	ruff check --select I --fix app tests main.py

lint:
	ruff check --fix app tests main.py

format:
	$(MAKE) isort
	$(MAKE) ruff

test:
	docker compose exec web pytest

