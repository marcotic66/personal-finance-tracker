import csv
import io
from datetime import date
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import extract
from sqlalchemy.orm import Session

from app.database import get_db
from app import models, schemas

router = APIRouter(prefix="/transactions", tags=["transactions"])


def _build_query(
    db: Session,
    month: Optional[int],
    year: Optional[int],
    start_date: Optional[date],
    end_date: Optional[date],
    category_id: Optional[int],
    type: Optional[models.TransactionType],
):
    q = db.query(models.Transaction)
    if start_date is not None:
        q = q.filter(models.Transaction.date >= start_date)
    if end_date is not None:
        q = q.filter(models.Transaction.date <= end_date)
    if start_date is None and end_date is None:
        if month is not None:
            q = q.filter(extract("month", models.Transaction.date) == month)
        if year is not None:
            q = q.filter(extract("year", models.Transaction.date) == year)
    if category_id is not None:
        q = q.filter(models.Transaction.category_id == category_id)
    if type is not None:
        q = q.filter(models.Transaction.type == type)
    return q.order_by(models.Transaction.date.desc())


@router.get("/export", tags=["transactions"])
def export_transactions_csv(
    month: Optional[int] = Query(None, ge=1, le=12),
    year: Optional[int] = Query(None, ge=2000),
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    category_id: Optional[int] = None,
    type: Optional[models.TransactionType] = None,
    db: Session = Depends(get_db),
):
    transactions = _build_query(db, month, year, start_date, end_date, category_id, type).all()

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["id", "date", "description", "category", "type", "amount"])
    for t in transactions:
        writer.writerow([t.id, t.date.isoformat(), t.description,
                         t.category.name, t.type.value, f"{t.amount:.2f}"])

    buf.seek(0)
    filename = "transactions"
    if start_date or end_date:
        filename += f"_{start_date or ''}_{end_date or ''}"
    elif month and year:
        filename += f"_{year}_{month:02d}"
    filename += ".csv"

    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/", response_model=list[schemas.TransactionOut])
def list_transactions(
    month: Optional[int] = Query(None, ge=1, le=12),
    year: Optional[int] = Query(None, ge=2000),
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    category_id: Optional[int] = None,
    type: Optional[models.TransactionType] = None,
    db: Session = Depends(get_db),
):
    return _build_query(db, month, year, start_date, end_date, category_id, type).all()


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
