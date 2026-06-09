from datetime import date, datetime
from typing import Optional
from pydantic import BaseModel, field_validator
from app.models import TransactionType


class CategoryBase(BaseModel):
    name: str
    type: TransactionType
    color: str = "#6366f1"
    icon: str = "💰"


class CategoryCreate(CategoryBase):
    pass


class CategoryUpdate(BaseModel):
    name: Optional[str] = None
    type: Optional[TransactionType] = None
    color: Optional[str] = None
    icon: Optional[str] = None


class CategoryOut(CategoryBase):
    id: int
    created_at: datetime

    model_config = {"from_attributes": True}


class TransactionBase(BaseModel):
    amount: float
    description: str
    date: date
    type: TransactionType
    category_id: int

    @field_validator("amount")
    @classmethod
    def amount_must_be_positive(cls, v):
        if v <= 0:
            raise ValueError("amount must be positive")
        return v


class TransactionCreate(TransactionBase):
    pass


class TransactionUpdate(BaseModel):
    amount: Optional[float] = None
    description: Optional[str] = None
    date: Optional[date] = None
    type: Optional[TransactionType] = None
    category_id: Optional[int] = None


class TransactionOut(TransactionBase):
    id: int
    created_at: datetime
    category: CategoryOut

    model_config = {"from_attributes": True}


class BudgetBase(BaseModel):
    category_id: int
    amount: float
    month: int
    year: int

    @field_validator("month")
    @classmethod
    def month_range(cls, v):
        if not 1 <= v <= 12:
            raise ValueError("month must be between 1 and 12")
        return v

    @field_validator("amount")
    @classmethod
    def amount_positive(cls, v):
        if v <= 0:
            raise ValueError("amount must be positive")
        return v


class BudgetCreate(BudgetBase):
    pass


class BudgetUpdate(BaseModel):
    amount: Optional[float] = None
    month: Optional[int] = None
    year: Optional[int] = None


class BudgetOut(BudgetBase):
    id: int
    created_at: datetime
    category: CategoryOut

    model_config = {"from_attributes": True}


class CategorySummary(BaseModel):
    category_id: int
    category_name: str
    category_color: str
    category_icon: str
    type: TransactionType
    total: float
    budget: Optional[float] = None
    budget_id: Optional[int] = None


class MonthlySummary(BaseModel):
    month: int
    year: int
    total_income: float
    total_expenses: float
    net: float
    by_category: list[CategorySummary]
