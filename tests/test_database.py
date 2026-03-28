import pytest
from app.database import Database
from app.models import User, Merchant, Order


@pytest.fixture
def db():
    database = Database(":memory:")
    yield database
    database.close()


@pytest.fixture
def saved_user(db):
    user = User("Ali", "ali@example.com", "secret123", balance=5000)
    db.save_user(user)
    return user


@pytest.fixture
def saved_merchant(db):
    merchant = Merchant("ShopX", "shop@example.com", "Retail")
    db.save_merchant(merchant)
    return merchant


class TestUserDB:
    def test_save_and_get_user(self, db, saved_user):
        row = db.get_user(saved_user.user_id)
        assert row["name"] == "Ali"
        assert row["email"] == "ali@example.com"
        assert row["balance"] == 5000
        assert row["is_active"] == 1

    def test_get_user_by_email(self, db, saved_user):
        row = db.get_user_by_email("ali@example.com")
        assert row["user_id"] == saved_user.user_id

    def test_update_user(self, db, saved_user):
        saved_user.deposit(1000)
        db.update_user(saved_user)
        row = db.get_user(saved_user.user_id)
        assert row["balance"] == 6000

    def test_get_nonexistent_user(self, db):
        assert db.get_user("no-such-id") is None


class TestMerchantDB:
    def test_save_and_get_merchant(self, db, saved_merchant):
        row = db.get_merchant(saved_merchant.merchant_id)
        assert row["name"] == "ShopX"
        assert row["category"] == "Retail"

    def test_update_merchant(self, db, saved_merchant):
        saved_merchant.receive_payment(500)
        db.update_merchant(saved_merchant)
        row = db.get_merchant(saved_merchant.merchant_id)
        assert row["balance"] == 500
        assert row["total_transactions"] == 1


class TestOrderDB:
    def test_save_and_get_order(self, db, saved_user, saved_merchant):
        order = Order(saved_user, saved_merchant, 1200, 4)
        db.save_order(order)
        row = db.get_order(order.order_id)
        assert row["amount"] == 1200
        assert row["num_installments"] == 4
        assert row["status"] == "pending"

    def test_get_orders_by_user(self, db, saved_user, saved_merchant):
        o1 = Order(saved_user, saved_merchant, 500, 2)
        o2 = Order(saved_user, saved_merchant, 800, 4)
        db.save_order(o1)
        db.save_order(o2)
        rows = db.get_orders_by_user(saved_user.user_id)
        assert len(rows) == 2

    def test_update_order_status(self, db, saved_user, saved_merchant):
        order = Order(saved_user, saved_merchant, 600, 3)
        db.save_order(order)
        order.approve()
        db.update_order(order)
        row = db.get_order(order.order_id)
        assert row["status"] == "approved"


class TestPaymentDB:
    def test_save_and_get_payment(self, db, saved_user, saved_merchant):
        order = Order(saved_user, saved_merchant, 1000, 2)
        db.save_order(order)
        order.approve()
        payment = order.make_payment()
        db.save_payment(payment)
        rows = db.get_payments_by_order(order.order_id)
        assert len(rows) == 1
        assert rows[0]["amount"] == 500.0
        assert rows[0]["status"] == "completed"
