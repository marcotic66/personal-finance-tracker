from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app import models, schemas

router = APIRouter(prefix="/transactions", tags=["transactions"])


@router.get("/", response_model=list[schemas.TransactionOut])
def list_transactions(
    month: Optional[int] = Query(None, ge=1, le=12),
    year: Optional[int] = Query(None, ge=2000),
    category_id: Optional[int] = None,
    type: Optional[models.TransactionType] = None,
    db: Session = Depends(get_db),
):
    q = db.query(models.Transaction)
    if month is not None:
        from sqlalchemy import extract
        q = q.filter(extract("month", models.Transaction.date) == month)
    if year is not None:
        from sqlalchemy import extract
        q = q.filter(extract("year", models.Transaction.date) == year)
    if category_id is not None:
        q = q.filter(models.Transaction.category_id == category_id)
    if type is not None:
        q = q.filter(models.Transaction.type == type)
    return q.order_by(models.Transaction.date.desc()).all()


@router.post("/", response_model=schemas.TransactionOut, status_code=201)
def create_transaction(payload: schemas.TransactionCreate, db: Session = Depends(get_db)):
    category = db.query(models.Category).filter(models.Category.id == payload.category_id).first()
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    if category.type != payload.type:
        raise HTTPException(
            status_code=422,
            detail=f"Category '{category.name}' is for {category.type.value}, not {payload.type.value}",
        )
    transaction = models.Transaction(**payload.model_dump())
    db.add(transaction)
    db.commit()
    db.refresh(transaction)
    return transaction


@router.get("/{transaction_id}", response_model=schemas.TransactionOut)
def get_transaction(transaction_id: int, db: Session = Depends(get_db)):
    t = db.query(models.Transaction).filter(models.Transaction.id == transaction_id).first()
    if not t:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return t


@router.put("/{transaction_id}", response_model=schemas.TransactionOut)
def update_transaction(transaction_id: int, payload: schemas.TransactionUpdate, db: Session = Depends(get_db)):
    t = db.query(models.Transaction).filter(models.Transaction.id == transaction_id).first()
    if not t:
        raise HTTPException(status_code=404, detail="Transaction not found")
    updates = payload.model_dump(exclude_none=True)
    if "category_id" in updates:
        category = db.query(models.Category).filter(models.Category.id == updates["category_id"]).first()
        if not category:
            raise HTTPException(status_code=404, detail="Category not found")
    for field, value in updates.items():
        setattr(t, field, value)
    db.commit()
    db.refresh(t)
    return t


@router.delete("/{transaction_id}", status_code=204)
def delete_transaction(transaction_id: int, db: Session = Depends(get_db)):
    t = db.query(models.Transaction).filter(models.Transaction.id == transaction_id).first()
    if not t:
        raise HTTPException(status_code=404, detail="Transaction not found")
    db.delete(t)
    db.commit()
