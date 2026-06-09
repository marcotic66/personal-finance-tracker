from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app import models, schemas

router = APIRouter(prefix="/budgets", tags=["budgets"])


@router.get("/", response_model=list[schemas.BudgetOut])
def list_budgets(
    month: Optional[int] = Query(None, ge=1, le=12),
    year: Optional[int] = Query(None, ge=2000),
    db: Session = Depends(get_db),
):
    q = db.query(models.Budget)
    if month is not None:
        q = q.filter(models.Budget.month == month)
    if year is not None:
        q = q.filter(models.Budget.year == year)
    return q.order_by(models.Budget.year.desc(), models.Budget.month.desc()).all()


@router.post("/", response_model=schemas.BudgetOut, status_code=201)
def create_budget(payload: schemas.BudgetCreate, db: Session = Depends(get_db)):
    category = db.query(models.Category).filter(models.Category.id == payload.category_id).first()
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    existing = (
        db.query(models.Budget)
        .filter(
            models.Budget.category_id == payload.category_id,
            models.Budget.month == payload.month,
            models.Budget.year == payload.year,
        )
        .first()
    )
    if existing:
        raise HTTPException(status_code=409, detail="Budget already exists for this category and period")
    budget = models.Budget(**payload.model_dump())
    db.add(budget)
    db.commit()
    db.refresh(budget)
    return budget


@router.get("/{budget_id}", response_model=schemas.BudgetOut)
def get_budget(budget_id: int, db: Session = Depends(get_db)):
    budget = db.query(models.Budget).filter(models.Budget.id == budget_id).first()
    if not budget:
        raise HTTPException(status_code=404, detail="Budget not found")
    return budget


@router.put("/{budget_id}", response_model=schemas.BudgetOut)
def update_budget(budget_id: int, payload: schemas.BudgetUpdate, db: Session = Depends(get_db)):
    budget = db.query(models.Budget).filter(models.Budget.id == budget_id).first()
    if not budget:
        raise HTTPException(status_code=404, detail="Budget not found")
    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(budget, field, value)
    db.commit()
    db.refresh(budget)
    return budget


@router.delete("/{budget_id}", status_code=204)
def delete_budget(budget_id: int, db: Session = Depends(get_db)):
    budget = db.query(models.Budget).filter(models.Budget.id == budget_id).first()
    if not budget:
        raise HTTPException(status_code=404, detail="Budget not found")
    db.delete(budget)
    db.commit()
