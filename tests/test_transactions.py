from tests.conftest import make_category, make_transaction


class TestListTransactions:
    def test_empty(self, client):
        r = client.get("/api/transactions/")
        assert r.status_code == 200
        assert r.json() == []

    def test_returns_transactions_with_category(self, client):
        cat = make_category(client)
        make_transaction(client, cat["id"])
        data = client.get("/api/transactions/").json()
        assert len(data) == 1
        assert data[0]["category"]["name"] == "Groceries"

    def test_filter_by_month(self, client):
        cat = make_category(client)
        make_transaction(client, cat["id"], date="2026-06-15")
        make_transaction(client, cat["id"], date="2026-07-01")
        data = client.get("/api/transactions/?month=6").json()
        assert len(data) == 1
        assert data[0]["date"] == "2026-06-15"

    def test_filter_by_year(self, client):
        cat = make_category(client)
        make_transaction(client, cat["id"], date="2026-01-01")
        make_transaction(client, cat["id"], date="2025-01-01")
        data = client.get("/api/transactions/?year=2026").json()
        assert len(data) == 1

    def test_filter_by_month_and_year(self, client):
        cat = make_category(client)
        make_transaction(client, cat["id"], date="2026-06-01")
        make_transaction(client, cat["id"], date="2026-05-01")
        make_transaction(client, cat["id"], date="2025-06-01")
        data = client.get("/api/transactions/?month=6&year=2026").json()
        assert len(data) == 1

    def test_filter_by_type(self, client):
        exp_cat = make_category(client, name="Food", type="expense")
        inc_cat = make_category(client, name="Salary", type="income")
        make_transaction(client, exp_cat["id"], type="expense")
        make_transaction(client, inc_cat["id"], type="income")
        data = client.get("/api/transactions/?type=income").json()
        assert len(data) == 1
        assert data[0]["type"] == "income"

    def test_filter_by_category_id(self, client):
        cat1 = make_category(client, name="Food")
        cat2 = make_category(client, name="Transport")
        make_transaction(client, cat1["id"])
        make_transaction(client, cat2["id"])
        data = client.get(f"/api/transactions/?category_id={cat1['id']}").json()
        assert len(data) == 1
        assert data[0]["category_id"] == cat1["id"]

    def test_ordered_by_date_descending(self, client):
        cat = make_category(client)
        make_transaction(client, cat["id"], date="2026-06-01")
        make_transaction(client, cat["id"], date="2026-06-20")
        make_transaction(client, cat["id"], date="2026-06-10")
        dates = [t["date"] for t in client.get("/api/transactions/").json()]
        assert dates == sorted(dates, reverse=True)


class TestCreateTransaction:
    def test_creates_expense(self, client):
        cat = make_category(client, name="Rent", type="expense")
        r = client.post("/api/transactions/", json={
            "amount": 1200.0, "description": "Monthly rent",
            "date": "2026-06-01", "type": "expense", "category_id": cat["id"],
        })
        assert r.status_code == 201
        data = r.json()
        assert data["amount"] == 1200.0
        assert data["description"] == "Monthly rent"
        assert data["category"]["id"] == cat["id"]

    def test_creates_income(self, client):
        cat = make_category(client, name="Salary", type="income")
        r = client.post("/api/transactions/", json={
            "amount": 5000.0, "description": "Paycheck",
            "date": "2026-06-01", "type": "income", "category_id": cat["id"],
        })
        assert r.status_code == 201
        assert r.json()["type"] == "income"

    def test_category_type_mismatch_returns_422(self, client):
        cat = make_category(client, name="Groceries", type="expense")
        r = client.post("/api/transactions/", json={
            "amount": 100.0, "description": "Wrong type",
            "date": "2026-06-01", "type": "income", "category_id": cat["id"],
        })
        assert r.status_code == 422

    def test_nonexistent_category_returns_404(self, client):
        r = client.post("/api/transactions/", json={
            "amount": 50.0, "description": "Ghost category",
            "date": "2026-06-01", "type": "expense", "category_id": 999,
        })
        assert r.status_code == 404

    def test_zero_amount_returns_422(self, client):
        cat = make_category(client)
        r = client.post("/api/transactions/", json={
            "amount": 0, "description": "Zero", "date": "2026-06-01",
            "type": "expense", "category_id": cat["id"],
        })
        assert r.status_code == 422

    def test_negative_amount_returns_422(self, client):
        cat = make_category(client)
        r = client.post("/api/transactions/", json={
            "amount": -10.0, "description": "Negative", "date": "2026-06-01",
            "type": "expense", "category_id": cat["id"],
        })
        assert r.status_code == 422


class TestGetTransaction:
    def test_get_existing(self, client):
        cat = make_category(client)
        tx = make_transaction(client, cat["id"], amount=75.0)
        r = client.get(f"/api/transactions/{tx['id']}")
        assert r.status_code == 200
        assert r.json()["amount"] == 75.0

    def test_not_found_returns_404(self, client):
        r = client.get("/api/transactions/999")
        assert r.status_code == 404


class TestUpdateTransaction:
    def test_updates_amount(self, client):
        cat = make_category(client)
        tx = make_transaction(client, cat["id"], amount=50.0)
        r = client.put(f"/api/transactions/{tx['id']}", json={"amount": 99.99})
        assert r.status_code == 200
        assert r.json()["amount"] == 99.99

    def test_updates_description(self, client):
        cat = make_category(client)
        tx = make_transaction(client, cat["id"], description="Old")
        r = client.put(f"/api/transactions/{tx['id']}", json={"description": "New"})
        assert r.status_code == 200
        assert r.json()["description"] == "New"

    def test_updates_category(self, client):
        cat1 = make_category(client, name="Food")
        cat2 = make_category(client, name="Transport")
        tx = make_transaction(client, cat1["id"])
        r = client.put(f"/api/transactions/{tx['id']}", json={"category_id": cat2["id"]})
        assert r.status_code == 200
        assert r.json()["category_id"] == cat2["id"]

    def test_update_to_nonexistent_category_returns_404(self, client):
        cat = make_category(client)
        tx = make_transaction(client, cat["id"])
        r = client.put(f"/api/transactions/{tx['id']}", json={"category_id": 999})
        assert r.status_code == 404

    def test_not_found_returns_404(self, client):
        r = client.put("/api/transactions/999", json={"amount": 10.0})
        assert r.status_code == 404


class TestDeleteTransaction:
    def test_deletes_transaction(self, client):
        cat = make_category(client)
        tx = make_transaction(client, cat["id"])
        r = client.delete(f"/api/transactions/{tx['id']}")
        assert r.status_code == 204
        assert client.get(f"/api/transactions/{tx['id']}").status_code == 404

    def test_not_found_returns_404(self, client):
        r = client.delete("/api/transactions/999")
        assert r.status_code == 404
