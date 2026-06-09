# Architecture

## Stack

| Layer | Technology |
|---|---|
| Language | Python 3.11 |
| Package manager | uv |
| Web framework | FastAPI |
| ORM | SQLAlchemy 2 |
| Database | SQLite (`data/finance.db`) |
| Frontend | Vanilla JS + Chart.js 4 |
| Server | Uvicorn (ASGI) |

FastAPI serves both the REST API (under `/api`) and the static frontend files. The frontend is a single HTML page that talks exclusively to the API — there is no server-side rendering.

## Directory Structure

```
personal-finance-tracker/
├── main.py                  # App entry point: mounts routers + static files
├── seed_data.py             # Populates dev/demo data (clears first)
├── pyproject.toml           # uv project config + dependencies
├── app/
│   ├── database.py          # Engine, SessionLocal, get_db dependency
│   ├── models.py            # SQLAlchemy ORM models
│   ├── schemas.py           # Pydantic request/response schemas
│   └── routers/
│       ├── categories.py    # CRUD  /api/categories
│       ├── transactions.py  # CRUD  /api/transactions
│       ├── budgets.py       # CRUD  /api/budgets
│       └── summary.py       # Read  /api/summary
├── static/
│   ├── index.html           # App shell (single page)
│   ├── css/style.css        # Dark-theme CSS variables + layout
│   └── js/app.js            # All frontend logic (~750 lines)
├── docs/                    # Project documentation
└── data/
    └── finance.db           # SQLite database (gitignored)
```

## Data Model

```
categories
  id          INTEGER  PK
  name        TEXT     UNIQUE NOT NULL
  type        ENUM     income | expense
  color       TEXT     hex color, default #6366f1
  icon        TEXT     emoji, default 💰
  created_at  DATETIME

transactions
  id           INTEGER  PK
  amount       REAL     > 0
  description  TEXT     NOT NULL
  date         DATE     NOT NULL
  type         ENUM     income | expense
  category_id  INTEGER  FK → categories.id
  created_at   DATETIME

budgets
  id           INTEGER  PK
  category_id  INTEGER  FK → categories.id
  amount       REAL     > 0
  month        INTEGER  1–12
  year         INTEGER
  created_at   DATETIME
  UNIQUE (category_id, month, year)
```

## API

All endpoints are prefixed `/api`. Full interactive docs at `/docs`.

### Categories — `/api/categories`
| Method | Path | Description |
|---|---|---|
| GET | `/` | List all categories (alphabetical) |
| POST | `/` | Create category |
| GET | `/{id}` | Get category |
| PUT | `/{id}` | Update category (partial) |
| DELETE | `/{id}` | Delete — 409 if transactions exist |

### Transactions — `/api/transactions`
| Method | Path | Description |
|---|---|---|
| GET | `/` | List transactions; filter by `month`, `year`, `category_id`, `type` |
| POST | `/` | Create transaction; enforces category type match |
| GET | `/{id}` | Get transaction |
| PUT | `/{id}` | Update transaction (partial) |
| DELETE | `/{id}` | Delete transaction |

### Budgets — `/api/budgets`
| Method | Path | Description |
|---|---|---|
| GET | `/` | List budgets; filter by `month`, `year` |
| POST | `/` | Create budget — 409 if period+category already exists |
| GET | `/{id}` | Get budget |
| PUT | `/{id}` | Update budget amount/period |
| DELETE | `/{id}` | Delete budget |

### Summary — `/api/summary`
| Method | Path | Description |
|---|---|---|
| GET | `/?month=&year=` | Aggregated monthly summary |

**Summary response shape:**
```json
{
  "month": 6,
  "year": 2026,
  "total_income": 5992.97,
  "total_expenses": 3373.07,
  "net": 2619.90,
  "by_category": [
    {
      "category_id": 1,
      "category_name": "Housing",
      "category_color": "#ef4444",
      "category_icon": "🏠",
      "type": "expense",
      "total": 1450.00,
      "budget": 1500.00,
      "budget_id": 23
    }
  ]
}
```

The summary endpoint loads all transactions and budgets for the period in two queries, aggregates in Python, and returns a union of categories that have either transactions or budgets in that month.

## Request / Response Flow

```
Browser  →  GET /api/summary?month=6&year=2026
             ↓
         FastAPI router (summary.py)
             ↓
         SQLAlchemy queries (2 SELECTs)
             ↓
         Pydantic serialization (MonthlySummary)
             ↓
         JSON response
```

Validation happens at two layers: Pydantic rejects malformed input before the handler runs, and the handler enforces business rules (e.g. category type mismatch, duplicate budget) with explicit 409/422 responses.

## Key Constraints

- `check_same_thread=False` is set on the SQLite engine because FastAPI uses a thread pool for sync route handlers; each request gets its own `SessionLocal` via `get_db`.
- The database file is gitignored. Run `seed_data.py` to populate a fresh database.
- `models.Base.metadata.create_all` runs on startup (`main.py`), so tables are created automatically on first run.
