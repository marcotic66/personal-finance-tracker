import pytest
from pydantic import ValidationError

from app.schemas import (
    CategoryCreate, CategoryUpdate,
    TransactionCreate, TransactionUpdate,
    BudgetCreate, BudgetUpdate,
)


class TestCategorySchema:
    def test_valid_expense_category(self):
        c = CategoryCreate(name="Groceries", type="expense")
        assert c.name == "Groceries"
        assert c.type == "expense"

    def test_valid_income_category(self):
        c = CategoryCreate(name="Salary", type="income")
        assert c.type == "income"

    def test_default_color_and_icon(self):
        c = CategoryCreate(name="Misc", type="expense")
        assert c.color == "#6366f1"
        assert c.icon == "💰"

    def test_invalid_type_raises(self):
        with pytest.raises(ValidationError):
            CategoryCreate(name="X", type="savings")

    def test_missing_name_raises(self):
        with pytest.raises(ValidationError):
            CategoryCreate(type="expense")

    def test_update_all_optional(self):
        u = CategoryUpdate()
        assert u.name is None
        assert u.type is None


class TestTransactionSchema:
    def _valid(self, **kwargs):
        defaults = dict(amount=50.0, description="Test", date="2026-06-01",
                        type="expense", category_id=1)
        defaults.update(kwargs)
        return TransactionCreate(**defaults)

    def test_valid_transaction(self):
        t = self._valid()
        assert t.amount == 50.0

    def test_zero_amount_raises(self):
        with pytest.raises(ValidationError):
            self._valid(amount=0)

    def test_negative_amount_raises(self):
        with pytest.raises(ValidationError):
            self._valid(amount=-1.0)

    def test_positive_amount_passes(self):
        t = self._valid(amount=0.01)
        assert t.amount == 0.01

    def test_invalid_type_raises(self):
        with pytest.raises(ValidationError):
            self._valid(type="transfer")

    def test_missing_required_field_raises(self):
        with pytest.raises(ValidationError):
            TransactionCreate(amount=10.0, type="expense", category_id=1)

    def test_update_all_optional(self):
        u = TransactionUpdate()
        assert u.amount is None
        assert u.description is None


class TestBudgetSchema:
    def _valid(self, **kwargs):
        defaults = dict(category_id=1, amount=200.0, month=6, year=2026)
        defaults.update(kwargs)
        return BudgetCreate(**defaults)

    def test_valid_budget(self):
        b = self._valid()
        assert b.amount == 200.0
        assert b.month == 6

    def test_zero_amount_raises(self):
        with pytest.raises(ValidationError):
            self._valid(amount=0)

    def test_negative_amount_raises(self):
        with pytest.raises(ValidationError):
            self._valid(amount=-100.0)

    def test_month_zero_raises(self):
        with pytest.raises(ValidationError):
            self._valid(month=0)

    def test_month_13_raises(self):
        with pytest.raises(ValidationError):
            self._valid(month=13)

    def test_month_boundary_1(self):
        b = self._valid(month=1)
        assert b.month == 1

    def test_month_boundary_12(self):
        b = self._valid(month=12)
        assert b.month == 12

    def test_update_all_optional(self):
        u = BudgetUpdate()
        assert u.amount is None
        assert u.month is None
