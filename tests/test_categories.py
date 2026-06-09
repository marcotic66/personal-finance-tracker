from tests.conftest import make_category, make_transaction


class TestListCategories:
    def test_empty(self, client):
        r = client.get("/api/categories/")
        assert r.status_code == 200
        assert r.json() == []

    def test_returns_all_sorted_by_name(self, client):
        make_category(client, name="Salary", type="income")
        make_category(client, name="Groceries", type="expense")
        make_category(client, name="Rent", type="expense")
        names = [c["name"] for c in client.get("/api/categories/").json()]
        assert names == sorted(names)


class TestCreateCategory:
    def test_creates_expense_category(self, client):
        r = client.post("/api/categories/", json={
            "name": "Dining", "type": "expense", "color": "#f97316", "icon": "🍕",
        })
        assert r.status_code == 201
        data = r.json()
        assert data["name"] == "Dining"
        assert data["type"] == "expense"
        assert data["color"] == "#f97316"
        assert data["icon"] == "🍕"
        assert "id" in data

    def test_creates_income_category(self, client):
        r = client.post("/api/categories/", json={"name": "Salary", "type": "income"})
        assert r.status_code == 201
        assert r.json()["type"] == "income"

    def test_duplicate_name_returns_409(self, client):
        make_category(client, name="Groceries")
        r = client.post("/api/categories/", json={"name": "Groceries", "type": "expense"})
        assert r.status_code == 409

    def test_missing_required_fields_returns_422(self, client):
        r = client.post("/api/categories/", json={"name": "No type"})
        assert r.status_code == 422

    def test_default_color_and_icon_applied(self, client):
        r = client.post("/api/categories/", json={"name": "Misc", "type": "expense"})
        data = r.json()
        assert data["color"] == "#6366f1"
        assert data["icon"] == "💰"


class TestGetCategory:
    def test_get_existing(self, client):
        cat = make_category(client, name="Transport")
        r = client.get(f"/api/categories/{cat['id']}")
        assert r.status_code == 200
        assert r.json()["name"] == "Transport"

    def test_not_found_returns_404(self, client):
        r = client.get("/api/categories/999")
        assert r.status_code == 404


class TestUpdateCategory:
    def test_updates_name(self, client):
        cat = make_category(client, name="Old Name")
        r = client.put(f"/api/categories/{cat['id']}", json={"name": "New Name"})
        assert r.status_code == 200
        assert r.json()["name"] == "New Name"

    def test_updates_color_only(self, client):
        cat = make_category(client, name="Shopping", color="#aaaaaa")
        r = client.put(f"/api/categories/{cat['id']}", json={"color": "#ffffff"})
        assert r.status_code == 200
        data = r.json()
        assert data["color"] == "#ffffff"
        assert data["name"] == "Shopping"

    def test_not_found_returns_404(self, client):
        r = client.put("/api/categories/999", json={"name": "Ghost"})
        assert r.status_code == 404


class TestDeleteCategory:
    def test_deletes_unused_category(self, client):
        cat = make_category(client)
        r = client.delete(f"/api/categories/{cat['id']}")
        assert r.status_code == 204
        assert client.get(f"/api/categories/{cat['id']}").status_code == 404

    def test_cannot_delete_category_with_transactions(self, client):
        cat = make_category(client)
        make_transaction(client, cat["id"])
        r = client.delete(f"/api/categories/{cat['id']}")
        assert r.status_code == 409

    def test_not_found_returns_404(self, client):
        r = client.delete("/api/categories/999")
        assert r.status_code == 404
