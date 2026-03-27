import pytest
from app.models import User, Merchant, Order

@pytest.fixture
def sample_user():
    return User(name="Test User", email="testuser@example.com", password="testpass", balance=5000)

@pytest.fixture
def poor_user():
    return User(name="Poor User", email="pooruser@example.com", password="testpass", balance=100)

@pytest.fixture
def sample_merchant():
    return Merchant(name="Test Merchant", email="merchant@example.com", category="Retail")

@pytest.fixture
def sample_order(sample_user, sample_merchant):
    return Order(sample_user, sample_merchant, 1200, 4)
