import base64
import json
import sqlite3
import sys
from datetime import datetime
from http.server import BaseHTTPRequestHandler
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core import analyze_resume, read_resume_bytes


DB_PATH = Path("/tmp/resume_results.db")


def init_database():
    """Create the SQLite results table for serverless analysis records."""
    with sqlite3.connect(DB_PATH) as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS analyses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                resume_name TEXT NOT NULL,
                jd_title TEXT NOT NULL,
                score REAL NOT NULL,
                missing_keywords TEXT NOT NULL,
                suggestions TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )


def save_result(resume_name, jd_title, score, missing_keywords, suggestions):
    """Save one Vercel API analysis result to SQLite in the function instance."""
    init_database()
    with sqlite3.connect(DB_PATH) as connection:
        connection.execute(
            """
            INSERT INTO analyses (
                resume_name,
                jd_title,
                score,
                missing_keywords,
                suggestions,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                resume_name,
                jd_title,
                score,
                ", ".join(missing_keywords),
                " | ".join(suggestions),
                datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC"),
            ),
        )


def json_response(handler, status_code, payload):
    """Write a JSON response from the serverless function."""
    body = json.dumps(payload).encode("utf-8")
    handler.send_response(status_code)
    handler.send_header("Content-Type", "application/json")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


def html_response(handler, include_body=True):
    """Write the main HTML interface from the repository root."""
    body = (ROOT / "index.html").read_bytes()
    handler.send_response(200)
    handler.send_header("Content-Type", "text/html; charset=utf-8")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    if include_body:
        handler.wfile.write(body)


def get_history():
    """Return recent SQLite results from the current function instance."""
    if not DB_PATH.exists():
        return []
    with sqlite3.connect(DB_PATH) as connection:
        connection.row_factory = sqlite3.Row
        rows = connection.execute(
            """
            SELECT resume_name, jd_title, score, missing_keywords, suggestions, created_at
            FROM analyses
            ORDER BY id DESC
            LIMIT 10
            """
        ).fetchall()
    return [dict(row) for row in rows]


class handler(BaseHTTPRequestHandler):
    """Handle resume analyzer API routes for the Vercel deployment."""

    def do_HEAD(self):
        """Return headers for the main HTML page."""
        html_response(self, include_body=False)

    def do_GET(self):
        """Return saved history for API requests or the main HTML page otherwise."""
        if self.path.startswith("/api/history"):
            json_response(self, 200, {"results": get_history()})
            return
        html_response(self)

    def do_POST(self):
        """Accept JSON input, analyze the resume, save it, and return the report."""
        try:
            content_length = int(self.headers.get("Content-Length", "0"))
            request_body = self.rfile.read(content_length)
            payload = json.loads(request_body.decode("utf-8"))
            file_name = payload.get("file_name", "resume.txt")
            jd_title = payload.get("jd_title", "Untitled Role")
            jd_text = payload.get("jd_text", "")
            resume_base64 = payload.get("resume_base64", "")

            if not jd_text.strip() or not resume_base64:
                json_response(self, 400, {"error": "Resume file and job description are required."})
                return

            resume_bytes = base64.b64decode(resume_base64)
            resume_text = read_resume_bytes(file_name, resume_bytes)
            if not resume_text.strip():
                json_response(self, 400, {"error": "Could not extract text from the resume."})
                return

            result = analyze_resume(resume_text, jd_text)
            save_result(
                file_name,
                jd_title,
                result["score"],
                result["missing_keywords"],
                result["suggestions"],
            )
            json_response(self, 200, result)
        except Exception as error:
            json_response(self, 500, {"error": str(error)})
