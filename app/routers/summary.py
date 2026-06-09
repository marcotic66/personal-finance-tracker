from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, extract
from sqlalchemy.orm import Session

from app.database import get_db
from app import models, schemas

router = APIRouter(prefix="/summary", tags=["summary"])


@router.get("/", response_model=schemas.MonthlySummary)
def get_summary(
    month: int = Query(..., ge=1, le=12),
    year: int = Query(..., ge=2000),
    db: Session = Depends(get_db),
):
    transactions = (
        db.query(models.Transaction)
        .filter(
            extract("month", models.Transaction.date) == month,
            extract("year", models.Transaction.date) == year,
        )
        .all()
    )

    budgets = (
        db.query(models.Budget)
        .filter(models.Budget.month == month, models.Budget.year == year)
        .all()
    )
    budget_map = {b.category_id: b for b in budgets}

    totals: dict[int, float] = {}
    for t in transactions:
        totals[t.category_id] = totals.get(t.category_id, 0.0) + t.amount

    categories = db.query(models.Category).all()
    cat_map = {c.id: c for c in categories}

    by_category = []
    seen_categories = set(totals.keys()) | set(budget_map.keys())
    for cat_id in seen_categories:
        cat = cat_map.get(cat_id)
        if not cat:
            continue
        budget = budget_map.get(cat_id)
        by_category.append(
            schemas.CategorySummary(
                category_id=cat_id,
                category_name=cat.name,
                category_color=cat.color,
                category_icon=cat.icon,
                type=cat.type,
                total=totals.get(cat_id, 0.0),
                budget=budget.amount if budget else None,
                budget_id=budget.id if budget else None,
            )
        )

    by_category.sort(key=lambda x: x.total, reverse=True)

    total_income = sum(t.amount for t in transactions if t.type == models.TransactionType.income)
    total_expenses = sum(t.amount for t in transactions if t.type == models.TransactionType.expense)

    return schemas.MonthlySummary(
        month=month,
        year=year,
        total_income=total_income,
        total_expenses=total_expenses,
        net=total_income - total_expenses,
        by_category=by_category,
    )
