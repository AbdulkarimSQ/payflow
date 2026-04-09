# 💳 PayFlow — BNPL Payment System

![Tests](https://github.com/AbdulkarimSQ/payflow/actions/workflows/tests.yml/badge.svg)

A Buy Now Pay Later (BNPL) payment system built with Flask, featuring installment management, JWT authentication, and comprehensive test coverage.

## Features

- User registration and JWT authentication
- Installment-based payment processing (2, 3, 4, or 6 payments)
- Merchant management
- Input validation and error handling
- Rate limiting for brute force protection
- Password hashing (SHA-256)
- 73 automated tests (unit, integration, API, security)

## Tech Stack

- Python 3.12 / Flask
- SQLite / JWT (PyJWT)
- pytest / Docker / GitHub Actions

## Quick Start

```bash
git clone https://github.com/AbdulkarimSQ/payflow.git
cd payflow
pip install -r requirements.txt
python -m app.routes
```

## Run Tests

```bash
pytest tests/ -v
```

## API Endpoints

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| POST | /api/ster | Register new user | No |
| POST | /api/login | Login → JWT token | No |
| GET | /api/me | Get my profile | Yes |
| POST | /api/deposit | Deposit funds | Yes |
| GET | /api/merchants | List merchants | Yes |
| POST | /api/orders | Create order | Yes |
| GET | /api/orders | List my orders | Yes |
| POST | /api/orders/:id/approve | Approve order | Yes |
| POST | /api/orders/:id/pay | Pay installment | Yes |
| GET | /api/health | Health check | No |

## Testing
tests/test_models.py    — 18 unit tests
tests/test_database.py  — 10 integration tests
tests/test_api.py       — 27 API integration tests
tests/test_security.py  — 17 security tests
Total: 73 tests
## Security

- JWT authentication with 24h token expiry
- Password hashing (SHA-256)
- Input validation (email, password, amounts)
- Rate limiting (5 attempts / 15 min)
- SQL injection protection (parameterized queries)
- Safe error messages (no info leakage)

## Project Structure
payflow/
├── app/
│   ├── models.py          # User, Merchant, Order, Payment
│   ├── database.py        # SQLite CRUD operations
│   ├── auth.py            # JWT token create/verify
│   ├── routes.py          # Flask API endpoints
│   ├── validators.py      # Input validation
│   └── rate_limiter.py    # Brute force protection
├── tests/
│   ├── test_models.py     # Unit tests
│   ├── test_database.py   # DB integration tests
│   ├── test_api.py        # API integration tests
│   └── test_security.py   # Security tests
├── Dockerfile
├── .github/workflows/tests.yml
└── requirements.txt
## Author

**Abdulkarim Alqahtani** — [GitHub](https://github.com/AbdulkarimSQ)
