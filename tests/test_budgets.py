from tests.conftest import make_category, make_budget


class TestListBudgets:
    def test_empty(self, client):
        r = client.get("/api/budgets/")
        assert r.status_code == 200
        assert r.json() == []

    def test_filter_by_month(self, client):
        cat = make_category(client)
        make_budget(client, cat["id"], month=6, year=2026)
        make_budget(client, cat["id"], month=7, year=2026)
        data = client.get("/api/budgets/?month=6").json()
        assert len(data) == 1
        assert data[0]["month"] == 6

    def test_filter_by_year(self, client):
        cat = make_category(client)
        make_budget(client, cat["id"], month=1, year=2026)
        make_budget(client, cat["id"], month=1, year=2025)
        data = client.get("/api/budgets/?year=2026").json()
        assert len(data) == 1
        assert data[0]["year"] == 2026

    def test_filter_by_month_and_year(self, client):
        cat1 = make_category(client, name="Food")
        cat2 = make_category(client, name="Transport")
        make_budget(client, cat1["id"], month=6, year=2026)
        make_budget(client, cat2["id"], month=5, year=2026)
        data = client.get("/api/budgets/?month=6&year=2026").json()
        assert len(data) == 1

    def test_returns_budget_with_category(self, client):
        cat = make_category(client, name="Dining")
        make_budget(client, cat["id"])
        data = client.get("/api/budgets/").json()
        assert data[0]["category"]["name"] == "Dining"


class TestCreateBudget:
    def test_creates_budget(self, client):
        cat = make_category(client)
        r = client.post("/api/budgets/", json={
            "category_id": cat["id"], "amount": 300.0, "month": 6, "year": 2026,
        })
        assert r.status_code == 201
        data = r.json()
        assert data["amount"] == 300.0
        assert data["month"] == 6
        assert data["year"] == 2026

    def test_duplicate_period_returns_409(self, client):
        cat = make_category(client)
        make_budget(client, cat["id"], month=6, year=2026)
        r = client.post("/api/budgets/", json={
            "category_id": cat["id"], "amount": 400.0, "month": 6, "year": 2026,
        })
        assert r.status_code == 409

    def test_same_category_different_months_allowed(self, client):
        cat = make_category(client)
        make_budget(client, cat["id"], month=6, year=2026)
        r = client.post("/api/budgets/", json={
            "category_id": cat["id"], "amount": 300.0, "month": 7, "year": 2026,
        })
        assert r.status_code == 201

    def test_nonexistent_category_returns_404(self, client):
        r = client.post("/api/budgets/", json={
            "category_id": 999, "amount": 100.0, "month": 6, "year": 2026,
        })
        assert r.status_code == 404

    def test_zero_amount_returns_422(self, client):
        cat = make_category(client)
        r = client.post("/api/budgets/", json={
            "category_id": cat["id"], "amount": 0, "month": 6, "year": 2026,
        })
        assert r.status_code == 422

    def test_invalid_month_returns_422(self, client):
        cat = make_category(client)
        r = client.post("/api/budgets/", json={
            "category_id": cat["id"], "amount": 100.0, "month": 13, "year": 2026,
        })
        assert r.status_code == 422

    def test_month_zero_returns_422(self, client):
        cat = make_category(client)
        r = client.post("/api/budgets/", json={
            "category_id": cat["id"], "amount": 100.0, "month": 0, "year": 2026,
        })
        assert r.status_code == 422


class TestGetBudget:
    def test_get_existing(self, client):
        cat = make_category(client)
        b = make_budget(client, cat["id"], amount=150.0)
        r = client.get(f"/api/budgets/{b['id']}")
        assert r.status_code == 200
        assert r.json()["amount"] == 150.0

    def test_not_found_returns_404(self, client):
        r = client.get("/api/budgets/999")
        assert r.status_code == 404


class TestUpdateBudget:
    def test_updates_amount(self, client):
        cat = make_category(client)
        b = make_budget(client, cat["id"], amount=100.0)
        r = client.put(f"/api/budgets/{b['id']}", json={"amount": 250.0})
        assert r.status_code == 200
        assert r.json()["amount"] == 250.0

    def test_partial_update_preserves_other_fields(self, client):
        cat = make_category(client)
        b = make_budget(client, cat["id"], amount=100.0, month=6, year=2026)
        r = client.put(f"/api/budgets/{b['id']}", json={"amount": 200.0})
        data = r.json()
        assert data["month"] == 6
        assert data["year"] == 2026

    def test_not_found_returns_404(self, client):
        r = client.put("/api/budgets/999", json={"amount": 100.0})
        assert r.status_code == 404


class TestDeleteBudget:
    def test_deletes_budget(self, client):
        cat = make_category(client)
        b = make_budget(client, cat["id"])
        r = client.delete(f"/api/budgets/{b['id']}")
        assert r.status_code == 204
        assert client.get(f"/api/budgets/{b['id']}").status_code == 404

    def test_not_found_returns_404(self, client):
        r = client.delete("/api/budgets/999")
        assert r.status_code == 404
