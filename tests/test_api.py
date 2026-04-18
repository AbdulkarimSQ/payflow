"""
PayFlow API Tests — Integration tests for all endpoints
"""
import pytest
from app.routes import app, db
from app.models import Merchant


@pytest.fixture(autouse=True)
def reset_db():
    """Reset all tables before each test."""
    db.connection.executescript("""
        DELETE FROM payments;
        DELETE FROM orders;
        DELETE FROM merchants;
        DELETE FROM users;
    """)
    db.connection.commit()
    # Re-seed test merchant
    m = Merchant("IKEA", "ikea@tabby.ai", "furniture")
    db.save_merchant(m)
    yield


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


@pytest.fixture
def auth_token(client):
    client.post("/api/register", json={
        "name": "Test User",
        "email": "test@mail.com",
        "password": "pass1234",
    })
    res = client.post("/api/login", json={
        "email": "test@mail.com",
        "password": "pass1234",
    })
    return res.json["token"]


@pytest.fixture
def auth_headers(auth_token):
    return {"Authorization": f"Bearer {auth_token}"}


@pytest.fixture
def funded_headers(client, auth_headers):
    """Auth headers for a user with 10000 balance."""
    client.post("/api/deposit", json={"amount": 10000}, headers=auth_headers)
    return auth_headers


@pytest.fixture
def merchant_id():
    rows = db.get_all_merchants()
    return rows[0]["merchant_id"]


# ═══ Health ═══
class TestHealth:
    def test_health(self, client):
        res = client.get("/api/health")
        assert res.status_code == 200
        assert res.json["status"] == "ok"


# ═══ Register ═══
class TestRegister:
    def test_register_success(self, client):
        res = client.post("/api/register", json={
            "name": "Ahmed",
            "email": "ahmed@test.com",
            "password": "pass1234",
        })
        assert res.status_code == 201
        assert "user_id" in res.json

    def test_register_missing_fields(self, client):
        res = client.post("/api/register", json={"name": "Ahmed"})
        assert res.status_code == 400

    def test_register_duplicate_email(self, client):
        client.post("/api/register", json={
            "name": "A", "email": "dup@test.com", "password": "pass1234",
        })
        res = client.post("/api/register", json={
            "name": "B", "email": "dup@test.com", "password": "pass1234",
        })
        assert res.status_code == 400


# ═══ Login ═══
class TestLogin:
    def test_login_success(self, client):
        client.post("/api/register", json={
            "name": "Ali", "email": "ali@test.com", "password": "pass1234",
        })
        res = client.post("/api/login", json={
            "email": "ali@test.com", "password": "pass1234",
        })
        assert res.status_code == 200
        assert "token" in res.json

    def test_login_wrong_password(self, client):
        client.post("/api/register", json={
            "name": "Ali", "email": "ali2@test.com", "password": "pass1234",
        })
        res = client.post("/api/login", json={
            "email": "ali2@test.com", "password": "wrongpass",
        })
        assert res.status_code == 401

    def test_login_nonexistent(self, client):
        res = client.post("/api/login", json={
            "email": "nobody@test.com", "password": "pass1234",
        })
        assert res.status_code == 401


# ═══ Me ═══
class TestMe:
    def test_me_with_token(self, client, auth_headers):
        res = client.get("/api/me", headers=auth_headers)
        assert res.status_code == 200
        assert res.json["name"] == "Test User"

    def test_me_without_token(self, client):
        res = client.get("/api/me")
        assert res.status_code == 401


# ═══ Deposit ═══
class TestDeposit:
    def test_deposit_success(self, client, auth_headers):
        res = client.post("/api/deposit", json={"amount": 5000}, headers=auth_headers)
        assert res.status_code == 200
        assert res.json["balance"] == 5000.0

    def test_deposit_negative(self, client, auth_headers):
        res = client.post("/api/deposit", json={"amount": -100}, headers=auth_headers)
        assert res.status_code == 400

    def test_deposit_without_token(self, client):
        res = client.post("/api/deposit", json={"amount": 500})
        assert res.status_code == 401


# ═══ Merchants ═══
class TestMerchants:
    def test_list_merchants(self, client, auth_headers):
        res = client.get("/api/merchants", headers=auth_headers)
        assert res.status_code == 200
        merchants = res.json["merchants"]
        assert len(merchants) >= 1
        assert merchants[0]["name"] == "IKEA"

    def test_list_merchants_without_token(self, client):
        res = client.get("/api/merchants")
        assert res.status_code == 401


