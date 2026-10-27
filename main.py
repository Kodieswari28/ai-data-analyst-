import os
import sqlite3

from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI, HTTPException  # noqa: E402
from fastapi.responses import FileResponse  # noqa: E402
from pydantic import BaseModel, Field  # noqa: E402

import db, llm, safety  # noqa: E402

app = FastAPI(title="AI Data Analyst", description="Ask your database questions in plain English.")
db.init_db()
HERE = os.path.dirname(os.path.abspath(__file__))


class Ask(BaseModel):
    question: str = Field(min_length=3, max_length=300)
    history: list[str] = []


@app.get("/api/schema")
def schema():
    return db.get_schema_dict()


@app.post("/api/ask")
def ask(body: Ask):
    schema_text = db.get_schema_text()
    try:
        out = llm.generate_sql(body.question, schema_text, body.history)
    except Exception as e:
        detail = str(e)
        resp = getattr(e, "response", None)
        if resp is not None:
            try:
                detail = f"{resp.status_code}: {resp.json()['error']['message']}"
            except Exception:
                detail = f"{resp.status_code}: {resp.text[:150]}"
        print("LLM ERROR:", repr(e), detail, flush=True)
        raise HTTPException(502, f"AI service error ({detail[:180]})")

    if not out.get("sql"):
        return {"sql": "", "columns": [], "rows": [], "chart": "none",
                "explanation": out.get("explanation", "I could not answer that."), "mode": out.get("mode")}

    sql = out["sql"]
    for attempt in range(2):  # second attempt lets the AI repair its own SQL error
        try:
            clean = safety.validate_sql(sql)
            cols, rows = safety.run_readonly(db.DB_PATH, clean)
            return {"sql": clean, "columns": cols, "rows": rows, "chart": out.get("chart", "none"),
                    "explanation": out.get("explanation", ""), "mode": out.get("mode")}
        except safety.UnsafeSQL as e:
            raise HTTPException(400, f"Blocked for safety: {e}")
        except sqlite3.Error as e:
            if attempt == 1 or out.get("mode") == "demo":
                raise HTTPException(400, f"The query failed: {e}")
            out = llm.generate_sql(body.question, schema_text, body.history, error=str(e), bad_sql=sql)
            sql = out.get("sql", "")


@app.get("/")
def index():
    return FileResponse(os.path.join(HERE, "index.html"))

