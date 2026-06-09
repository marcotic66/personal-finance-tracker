from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from sqlalchemy import text

from app.database import engine
from app import models
from app.routers import categories, transactions, budgets, summary, goals

models.Base.metadata.create_all(bind=engine)

# Add category_id column to savings_goals if it doesn't exist yet (one-time migration)
with engine.connect() as _conn:
    try:
        _conn.execute(text(
            "ALTER TABLE savings_goals ADD COLUMN category_id INTEGER REFERENCES categories(id)"
        ))
        _conn.commit()
    except Exception:
        pass

app = FastAPI(title="Personal Finance Tracker", version="1.0.0")

app.include_router(categories.router, prefix="/api")
app.include_router(transactions.router, prefix="/api")
app.include_router(budgets.router, prefix="/api")
app.include_router(summary.router, prefix="/api")
app.include_router(goals.router, prefix="/api")

app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/", include_in_schema=False)
def serve_index():
    return FileResponse("static/index.html")
