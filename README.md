# Resume Analyzer Tool

A Streamlit web app that compares a resume against a job description, calculates a match score, highlights missing keywords and skill gaps, and stores analysis history in SQLite.

## Features

- Upload `.txt` or `.pdf` resumes
- Paste a job description and title
- Lowercase, tokenize, and remove stopwords during preprocessing
- Extract top keywords from the resume and job description
- Calculate a match score from `0-100%`
- Show missing keywords and likely skill gaps
- Generate suggestions for improving the resume
- Save results to `resume_results.db`
- View previous analyses in the app

## Setup

```bash
cd /Users/uddhavbhardwaj17/Documents/Python/resume_analyzer_tool
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

## Vercel Deployment

This repository also includes a Vercel-compatible static frontend and Python serverless API:

- `index.html` is the public Vercel interface.
- `api/analyze.py` analyzes uploaded resumes.
- `api/history.py` exposes recent SQLite records from the current serverless function instance.
- `core.py` shares the preprocessing, keyword extraction, scoring, and suggestion logic with Streamlit.

Deploy with:

```bash
vercel --prod
```

## Notes

The PDF text extractor uses only Python standard-library modules so the project stays within the requested dependency list. It works best with text-based PDFs. Scanned image PDFs need OCR, which would require extra libraries or services.
