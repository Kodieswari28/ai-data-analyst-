"""Sample e-commerce database + schema helpers."""
import os
import random
import sqlite3
from datetime import date, timedelta

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "shop.db")

CITIES = ["Chennai", "Coimbatore", "Madurai", "Thanjavur", "Trichy", "Salem", "Erode", "Tirunelveli"]
FIRST = ["Arun", "Divya", "Karthik", "Meena", "Suresh", "Priya", "Vijay", "Lakshmi", "Ravi", "Anitha",
         "Manoj", "Kavya", "Hari", "Nithya", "Sanjay", "Deepa", "Bala", "Swathi", "Gokul", "Revathi"]
LAST = ["Kumar", "Raj", "Sundar", "Devi", "Mohan", "Selvam", "Pandian", "Natarajan"]
PRODUCTS = [
    ("Wireless Earbuds", "Electronics", 1999), ("Smart Watch", "Electronics", 3499),
    ("Power Bank 20000mAh", "Electronics", 1499), ("Bluetooth Speaker", "Electronics", 2299),
    ("Cotton Kurta", "Fashion", 899), ("Denim Jeans", "Fashion", 1599), ("Running Shoes", "Fashion", 2799),
    ("Backpack", "Fashion", 1199), ("Mixer Grinder", "Home", 3299), ("Non-stick Cookware Set", "Home", 2199),
    ("LED Desk Lamp", "Home", 699), ("Yoga Mat", "Fitness", 799), ("Dumbbell Set", "Fitness", 2499),
    ("Python Crash Course", "Books", 549), ("Atomic Habits", "Books", 399),
]
STATUSES = ["delivered"] * 8 + ["shipped", "cancelled", "returned"]

SCHEMA_SQL = """
CREATE TABLE customers (id INTEGER PRIMARY KEY, name TEXT, city TEXT, signup_date TEXT);
CREATE TABLE products (id INTEGER PRIMARY KEY, name TEXT, category TEXT, price INTEGER);
CREATE TABLE orders (
  id INTEGER PRIMARY KEY, customer_id INTEGER REFERENCES customers(id),
  product_id INTEGER REFERENCES products(id), quantity INTEGER,
  order_date TEXT, status TEXT
);
"""


def init_db(path: str = DB_PATH, force: bool = False) -> None:
    if os.path.exists(path):
        if not force:
            return
        os.remove(path)
    rnd = random.Random(42)
    con = sqlite3.connect(path)
    con.executescript(SCHEMA_SQL)
    start = date(2025, 1, 1)
    customers = []
    for i in range(1, 121):
        signup = start + timedelta(days=rnd.randint(0, 600))
        customers.append((i, f"{rnd.choice(FIRST)} {rnd.choice(LAST)}", rnd.choice(CITIES), signup.isoformat()))
    con.executemany("INSERT INTO customers VALUES (?,?,?,?)", customers)
    con.executemany("INSERT INTO products VALUES (?,?,?,?)", [(i + 1, *p) for i, p in enumerate(PRODUCTS)])
    orders = []
    for i in range(1, 1501):
        d = start + timedelta(days=rnd.randint(30, 640))
        orders.append((i, rnd.randint(1, 120), rnd.randint(1, len(PRODUCTS)), rnd.randint(1, 3),
                       d.isoformat(), rnd.choice(STATUSES)))
    con.executemany("INSERT INTO orders VALUES (?,?,?,?,?,?)", orders)
    con.commit()
    con.close()


def get_schema_text(path: str = DB_PATH) -> str:
    """Schema as plain text for the LLM prompt."""
    con = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    rows = con.execute("SELECT sql FROM sqlite_master WHERE type='table' ORDER BY name").fetchall()
    con.close()
    return "\n".join(r[0].strip() for r in rows)


def get_schema_dict(path: str = DB_PATH) -> dict:
    con = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    tables = [r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
    out = {t: [c[1] for c in con.execute(f"PRAGMA table_info({t})")] for t in tables}
    con.close()
    return out
