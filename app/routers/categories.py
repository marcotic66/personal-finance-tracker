from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app import models, schemas

router = APIRouter(prefix="/categories", tags=["categories"])


@router.get("/", response_model=list[schemas.CategoryOut])
def list_categories(db: Session = Depends(get_db)):
    return db.query(models.Category).order_by(models.Category.name).all()


@router.post("/", response_model=schemas.CategoryOut, status_code=201)
def create_category(payload: schemas.CategoryCreate, db: Session = Depends(get_db)):
    existing = db.query(models.Category).filter(models.Category.name == payload.name).first()
    if existing:
        raise HTTPException(status_code=409, detail="Category name already exists")
    category = models.Category(**payload.model_dump())
    db.add(category)
    db.commit()
    db.refresh(category)
    return category


@router.get("/{category_id}", response_model=schemas.CategoryOut)
def get_category(category_id: int, db: Session = Depends(get_db)):
    category = db.query(models.Category).filter(models.Category.id == category_id).first()
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    return category


@router.put("/{category_id}", response_model=schemas.CategoryOut)
def update_category(category_id: int, payload: schemas.CategoryUpdate, db: Session = Depends(get_db)):
    category = db.query(models.Category).filter(models.Category.id == category_id).first()
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(category, field, value)
    db.commit()
    db.refresh(category)
    return category


@router.delete("/{category_id}", status_code=204)
def delete_category(category_id: int, db: Session = Depends(get_db)):
    category = db.query(models.Category).filter(models.Category.id == category_id).first()
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    if category.transactions:
        raise HTTPException(status_code=409, detail="Cannot delete category with existing transactions")
    db.delete(category)
    db.commit()
