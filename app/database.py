"""
PayFlow Database — SQLite connection and table creation
"""
import sqlite3


class Database:
    def __init__(self, db_path="payflow.db"):
        self.db_path = db_path
        self.connection = sqlite3.connect(db_path, check_same_thread=False)
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("PRAGMA foreign_keys = ON")
        self._create_tables()

    def _create_tables(self):
        self.connection.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                user_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                balance REAL DEFAULT 0,
                is_active INTEGER DEFAULT 1
            );

            CREATE TABLE IF NOT EXISTS merchants (
                merchant_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                category TEXT NOT NULL,
                balance REAL DEFAULT 0,
                total_transactions INTEGER DEFAULT 0,
                is_active INTEGER DEFAULT 1
            );

            CREATE TABLE IF NOT EXISTS orders (
                order_id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                merchant_id TEXT NOT NULL,
                amount REAL NOT NULL,
                num_installments INTEGER NOT NULL,
                installment_amount REAL NOT NULL,
                status TEXT DEFAULT 'pending',
                created_at TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(user_id),
                FOREIGN KEY (merchant_id) REFERENCES merchants(merchant_id)
            );

            CREATE TABLE IF NOT EXISTS payments (
                payment_id TEXT PRIMARY KEY,
                order_id TEXT NOT NULL,
                amount REAL NOT NULL,
                status TEXT DEFAULT 'pending',
                created_at TEXT NOT NULL,
                FOREIGN KEY (order_id) REFERENCES orders(order_id)
            );
        """)
        self.connection.commit()

    # ── Users ──

    def save_user(self, user):
        self.connection.execute(
            "INSERT INTO users (user_id, name, email, password, balance, is_active) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (user.user_id, user.name, user.email, user.password,
             user.balance, int(user.is_active)),
        )
        self.connection.commit()

    def get_user(self, user_id):
        return self.connection.execute(
            "SELECT * FROM users WHERE user_id = ?", (user_id,)
        ).fetchone()

    def get_user_by_email(self, email):
        return self.connection.execute(
            "SELECT * FROM users WHERE email = ?", (email,)
        ).fetchone()

    def update_user(self, user):
        self.connection.execute(
            "UPDATE users SET name=?, email=?, password=?, balance=?, is_active=? "
            "WHERE user_id=?",
            (user.name, user.email, user.password, user.balance,
             int(user.is_active), user.user_id),
        )
        self.connection.commit()

    # ── Merchants ──

    def save_merchant(self, merchant):
        self.connection.execute(
            "INSERT INTO merchants (merchant_id, name, email, category, balance, total_transactions, is_active) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (merchant.merchant_id, merchant.name, merchant.email,
             merchant.category, merchant.balance, merchant.total_transactions,
             int(merchant.is_active)),
        )
        self.connection.commit()

    def get_merchant(self, merchant_id):
        return self.connection.execute(
            "SELECT * FROM merchants WHERE merchant_id = ?", (merchant_id,)
        ).fetchone()

    def get_all_merchants(self):
        return self.connection.execute(
            "SELECT * FROM merchants WHERE is_active = 1"
        ).fetchall()

    def update_merchant(self, merchant):
        self.connection.execute(
            "UPDATE merchants SET name=?, email=?, category=?, balance=?, "
            "total_transactions=?, is_active=? WHERE merchant_id=?",
            (merchant.name, merchant.email, merchant.category,
             merchant.balance, merchant.total_transactions,
             int(merchant.is_active), merchant.merchant_id),
        )
        self.connection.commit()

    # ── Orders ──

    def save_order(self, order):
        self.connection.execute(
            "INSERT INTO orders (order_id, user_id, merchant_id, amount, "
            "num_installments, installment_amount, status, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (order.order_id, order.user.user_id, order.merchant.merchant_id,
             order.amount, order.num_installments, order.installment_amount,
             order.status, order.created_at.isoformat()),
        )
        self.connection.commit()

    def get_order(self, order_id):
        return self.connection.execute(
            "SELECT * FROM orders WHERE order_id = ?", (order_id,)
        ).fetchone()

    def get_orders_by_user(self, user_id):
        return self.connection.execute(
            "SELECT * FROM orders WHERE user_id = ?", (user_id,)
        ).fetchall()

    def update_order(self, order):
        self.connection.execute(
            "UPDATE orders SET status=? WHERE order_id=?",
            (order.status, order.order_id),
        )
        self.connection.commit()

    # ── Payments ──

    def save_payment(self, payment):
        self.connection.execute(
            "INSERT INTO payments (payment_id, order_id, amount, status, created_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (payment.payment_id, payment.order.order_id, payment.amount,
             payment.status, payment.created_at.isoformat()),
        )
        self.connection.commit()

    def get_payments_by_order(self, order_id):
        return self.connection.execute(
            "SELECT * FROM payments WHERE order_id = ?", (order_id,)
        ).fetchall()

    # ── Cleanup ──

    def close(self):
        self.connection.close()
