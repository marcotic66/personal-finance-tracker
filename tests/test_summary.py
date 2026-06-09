from tests.conftest import make_category, make_transaction, make_budget


class TestSummaryEndpoint:
    def test_empty_month_returns_zeros(self, client):
        r = client.get("/api/summary/?month=6&year=2026")
        assert r.status_code == 200
        data = r.json()
        assert data["total_income"] == 0.0
        assert data["total_expenses"] == 0.0
        assert data["net"] == 0.0
        assert data["by_category"] == []

    def test_requires_month_and_year(self, client):
        assert client.get("/api/summary/?month=6").status_code == 422
        assert client.get("/api/summary/?year=2026").status_code == 422
        assert client.get("/api/summary/").status_code == 422

    def test_totals_income_correctly(self, client):
        cat = make_category(client, name="Salary", type="income")
        make_transaction(client, cat["id"], amount=3000.0, type="income", date="2026-06-01")
        make_transaction(client, cat["id"], amount=2000.0, type="income", date="2026-06-15")
        data = client.get("/api/summary/?month=6&year=2026").json()
        assert data["total_income"] == 5000.0
        assert data["total_expenses"] == 0.0
        assert data["net"] == 5000.0

    def test_totals_expenses_correctly(self, client):
        cat = make_category(client, name="Food", type="expense")
        make_transaction(client, cat["id"], amount=100.0, date="2026-06-01")
        make_transaction(client, cat["id"], amount=50.0, date="2026-06-10")
        data = client.get("/api/summary/?month=6&year=2026").json()
        assert data["total_expenses"] == 150.0
        assert data["total_income"] == 0.0
        assert data["net"] == -150.0

    def test_net_income_minus_expenses(self, client):
        inc = make_category(client, name="Salary", type="income")
        exp = make_category(client, name="Rent", type="expense")
        make_transaction(client, inc["id"], amount=5000.0, type="income", date="2026-06-01")
        make_transaction(client, exp["id"], amount=1500.0, date="2026-06-01")
        data = client.get("/api/summary/?month=6&year=2026").json()
        assert data["total_income"] == 5000.0
        assert data["total_expenses"] == 1500.0
        assert data["net"] == 3500.0

    def test_only_includes_transactions_in_period(self, client):
        cat = make_category(client, name="Food", type="expense")
        make_transaction(client, cat["id"], amount=200.0, date="2026-06-15")
        make_transaction(client, cat["id"], amount=999.0, date="2026-07-01")
        make_transaction(client, cat["id"], amount=999.0, date="2025-06-01")
        data = client.get("/api/summary/?month=6&year=2026").json()
        assert data["total_expenses"] == 200.0

    def test_by_category_aggregates_multiple_transactions(self, client):
        cat = make_category(client, name="Food", type="expense")
        make_transaction(client, cat["id"], amount=40.0, date="2026-06-01")
        make_transaction(client, cat["id"], amount=60.0, date="2026-06-10")
        data = client.get("/api/summary/?month=6&year=2026").json()
        cat_data = data["by_category"][0]
        assert cat_data["category_name"] == "Food"
        assert cat_data["total"] == 100.0

    def test_by_category_includes_budget(self, client):
        cat = make_category(client, name="Groceries", type="expense")
        make_transaction(client, cat["id"], amount=80.0, date="2026-06-01")
        make_budget(client, cat["id"], amount=200.0, month=6, year=2026)
        data = client.get("/api/summary/?month=6&year=2026").json()
        cat_data = data["by_category"][0]
        assert cat_data["budget"] == 200.0
        assert cat_data["budget_id"] is not None

    def test_by_category_includes_budgeted_categories_with_no_spending(self, client):
        cat = make_category(client, name="Travel", type="expense")
        make_budget(client, cat["id"], amount=500.0, month=6, year=2026)
        data = client.get("/api/summary/?month=6&year=2026").json()
        assert len(data["by_category"]) == 1
        assert data["by_category"][0]["total"] == 0.0
        assert data["by_category"][0]["budget"] == 500.0

    def test_by_category_sorted_by_total_descending(self, client):
        cat1 = make_category(client, name="Rent", type="expense")
        cat2 = make_category(client, name="Coffee", type="expense")
        make_transaction(client, cat1["id"], amount=1500.0, date="2026-06-01")
        make_transaction(client, cat2["id"], amount=30.0, date="2026-06-05")
        data = client.get("/api/summary/?month=6&year=2026").json()
        totals = [c["total"] for c in data["by_category"]]
        assert totals == sorted(totals, reverse=True)

    def test_category_meta_present_in_by_category(self, client):
        cat = make_category(client, name="Dining", type="expense", color="#f97316", icon="🍕")
        make_transaction(client, cat["id"], amount=50.0, date="2026-06-01")
        entry = client.get("/api/summary/?month=6&year=2026").json()["by_category"][0]
        assert entry["category_name"] == "Dining"
        assert entry["category_color"] == "#f97316"
        assert entry["category_icon"] == "🍕"
        assert entry["type"] == "expense"
