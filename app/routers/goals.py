from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app import models, schemas

router = APIRouter(prefix="/goals", tags=["goals"])


@router.get("/", response_model=list[schemas.SavingsGoalOut])
def list_goals(db: Session = Depends(get_db)):
    return db.query(models.SavingsGoal).order_by(models.SavingsGoal.created_at).all()


@router.post("/", response_model=schemas.SavingsGoalOut, status_code=201)
def create_goal(payload: schemas.SavingsGoalCreate, db: Session = Depends(get_db)):
    goal = models.SavingsGoal(**payload.model_dump())
    db.add(goal)
    db.commit()
    db.refresh(goal)
    return goal


@router.get("/{goal_id}", response_model=schemas.SavingsGoalOut)
def get_goal(goal_id: int, db: Session = Depends(get_db)):
    goal = db.query(models.SavingsGoal).filter(models.SavingsGoal.id == goal_id).first()
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found")
    return goal


@router.put("/{goal_id}", response_model=schemas.SavingsGoalOut)
def update_goal(goal_id: int, payload: schemas.SavingsGoalUpdate, db: Session = Depends(get_db)):
    goal = db.query(models.SavingsGoal).filter(models.SavingsGoal.id == goal_id).first()
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found")
    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(goal, field, value)
    db.commit()
    db.refresh(goal)
    return goal


@router.delete("/{goal_id}", status_code=204)
def delete_goal(goal_id: int, db: Session = Depends(get_db)):
    goal = db.query(models.SavingsGoal).filter(models.SavingsGoal.id == goal_id).first()
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found")
    db.delete(goal)
    db.commit()
