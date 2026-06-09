from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.database import get_db
from app import models, schemas

router = APIRouter(prefix="/goals", tags=["goals"])


def _enrich(goal, db):
    """Compute current_amount from linked category transactions."""
    if goal.category_id:
        total = db.query(func.sum(models.Transaction.amount)).filter(
            models.Transaction.category_id == goal.category_id,
            models.Transaction.type == models.TransactionType.income,
        ).scalar() or 0.0
        goal.current_amount = total
    else:
        goal.current_amount = 0.0
    return goal


@router.get("/", response_model=list[schemas.SavingsGoalOut])
def list_goals(db: Session = Depends(get_db)):
    goals = db.query(models.SavingsGoal).order_by(models.SavingsGoal.created_at).all()
    return [_enrich(g, db) for g in goals]


@router.post("/", response_model=schemas.SavingsGoalOut, status_code=201)
def create_goal(payload: schemas.SavingsGoalCreate, db: Session = Depends(get_db)):
    goal = models.SavingsGoal(**payload.model_dump())
    db.add(goal)
    db.commit()
    db.refresh(goal)
    return _enrich(goal, db)


@router.get("/{goal_id}", response_model=schemas.SavingsGoalOut)
def get_goal(goal_id: int, db: Session = Depends(get_db)):
    goal = db.query(models.SavingsGoal).filter(models.SavingsGoal.id == goal_id).first()
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found")
    return _enrich(goal, db)


@router.put("/{goal_id}", response_model=schemas.SavingsGoalOut)
def update_goal(goal_id: int, payload: schemas.SavingsGoalUpdate, db: Session = Depends(get_db)):
    goal = db.query(models.SavingsGoal).filter(models.SavingsGoal.id == goal_id).first()
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found")
    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(goal, field, value)
    db.commit()
    db.refresh(goal)
    return _enrich(goal, db)


@router.delete("/{goal_id}", status_code=204)
def delete_goal(goal_id: int, db: Session = Depends(get_db)):
    goal = db.query(models.SavingsGoal).filter(models.SavingsGoal.id == goal_id).first()
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found")
    db.delete(goal)
    db.commit()
