# Requirements

## Overview

A personal finance tracker that lets a user log income and expenses, organize them into categories, set monthly spending budgets, and view a summary of where their money is going.

## Functional Requirements

### Transactions
- Log a transaction with an amount, description, date, type (income or expense), and category
- Edit or delete any transaction
- View transactions filtered by month/year, category, or type
- Amounts must be positive; category type must match transaction type

### Categories
- Create named categories tagged as income or expense, with a display color and emoji icon
- Edit a category's name, type, color, or icon
- Delete a category — blocked if any transactions reference it
- Category names are unique

### Budgets
- Set a monthly spending budget for any expense category
- One budget per category per month/year period
- Edit or remove a budget at any time
- Budgets apply only to expense categories

### Dashboard / Summary
- View total income, total expenses, and net balance for a selected month
- Visualize expense breakdown by category (donut chart)
- Compare actual spending against budgets by category (bar chart)
- See progress bars per budgeted category with over-budget alerts
- Navigate forward and backward across months

## Non-Functional Requirements

- All data persisted locally in a SQLite database
- REST API must return JSON; interactive docs available at `/docs`
- Web UI must work without a build step — plain HTML/CSS/JS
- Python dependencies managed with `uv`
- Re-seeding sample data must be idempotent (clears and repopulates)

## Out of Scope

- User authentication / multi-user support
- Recurring transactions
- Data export
- Mobile native app