# ═══ Orders ═══
class TestOrders:
    def test_create_order(self, client, funded_headers, merchant_id):
        res = client.post("/api/orders", json={
            "merchant_id": merchant_id,
            "amount": 1200,
            "installments": 4,
        }, headers=funded_headers)
        assert res.status_code == 201
        assert res.json["amount"] == 1200
        assert res.json["installment_amount"] == 300.0
        assert res.json["status"] == "pending"

    def test_create_order_invalid_merchant(self, client, funded_headers):
        res = client.post("/api/orders", json={
            "merchant_id": "fake-id",
            "amount": 500,
        }, headers=funded_headers)
        assert res.status_code == 404

    def test_create_order_missing_amount(self, client, funded_headers, merchant_id):
        res = client.post("/api/orders", json={
            "merchant_id": merchant_id,
        }, headers=funded_headers)
        assert res.status_code == 400

    def test_list_orders(self, client, funded_headers, merchant_id):
        client.post("/api/orders", json={
            "merchant_id": merchant_id, "amount": 500, "installments": 2,
        }, headers=funded_headers)
        res = client.get("/api/orders", headers=funded_headers)
        assert res.status_code == 200
        assert len(res.json) == 1

    def test_list_orders_empty(self, client, auth_headers):
        res = client.get("/api/orders", headers=auth_headers)
        assert res.status_code == 200
        assert res.json == []


# ═══ Approve Order ═══
class TestApproveOrder:
    def test_approve_order(self, client, funded_headers, merchant_id):
        create = client.post("/api/orders", json={
            "merchant_id": merchant_id, "amount": 600, "installments": 3,
        }, headers=funded_headers)
        order_id = create.json["order_id"]

        res = client.post(f"/api/orders/{order_id}/approve", headers=funded_headers)
        assert res.status_code == 200
        assert res.json["status"] == "approved"

    def test_approve_nonexistent(self, client, auth_headers):
        res = client.post("/api/orders/fake-id/approve", headers=auth_headers)
        assert res.status_code == 404

    def test_double_approve(self, client, funded_headers, merchant_id):
        create = client.post("/api/orders", json={
            "merchant_id": merchant_id, "amount": 400, "installments": 2,
        }, headers=funded_headers)
        order_id = create.json["order_id"]

        client.post(f"/api/orders/{order_id}/approve", headers=funded_headers)
        res = client.post(f"/api/orders/{order_id}/approve", headers=funded_headers)
        assert res.status_code == 400


# ═══ Pay Installment ═══
class TestPayInstallment:
    def _create_and_approve(self, client, headers, merchant_id, amount=1000, installments=2):
        create = client.post("/api/orders", json={
            "merchant_id": merchant_id,
            "amount": amount,
            "installments": installments,
        }, headers=headers)
        order_id = create.json["order_id"]
        client.post(f"/api/orders/{order_id}/approve", headers=headers)
        return order_id

    def test_pay_installment(self, client, funded_headers, merchant_id):
        order_id = self._create_and_approve(client, funded_headers, merchant_id)
        res = client.post(f"/api/orders/{order_id}/pay", headers=funded_headers)
        assert res.status_code == 200
        assert res.json["installments_paid"] == 1
        assert res.json["remaining"] == 500.0

    def test_full_payment_flow(self, client, funded_headers, merchant_id):
        order_id = self._create_and_approve(client, funded_headers, merchant_id)
        for _ in range(2):
            res = client.post(f"/api/orders/{order_id}/pay", headers=funded_headers)
            assert res.status_code == 200
        assert res.json["installments_paid"] == 2
        assert res.json["remaining"] == 0

    def test_pay_nonexistent_order(self, client, auth_headers):
        res = client.post("/api/orders/fake-id/pay", headers=auth_headers)
        assert res.status_code == 404

    def test_pay_pending_order(self, client, funded_headers, merchant_id):
        create = client.post("/api/orders", json={
            "merchant_id": merchant_id, "amount": 500, "installments": 2,
        }, headers=funded_headers)
        order_id = create.json["order_id"]
        res = client.post(f"/api/orders/{order_id}/pay", headers=funded_headers)
        assert res.status_code == 400

    def test_overpay(self, client, funded_headers, merchant_id):
        order_id = self._create_and_approve(client, funded_headers, merchant_id)
        for _ in range(2):
            client.post(f"/api/orders/{order_id}/pay", headers=funded_headers)
        res = client.post(f"/api/orders/{order_id}/pay", headers=funded_headers)
        assert res.status_code == 400


class TestHealth:
    def test_health_check(self, client):
        response = client.get("/api/health")
        assert response.status_code == 200
        data = response.get_json()
        assert data["status"] == "ok"

    def test_health_check_post_not_allowed(self, client):
        response = client.post("/api/health")
        assert response.status_code == 405
