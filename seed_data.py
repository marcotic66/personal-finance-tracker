"""Populate the database with realistic sample data for the last 3 months."""
import sys
from datetime import date, timedelta
import random

sys.path.insert(0, ".")

from app.database import SessionLocal, engine
from app import models

models.Base.metadata.create_all(bind=engine)

db = SessionLocal()

# Clear existing data
db.query(models.Budget).delete()
db.query(models.Transaction).delete()
db.query(models.Category).delete()
db.commit()

# --- Categories ---
categories_data = [
    # Income
    {"name": "Salary", "type": "income", "color": "#22c55e", "icon": "💼"},
    {"name": "Freelance", "type": "income", "color": "#16a34a", "icon": "💻"},
    {"name": "Investments", "type": "income", "color": "#15803d", "icon": "📈"},
    # Expenses
    {"name": "Housing", "type": "expense", "color": "#ef4444", "icon": "🏠"},
    {"name": "Groceries", "type": "expense", "color": "#f97316", "icon": "🛒"},
    {"name": "Dining Out", "type": "expense", "color": "#f59e0b", "icon": "🍕"},
    {"name": "Transportation", "type": "expense", "color": "#eab308", "icon": "🚗"},
    {"name": "Utilities", "type": "expense", "color": "#84cc16", "icon": "💡"},
    {"name": "Entertainment", "type": "expense", "color": "#06b6d4", "icon": "🎬"},
    {"name": "Health & Fitness", "type": "expense", "color": "#8b5cf6", "icon": "🏋️"},
    {"name": "Shopping", "type": "expense", "color": "#ec4899", "icon": "🛍️"},
    {"name": "Subscriptions", "type": "expense", "color": "#6366f1", "icon": "📱"},
    {"name": "Travel", "type": "expense", "color": "#14b8a6", "icon": "✈️"},
    {"name": "Education", "type": "expense", "color": "#0ea5e9", "icon": "📚"},
]

cats = {}
for c in categories_data:
    obj = models.Category(**c)
    db.add(obj)
    db.flush()
    cats[c["name"]] = obj
db.commit()

# --- Transactions (last 3 months) ---
today = date(2026, 6, 9)

def rand_date(year, month):
    start = date(year, month, 1)
    if month == 12:
        end = date(year + 1, 1, 1) - timedelta(days=1)
    else:
        end = date(year, month + 1, 1) - timedelta(days=1)
    delta = (end - start).days
    return start + timedelta(days=random.randint(0, delta))

months = [(2026, 4), (2026, 5), (2026, 6)]

transactions = []

