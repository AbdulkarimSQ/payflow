"""
PayFlow Validators — Input validation for all endpoints
"""

import re


def validate_email(email):
    if not email or not isinstance(email, str):
        return False, "Email is required"
    if len(email) > 254:
        return False, "Email is too long"
    pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    if not re.match(pattern, email):
        return False, "Invalid email format"
    return True, ""


def validate_password(password):
    if not password or not isinstance(password, str):
        return False, "Password is required"
    if len(password) < 8:
        return False, "Password must be at least 8 characters"
    if len(password) > 128:
        return False, "Password is too long"
    return True, ""


def validate_name(name):
    if not name or not isinstance(name, str):
        return False, "Name is required"
    if len(name.strip()) == 0:
        return False, "Name cannot be empty"
    if len(name) > 100:
        return False, "Name is too long"
    return True, ""


def validate_amount(amount, max_amount=50000):
    if not isinstance(amount, (int, float)):
        return False, "Amount must be a number"
    if amount <= 0:
        return False, "Amount must be positive"
    if amount > max_amount:
        return False, f"Amount cannot exceed {max_amount}"
    return True, ""
