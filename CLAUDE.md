# Personal Finance Tracker

## Documentation

- [Requirements](docs/requirements.md) — features, functional and non-functional requirements, out of scope
- [Architecture](docs/architecture.md) — stack, directory structure, data model, full API reference
- [Design](docs/design.md) — UI layout, state management, page breakdown, modal and chart patterns

## Quick Start

```bash
# Install dependencies
uv sync

# Start the dev server
uv run uvicorn main:app --reload
# → http://localhost:8000
# → http://localhost:8000/docs  (interactive API docs)

# Seed sample data (clears existing data first)
uv run python seed_data.py
```

## Project Layout

```
app/
  database.py        SQLAlchemy engine + get_db dependency
  models.py          ORM models: Category, Transaction, Budget
  schemas.py         Pydantic schemas for all request/response types
  routers/
    categories.py    CRUD /api/categories
    transactions.py  CRUD /api/transactions
    budgets.py       CRUD /api/budgets
    summary.py       GET  /api/summary
static/
  index.html         Single-page app shell
  css/style.css      Dark theme, CSS variables
  js/app.js          All frontend logic (no framework)
docs/                Project documentation
data/                SQLite database (gitignored)
main.py              FastAPI app entry point
seed_data.py         Dev/demo data population script
```

## Key Conventions

- **Database** is auto-created on first startup (`create_all` in `main.py`). Never edit `data/finance.db` by hand.
- **Routers** validate business rules explicitly — category type must match transaction type; budgets are unique per category+month+year.
- **Schemas** use `exclude_none=True` on updates so partial PUTs only modify provided fields.
- **Frontend state** is a single `state` object in `app.js`. All four data collections are reloaded in parallel via `loadAll()` on every month navigation.
- **Chart instances** (`donutChart`, `barChart`) are destroyed before re-render to avoid Chart.js canvas reuse errors.
- The `data/` directory is gitignored. Run `seed_data.py` after cloning to get a working dataset.
