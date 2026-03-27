
import pytest
from app.models import Payment, User, Merchant, Order

class TestUser:
    def test_create_user(self, sample_user):
        assert sample_user.name == "Test User"
        assert sample_user.email == "testuser@example.com"
        assert sample_user.password == "testpass"
        assert sample_user.balance == 5000
        assert sample_user.is_active is True
        assert isinstance(sample_user.user_id, str)
        assert sample_user.orders == []

    def test_deposit(self, sample_user):
        result = sample_user.deposit(1000)
        assert result == 6000 
        assert sample_user.balance == 6000


    def test_withdraw(self, sample_user):
            result = sample_user.withdraw(2000)
            assert result == 3000

    def test_withdraw_insufficient(self, poor_user):
        with pytest.raises(ValueError):
            poor_user.withdraw(500)

    def test_negative_deposit(self, sample_user):
        with pytest.raises(ValueError):
            sample_user.deposit(-100)

    def test_deactivated_user_deposit(self, sample_user):
        sample_user.deactivate()
        with pytest.raises(ValueError):
            sample_user.deposit(100)


class TestMerchant:
    def test_create_merchant(self, sample_merchant):
        assert sample_merchant.name == "Test Merchant"
        assert sample_merchant.email == "merchant@example.com"
        assert sample_merchant.is_active is True
        assert sample_merchant.balance == 0
        assert sample_merchant.total_sales == 0

    def test_recive_payment(self, sample_merchant):
        result = sample_merchant.receive_payment(500)
        assert result == 500
        assert sample_merchant.total_sales == 1

    def test_deactiveted_merchant(self, sample_merchant):
        sample_merchant.deactivate()
        with pytest.raises(ValueError):
            sample_merchant.receive_payment(100)


class TestOrder:
    def test_create_order(self, sample_order):
        assert sample_order.amount == 1200
        assert sample_order.installment_amount == 300.0
        assert sample_order.status == "pending"

    def test_approve_order(self, sample_order):
        sample_order.approve()
        assert sample_order.status == "approved"

    def test_reject_order(self, sample_order):
        sample_order.reject("High risk")
        assert sample_order.status == "rejected"

    def test_make_payment(self, sample_order):
        sample_order.approve()
        payment = sample_order.make_payment()
        assert payment.status == "completed"
        assert sample_order.user.balance == 4700.0
        assert sample_order.get_remaining() == 900
        

    def test_full_payment_flow(self, sample_order):
        sample_order.approve()
        for _ in range(4):
            sample_order.make_payment()
        assert sample_order.status == "completed"
        assert sample_order.get_remaining()== 0

    def test_double_approve(self , sample_order):
        sample_order.approve()
        with pytest.raises(ValueError):
            sample_order.approve()

    def test_pay_rejected_order(self, sample_order):
        sample_order.reject("Fraud")
        with pytest.raises(ValueError):
            sample_order.make_payment()