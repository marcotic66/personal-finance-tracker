from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from app.database import engine
from app import models
from app.routers import categories, transactions, budgets, summary, goals

models.Base.metadata.create_all(bind=engine)

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
