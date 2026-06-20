import sqlite3
from datetime import datetime
from pathlib import Path

import streamlit as st

from core import analyze_resume, read_resume_bytes


DB_PATH = Path(__file__).with_name("resume_results.db")


def init_database():
    """Create the SQLite results table if it does not already exist."""
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
    """Store one resume analysis result in the SQLite database."""
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
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            ),
        )


def fetch_results():
    """Return saved analysis history ordered from newest to oldest."""
    with sqlite3.connect(DB_PATH) as connection:
        connection.row_factory = sqlite3.Row
        rows = connection.execute(
            """
            SELECT resume_name, jd_title, score, missing_keywords, suggestions, created_at
            FROM analyses
            ORDER BY id DESC
            """
        ).fetchall()
    return rows


def read_resume(uploaded_file):
    """Route the uploaded resume to the correct text extraction function."""
    return read_resume_bytes(uploaded_file.name, uploaded_file.getvalue())


def render_report(result):
    """Display a structured report for the latest resume analysis."""
    st.subheader("Structured Report")
    st.metric("Match Score", f"{result['score']}%")
    st.write("**Job Description Keywords**")
    st.write(", ".join(result["jd_keywords"]) or "No keywords found.")
    st.write("**Resume Keywords**")
    st.write(", ".join(result["resume_keywords"]) or "No keywords found.")
    st.write("**Matched Keywords**")
    st.write(", ".join(result["matched_keywords"]) or "No matched keywords found.")
    st.write("**Missing Keywords**")
    st.write(", ".join(result["missing_keywords"]) or "No missing keywords found.")
    st.write("**Skill Gaps**")
    st.write(", ".join(result["skill_gaps"]) or "No obvious skill gaps found.")
    st.write("**Suggestions**")
    for suggestion in result["suggestions"]:
        st.write(f"- {suggestion}")


def render_history():
    """Display previous resume analyses from the SQLite database."""
    st.subheader("Saved Results")
    rows = fetch_results()
    if not rows:
        st.info("No saved results yet.")
        return
    for row in rows:
        with st.expander(f"{row['resume_name']} | {row['jd_title']} | {row['score']}%"):
            st.write(f"**Timestamp:** {row['created_at']}")
            st.write(f"**Missing Keywords:** {row['missing_keywords'] or 'None'}")
            st.write(f"**Suggestions:** {row['suggestions'] or 'None'}")


def main():
    """Render the Streamlit web interface and coordinate user actions."""
    init_database()
    st.set_page_config(page_title="Resume Analyzer", page_icon="RA", layout="wide")
    st.title("Resume Analyzer")
    st.write("Upload a TXT or PDF resume, paste a job description, and review the match report.")

    left_column, right_column = st.columns([2, 1])
    with left_column:
        resume_file = st.file_uploader("Resume file", type=["txt", "pdf"])
        jd_title = st.text_input("Job description title", value="Untitled Role")
        jd_text = st.text_area("Job description", height=260)
        analyze_button = st.button("Analyze Resume", type="primary")

    with right_column:
        st.subheader("What This Checks")
        st.write("- Keyword overlap")
        st.write("- Missing terms")
        st.write("- Likely skill gaps")
        st.write("- Resume improvement suggestions")

    if analyze_button:
        if not resume_file:
            st.error("Please upload a resume file.")
            return
        if not jd_text.strip():
            st.error("Please enter a job description.")
            return

        resume_text = read_resume(resume_file)
        if not resume_text.strip():
            st.error("Could not extract text from the uploaded resume.")
            return

        result = analyze_resume(resume_text, jd_text)
        save_result(
            resume_file.name,
            jd_title.strip() or "Untitled Role",
            result["score"],
            result["missing_keywords"],
            result["suggestions"],
        )
        render_report(result)

    render_history()


if __name__ == "__main__":
    main()
