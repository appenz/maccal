.PHONY: install test lint format build clean benchmark

install:
	uv sync --dev

test:
	uv run pytest -v

lint:
	uv run ruff check src/ tests/

format:
	uv run ruff format src/ tests/

build:
	uv build

clean:
	rm -rf dist/ build/ *.egg-info .pytest_cache
	find . -type d -name __pycache__ -exec rm -rf {} +

benchmark:
	uv run python -m benchmarks.bench_query