for year, month in months:
    is_current = (year == today.year and month == today.month)
    day_limit = today.day if is_current else 31

    # Salary — 1st of each month
    transactions.append({
        "amount": 5200.00, "description": "Monthly salary", "type": "income",
        "category": "Salary", "date": date(year, month, 1),
    })
    # Freelance — occasional
    if random.random() > 0.4:
        transactions.append({
            "amount": round(random.uniform(300, 900), 2),
            "description": "Freelance web project",
            "type": "income", "category": "Freelance",
            "date": rand_date(year, month),
        })
    # Investments — small monthly
    transactions.append({
        "amount": round(random.uniform(50, 200), 2),
        "description": "Dividend payout",
        "type": "income", "category": "Investments",
        "date": rand_date(year, month),
    })

    # Housing — rent on the 1st
    transactions.append({
        "amount": 1450.00, "description": "Monthly rent", "type": "expense",
        "category": "Housing", "date": date(year, month, 1),
    })

    # Groceries — 3–4 trips
    grocery_items = ["Weekly groceries", "Costco run", "Whole Foods", "Trader Joe's", "Farmer's market"]
    for _ in range(random.randint(3, 4)):
        transactions.append({
            "amount": round(random.uniform(60, 180), 2),
            "description": random.choice(grocery_items),
            "type": "expense", "category": "Groceries",
            "date": rand_date(year, month),
        })

    # Dining out — 4–7 times
    dining_items = ["Chipotle", "Sushi dinner", "Pizza night", "Brunch with friends", "Coffee shop", "Thai takeout", "Burger place"]
    for _ in range(random.randint(4, 7)):
        transactions.append({
            "amount": round(random.uniform(12, 85), 2),
            "description": random.choice(dining_items),
            "type": "expense", "category": "Dining Out",
            "date": rand_date(year, month),
        })

    # Transportation
    transport_items = ["Gas fill-up", "Uber", "Monthly transit pass", "Parking"]
    for _ in range(random.randint(2, 4)):
        transactions.append({
            "amount": round(random.uniform(15, 90), 2),
            "description": random.choice(transport_items),
            "type": "expense", "category": "Transportation",
            "date": rand_date(year, month),
        })

    # Utilities
    transactions.append({"amount": round(random.uniform(80, 130), 2), "description": "Electric bill", "type": "expense", "category": "Utilities", "date": rand_date(year, month)})
    transactions.append({"amount": 65.00, "description": "Internet bill", "type": "expense", "category": "Utilities", "date": rand_date(year, month)})

    # Entertainment
    entertainment_items = ["Movie tickets", "Concert", "Board game", "Sports event", "Museum"]
    for _ in range(random.randint(1, 3)):
        transactions.append({
            "amount": round(random.uniform(15, 120), 2),
            "description": random.choice(entertainment_items),
            "type": "expense", "category": "Entertainment",
            "date": rand_date(year, month),
        })

    # Health
    transactions.append({"amount": 50.00, "description": "Gym membership", "type": "expense", "category": "Health & Fitness", "date": rand_date(year, month)})
    if random.random() > 0.6:
        transactions.append({"amount": round(random.uniform(20, 80), 2), "description": "Pharmacy", "type": "expense", "category": "Health & Fitness", "date": rand_date(year, month)})

    # Shopping
    if random.random() > 0.3:
        shopping_items = ["Amazon order", "Clothing", "Home supplies", "Electronics", "Books"]
        for _ in range(random.randint(1, 2)):
            transactions.append({
                "amount": round(random.uniform(25, 200), 2),
                "description": random.choice(shopping_items),
                "type": "expense", "category": "Shopping",
                "date": rand_date(year, month),
            })

    # Subscriptions — fixed monthly
    for sub, price in [("Netflix", 15.99), ("Spotify", 9.99), ("iCloud", 2.99), ("ChatGPT Plus", 20.00)]:
        transactions.append({
            "amount": price, "description": sub, "type": "expense",
            "category": "Subscriptions", "date": rand_date(year, month),
        })

    # Travel — occasional
    if random.random() > 0.6:
        transactions.append({
            "amount": round(random.uniform(200, 600), 2),
            "description": "Weekend trip",
            "type": "expense", "category": "Travel",
            "date": rand_date(year, month),
        })

for t in transactions:
    obj = models.Transaction(
        amount=t["amount"],
        description=t["description"],
        type=t["type"],
        category_id=cats[t["category"]].id,
        date=t["date"],
    )
    db.add(obj)
db.commit()

# --- Budgets (for all 3 months) ---
budget_targets = {
    "Housing": 1500.00,
    "Groceries": 400.00,
    "Dining Out": 250.00,
    "Transportation": 200.00,
    "Utilities": 200.00,
    "Entertainment": 150.00,
    "Health & Fitness": 100.00,
    "Shopping": 200.00,
    "Subscriptions": 60.00,
    "Travel": 300.00,
    "Education": 100.00,
}

for year, month in months:
    for cat_name, amount in budget_targets.items():
        obj = models.Budget(
            category_id=cats[cat_name].id,
            amount=amount,
            month=month,
            year=year,
        )
        db.add(obj)
db.commit()

db.close()

tx_count = sum(1 for _ in transactions)
print(f"Seeded {len(categories_data)} categories, {tx_count} transactions, {len(budget_targets) * len(months)} budgets.")
print("Done! Run: uv run uvicorn main:app --reload")
