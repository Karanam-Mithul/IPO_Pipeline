.PHONY: up down restart logs ps seed test clean

## ── Docker ───────────────────────────────────────────────────────────────────
up:
	cp -n .env.example .env || true
	docker compose up -d --build
	@echo "✅  Stack is up."
	@echo "   Airflow  → http://localhost:8080  (admin / admin)"
	@echo "   Dashboard→ http://localhost:8501"

down:
	docker compose down

restart:
	docker compose restart

logs:
	docker compose logs -f

ps:
	docker compose ps

## ── Database ─────────────────────────────────────────────────────────────────
seed:
	@echo "Seeding sample IPO data..."
	docker compose exec postgres psql -U ipo_user -d ipo_db -c "\dt" > /dev/null 2>&1 || \
		(echo "DB not ready yet. Wait a moment and retry." && exit 1)
	docker compose run --rm dashboard python /app/../database/seed_data.py || \
		python database/seed_data.py
	@echo "✅  Sample data loaded."

## ── Tests ────────────────────────────────────────────────────────────────────
test:
	pytest tests/ -v

## ── Cleanup ──────────────────────────────────────────────────────────────────
clean:
	docker compose down -v --remove-orphans
	find . -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pkl"       -delete 2>/dev/null || true
	@echo "✅  Clean done."
