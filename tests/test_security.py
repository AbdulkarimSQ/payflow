"""
PayFlow Security Tests — Validation, Rate Limiting, Idempotency
"""
import pytest
from app.routes import app, db
from app.models import Merchant
from app.rate_limiter import login_limiter


@pytest.fixture(autouse=True)
def reset():
    db.connection.executescript("""
        DELETE FROM payments;
        DELETE FROM orders;
        DELETE FROM merchants;
        DELETE FROM users;
    """)
    db.connection.commit()
    m = Merchant("IKEA", "ikea@tabby.ai", "furniture")
    db.save_merchant(m)
    login_limiter.reset("127.0.0.1")
    yield


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


class TestValidation:
    def test_invalid_email(self, client):
        res = client.post("/api/register", json={
            "name": "Test", "email": "not-an-email", "password": "pass12345"
        })
        assert res.status_code == 400

    def test_short_password(self, client):
        res = client.post("/api/register", json={
            "name": "Test", "email": "test@mail.com", "password": "123"
        })
        assert res.status_code == 400

    def test_empty_name(self, client):
        res = client.post("/api/register", json={
            "name": "", "email": "test@mail.com", "password": "pass12345"
        })
        assert res.status_code == 400

    def test_negative_deposit(self, client):
        # Register + Login
        client.post("/api/register", json={
            "name": "Ali", "email": "ali@mail.com", "password": "pass12345"
        })
        res = client.post("/api/login", json={
            "email": "ali@mail.com", "password": "pass12345"
        })
        token = res.json["token"]
        headers = {"Authorization": f"Bearer {token}"}

        res = client.post("/api/deposit", json={"amount": -500}, headers=headers)
        assert res.status_code == 400

    def test_huge_amount(self, client):
        client.post("/api/register", json={
            "name": "Ali", "email": "ali2@mail.com", "password": "pass12345"
        })
        res = client.post("/api/login", json={
            "email": "ali2@mail.com", "password": "pass12345"
        })
        token = res.json["token"]
        headers = {"Authorization": f"Bearer {token}"}

        res = client.post("/api/deposit", json={"amount": 999999}, headers=headers)
        assert res.status_code == 400


class TestRateLimiting:
    def test_rate_limit_after_5_attempts(self, client):
        # Register
        client.post("/api/register", json={
            "name": "Test", "email": "rate@mail.com", "password": "pass12345"
        })

        # 5 wrong attempts
        for _ in range(5):
            client.post("/api/login", json={
                "email": "rate@mail.com", "password": "wrongpass"
            })

        # 6th attempt should be blocked
        res = client.post("/api/login", json={
            "email": "rate@mail.com", "password": "wrongpass"
        })
        assert res.status_code == 429

    def test_correct_login_after_limit(self, client):
        client.post("/api/register", json={
            "name": "Test", "email": "rate2@mail.com", "password": "pass12345"
        })

        for _ in range(5):
            client.post("/api/login", json={
                "email": "rate2@mail.com", "password": "wrongpass"
            })

        # Even correct password blocked after limit
        res = client.post("/api/login", json={
            "email": "rate2@mail.com", "password": "pass12345"
        })
        assert res.status_code == 429

    def test_successful_login_resets_counter(self, client):
        client.post("/api/register", json={
            "name": "Test", "email": "reset@mail.com", "password": "pass12345"
        })

        # 4 wrong attempts
        for _ in range(4):
            client.post("/api/login", json={
                "email": "reset@mail.com", "password": "wrongpass"
            })

        # Correct login resets the counter
        res = client.post("/api/login", json={
            "email": "reset@mail.com", "password": "pass12345"
        })
        assert res.status_code == 200

        # 5 more wrong attempts needed to trigger limit again
        for _ in range(5):
            client.post("/api/login", json={
                "email": "reset@mail.com", "password": "wrongpass"
            })
        res = client.post("/api/login", json={
            "email": "reset@mail.com", "password": "wrongpass"
        })
        assert res.status_code == 429


class TestTokenSecurity:
    def test_garbage_token(self, client):
        res = client.get("/api/me", headers={"Authorization": "Bearer garbage.token.here"})
        assert res.status_code == 401

    def test_missing_bearer_prefix(self, client):
        res = client.get("/api/me", headers={"Authorization": "some-token"})
        assert res.status_code == 401

    def test_empty_bearer(self, client):
        res = client.get("/api/me", headers={"Authorization": "Bearer "})
        assert res.status_code == 401


class TestSQLInjection:
    def test_sql_injection_email(self, client):
        res = client.post("/api/register", json={
            "name": "Hacker",
            "email": "'; DROP TABLE users;--",
            "password": "pass12345",
        })
        assert res.status_code == 400

        # Verify users table still exists
        row = db.get_user_by_email("anything@test.com")
        assert row is None  # no crash = table intact

    def test_sql_injection_login(self, client):
        res = client.post("/api/login", json={
            "email": "' OR 1=1;--",
            "password": "pass12345",
        })
        assert res.status_code in (400, 401)


class TestAmountValidation:
    def _auth(self, client):
        client.post("/api/register", json={
            "name": "Test", "email": "amt@mail.com", "password": "pass12345"
        })
        res = client.post("/api/login", json={
            "email": "amt@mail.com", "password": "pass12345"
        })
        return {"Authorization": f"Bearer {res.json['token']}"}

    def test_string_amount(self, client):
        headers = self._auth(client)
        res = client.post("/api/deposit", json={"amount": "abc"}, headers=headers)
        assert res.status_code == 400

    def test_zero_amount(self, client):
        headers = self._auth(client)
        res = client.post("/api/deposit", json={"amount": 0}, headers=headers)
        assert res.status_code == 400

    def test_missing_amount(self, client):
        headers = self._auth(client)
        res = client.post("/api/deposit", json={}, headers=headers)
        assert res.status_code == 400


class TestOrderAuthorization:
    def test_pay_other_users_order(self, client):
        # User A registers, funds, creates order
        client.post("/api/register", json={
            "name": "User A", "email": "a@mail.com", "password": "pass12345"
        })
        res = client.post("/api/login", json={
            "email": "a@mail.com", "password": "pass12345"
        })
        headers_a = {"Authorization": f"Bearer {res.json['token']}"}
        client.post("/api/deposit", json={"amount": 10000}, headers=headers_a)

        merchant_id = db.get_all_merchants()[0]["merchant_id"]
        create = client.post("/api/orders", json={
            "merchant_id": merchant_id, "amount": 500, "installments": 2,
        }, headers=headers_a)
        order_id = create.json["order_id"]
        client.post(f"/api/orders/{order_id}/approve", headers=headers_a)

        # User B registers, tries to pay User A's order
        client.post("/api/register", json={
            "name": "User B", "email": "b@mail.com", "password": "pass12345"
        })
        res = client.post("/api/login", json={
            "email": "b@mail.com", "password": "pass12345"
        })
        headers_b = {"Authorization": f"Bearer {res.json['token']}"}

        res = client.post(f"/api/orders/{order_id}/pay", headers=headers_b)
        assert res.status_code == 403