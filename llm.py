"""Turns an English question into SQL using the Gemini API.

If GEMINI_API_KEY is missing, a small keyword-based demo mode runs so the
app still works for a first test.
"""
import json
import os

MODEL = os.getenv("GEMINI_MODEL", "gemini-3.8-flash")

SYSTEM_RULES = """You are a careful data analyst writing SQLite queries.
Rules:
- Use ONLY the tables and columns in the schema.
- Write exactly one SELECT statement. Never modify data.
- Revenue = orders.quantity * products.price. Exclude orders with status 'cancelled' or 'returned' from revenue unless asked.
- Dates are ISO text (YYYY-MM-DD). Use strftime for month/year grouping.
- Give columns readable aliases.
- If the question cannot be answered from the schema, return an empty "sql" and explain why in "explanation".
Reply as JSON: {"sql": "...", "explanation": "one or two plain sentences", "chart": "bar|line|pie|none"}
Use "line" for time series, "pie" for share of a total with few categories, "bar" for comparisons, "none" for single values or long text tables."""

DEMO = [
    (("top", "product"), "SELECT p.name AS product, SUM(o.quantity * p.price) AS revenue FROM orders o JOIN products p ON p.id = o.product_id WHERE o.status NOT IN ('cancelled','returned') GROUP BY p.name ORDER BY revenue DESC LIMIT 5",
     "Top 5 products by revenue (cancelled and returned orders excluded).", "bar"),
    (("month",), "SELECT strftime('%Y-%m', o.order_date) AS month, SUM(o.quantity * p.price) AS revenue FROM orders o JOIN products p ON p.id = o.product_id WHERE o.status NOT IN ('cancelled','returned') GROUP BY month ORDER BY month",
     "Monthly revenue over time.", "line"),
    (("city",), "SELECT c.city, COUNT(*) AS orders FROM orders o JOIN customers c ON c.id = o.customer_id GROUP BY c.city ORDER BY orders DESC",
     "Number of orders per customer city.", "bar"),
    (("category",), "SELECT p.category, SUM(o.quantity * p.price) AS revenue FROM orders o JOIN products p ON p.id = o.product_id WHERE o.status NOT IN ('cancelled','returned') GROUP BY p.category ORDER BY revenue DESC",
     "Revenue share by product category.", "pie"),
]


def _demo(question: str) -> dict:
    q = question.lower()
    for keys, sql, expl, chart in DEMO:
        if all(k in q for k in keys):
            return {"sql": sql, "explanation": expl, "chart": chart, "mode": "demo"}
    return {"sql": "", "mode": "demo",
            "explanation": "Demo mode understands: top products, revenue by month, orders by city, revenue by category. Add GEMINI_API_KEY to ask anything.",
            "chart": "none"}


def generate_sql(question: str, schema: str, history=None, error: str = "", bad_sql: str = "") -> dict:
    key = os.getenv("GEMINI_API_KEY", "").strip()
    if not key:
        return _demo(question)

    import httpx  # imported here so demo mode and tests need no extra install

    prompt = f"Schema:\n{schema}\n\n"
    if history:
        prompt += "Earlier questions in this chat:\n" + "\n".join(f"- {h}" for h in history[-4:]) + "\n\n"
    prompt += f"Question: {question}\n"
    if error:
        prompt += f"\nYour previous SQL failed.\nSQL: {bad_sql}\nError: {error}\nFix it.\n"

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent"
    body = {
        "systemInstruction": {"parts": [{"text": SYSTEM_RULES}]},
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0, "responseMimeType": "application/json"},
    }
    r = httpx.post(url, headers={"x-goog-api-key": key}, json=body, timeout=40)
    r.raise_for_status()
    text = r.json()["candidates"][0]["content"]["parts"][0]["text"]
    data = json.loads(text)
    data.setdefault("chart", "none")
    data["mode"] = "gemini"
    return data
