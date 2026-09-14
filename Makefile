.PHONY: check install

install:
	cd backend && python -m pip install -r requirements-dev.txt
	cd frontend && npm ci

check:
	cd backend && python -m ruff check . && python -m pytest -q
	cd frontend && npm run lint && npm run type-check && npm run build
