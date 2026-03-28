"""
PayFlow Models - User, Merchant, Order, Payment
"""
from datetime import datetime
import hashlib
import uuid

class User:
    def __init__(self, name, email, password, balance=0):
        self.user_id = str(uuid.uuid4())
        self.name = name
        self.password = hashlib.sha256(password.encode()).hexdigest()
        self.email = email
        self.balance = balance
        self.is_active = True


    def __str__(self):
        return f"{self.name} ({self.email}) - Balance {self.balance}"
    
     
    def deposit(self, amount):
        if not self.is_active:
            raise ValueError("Account is deactivated")
        if amount <= 0:
            raise ValueError("Amount must be positive")
        self.balance += amount
        return self.balance

    def withdraw(self, amount):
        if not self.is_active:
            raise ValueError("Account is deactivated")
        if amount <= 0:
            raise ValueError("Amount must be positive")
        if amount > self.balance:
            raise ValueError("Insufficient balance")
        self.balance -= amount
        return self.balance

    @classmethod
    def from_row(cls, row):
        user = object.__new__(cls)
        user.user_id = row["user_id"]
        user.name = row["name"]
        user.email = row["email"]
        user.password = row["password"]
        user.balance = row["balance"]
        user.is_active = bool(row["is_active"])
        return user

    def deactivate(self):
        self.is_active = False


class Merchant:
    def __init__(self, name , email, category):
        self.merchant_id = str(uuid.uuid4())
        self.name = name
        self.email = email
        self.category = category
        self.is_active = True
        self.balance = 0
        self.total_transactions = 0

    def __str__(self):
        return f"{self.name} ({self.category}) - Transactions: {self.total_transactions}"

    @classmethod
    def from_row(cls, row):
        merchant = object.__new__(cls)
        merchant.merchant_id = row["merchant_id"]
        merchant.name = row["name"]
        merchant.email = row["email"]
        merchant.category = row["category"]
        merchant.balance = row["balance"]
        merchant.total_transactions = row["total_transactions"]
        merchant.is_active = bool(row["is_active"])
        return merchant

    def receive_payment(self, amount):
        if not self.is_active:
            raise ValueError("Merchant is deactivated")
        if amount <= 0:
            raise ValueError("Amount must be positive")
        self.balance += amount
        self.total_transactions += 1
        return self.balance

    def deactivate(self):
        self.is_active = False


class Order:
    VALID_INSTALLMENTS = [2, 3, 4, 6]

    def __init__(self, user, merchant, amount, num_installments):
        if not user.is_active:
            raise ValueError(" User account is deactivated")
        if not merchant.is_active:
            raise ValueError("Merchant is deactivated")
        if amount <= 0:
            raise ValueError("Amount must be positive")
        if num_installments not in self.VALID_INSTALLMENTS:
            raise ValueError("Installments must be 2, 3, 4, or 6")
        

        self.order_id = str(uuid.uuid4())
        self.user = user
        self.merchant = merchant
        self.amount = amount
        self.num_installments = num_installments
        self.installment_amount = round(amount / num_installments, 2)
        self.status = "pending"
        self.payments = []
        self.created_at = datetime.now()

    def __str__(self):
        return f"Order {self.order_id}: {self.amount} SAR ({self.status})"

    def approve(self):
        if self.status != "pending":
            raise ValueError(f"Cannot approve order with status: {self.status}")
        self.status = "approved"

    def reject(self, reason=""):
        if self.status != "pending":
            raise ValueError(f"Cannot reject order with status: {self.status}")
        self.status = "rejected"
        self.reject_reason = reason

    def make_payment(self):
        if self.status not in ["approved", "active"]:
            raise ValueError(f"Cannot pay order with status: {self.status}")
        if len(self.payments) >= self.num_installments:
            raise ValueError("All installments already paid")

        is_last = len(self.payments) == self.num_installments - 1
        amount = self.get_remaining() if is_last else self.installment_amount
        payment = Payment(self, amount)
        self.user.withdraw(amount)
        self.merchant.receive_payment(amount)
        payment.status = "completed"
        self.payments.append(payment)
        self.status = "active"

        if len(self.payments) == self.num_installments:
            self.status = "completed"

        return payment

    def cancel(self):
        if self.status not in ["approved", "active"]:
            raise ValueError(f"Cannot cancel order with status: {self.status}")
        self.status = "cancelled"

    def get_remaining(self):
        paid = sum(p.amount for p in self.payments)
        return round(self.amount - paid, 2)


class Payment:
    def __init__(self, order , amount):
        self.payment_id = str(uuid.uuid4())
        self.order = order 
        self.amount = amount
        self.status = "pending"
        self.created_at = datetime.now()

    def __str__(self):
        return f"Payment {self.payment_id}: {self.amount} SAR ({self.status})"