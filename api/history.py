import json
import sqlite3
from http.server import BaseHTTPRequestHandler
from pathlib import Path

DB_PATH = Path("/tmp/resume_results.db")


def response(handler, status_code, payload):
    """Write a JSON response from the serverless function."""
    body = json.dumps(payload).encode("utf-8")
    handler.send_response(status_code)
    handler.send_header("Content-Type", "application/json")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


class handler(BaseHTTPRequestHandler):
    """Handle saved result history requests for the Vercel deployment."""

    def do_GET(self):
        """Return recent SQLite results from the current function instance."""
        if not DB_PATH.exists():
            response(self, 200, {"results": []})
            return
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
        response(self, 200, {"results": [dict(row) for row in rows]})
