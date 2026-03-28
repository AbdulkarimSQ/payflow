"""
PayFlow Auth — JWT token creation and verification
"""

import os
import jwt
import datetime
from functools import wraps
from flask import request, jsonify

SECRET_KEY = os.environ.get("PAYFLOW_SECRET_KEY", "payflow-dev-only-key")

def create_token(user_id):
    now = datetime.datetime.now(datetime.timezone.utc)
    payload = {
        "user_id": user_id,
        "iat": now,
        "exp": now + datetime.timedelta(hours=24),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm="HS256")

def verify_token(token):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        return payload["user_id"]
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get("Authorization")
        if not token or not token.startswith("Bearer "):
            return jsonify({"error": "Token missing"}), 401

        token = token[7:]
        user_id = verify_token(token)
        if not user_id:
            return jsonify({"error": "Invalid token"}), 401

        return f(user_id, *args, **kwargs)
    return decorated