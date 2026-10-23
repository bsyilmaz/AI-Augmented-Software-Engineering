"""Link Shortener — starter app for Week 5.

A deliberately tiny FastAPI service you will make *agent-native*. Run it, read it,
then use your coding agent (Antigravity by default) plus the tasks in docs/TASKS.md.

Run:
    pip install -r requirements.txt
    uvicorn main:app --reload
Test:
    pytest
"""
import sqlite3
import string
from contextlib import closing
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import RedirectResponse
from pydantic import BaseModel

DB_PATH = Path(__file__).parent / "links.db"
ALPHABET = string.ascii_letters + string.digits

app = FastAPI(title="Link Shortener")


def get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with closing(get_db()) as conn:
        conn.execute(
            """CREATE TABLE IF NOT EXISTS links (
                id   INTEGER PRIMARY KEY AUTOINCREMENT,
                code TEXT UNIQUE,
                url  TEXT NOT NULL
            )"""
        )
        conn.commit()


init_db()


def encode(n: int) -> str:
    """Base62-encode a row id into a short code."""
    base = len(ALPHABET)
    if n == 0:
        return ALPHABET[0]
    chars = []
    while n > 0:
        n, r = divmod(n, base)
        chars.append(ALPHABET[r])
    return "".join(reversed(chars))


UNREACHABLE_ALIASES = {"docs", "redoc", "openapi.json"}


class ShortenRequest(BaseModel):
    url: str
    alias: str | None = None


@app.post("/shorten")
def shorten(req: ShortenRequest):
    if not req.url.startswith(("http://", "https://")):
        raise HTTPException(status_code=400, detail="url must start with http:// or https://")

    if req.alias is not None:
        if not req.alias.strip():
            raise HTTPException(status_code=400, detail="alias must not be empty")
        if "/" in req.alias or req.alias in UNREACHABLE_ALIASES:
            raise HTTPException(status_code=400, detail="alias is not reachable")
        with closing(get_db()) as conn:
            try:
                conn.execute("INSERT INTO links (url, code) VALUES (?, ?)", (req.url, req.alias))
            except sqlite3.IntegrityError:
                raise HTTPException(status_code=409, detail="alias already taken")
            conn.commit()
        return {"code": req.alias, "short_url": f"/{req.alias}"}

    with closing(get_db()) as conn:
        cur = conn.execute("INSERT INTO links (url) VALUES (?)", (req.url,))
        row_id = cur.lastrowid
        base_code = encode(row_id)
        code = base_code
        suffix = 2
        while True:
            try:
                conn.execute("UPDATE links SET code = ? WHERE id = ?", (code, row_id))
                break
            except sqlite3.IntegrityError:
                code = f"{base_code}{suffix}"
                suffix += 1
        conn.commit()
    return {"code": code, "short_url": f"/{code}"}


@app.get("/{code}")
def redirect(code: str):
    with closing(get_db()) as conn:
        row = conn.execute("SELECT url FROM links WHERE code = ?", (code,)).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="unknown code")
    return RedirectResponse(url=row["url"], status_code=307)
