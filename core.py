import re
import zlib
from collections import Counter

try:
    from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS
except ImportError:
    ENGLISH_STOP_WORDS = {
        "a",
        "an",
        "and",
        "are",
        "as",
        "at",
        "be",
        "by",
        "for",
        "from",
        "has",
        "have",
        "in",
        "is",
        "it",
        "of",
        "on",
        "or",
        "that",
        "the",
        "to",
        "with",
        "you",
        "your",
    }


MAX_KEYWORDS = 30


SKILL_HINTS = {
    "python",
    "sql",
    "sqlite",
    "excel",
    "tableau",
    "powerbi",
    "aws",
    "azure",
    "gcp",
    "docker",
    "kubernetes",
    "django",
    "flask",
    "streamlit",
    "react",
    "javascript",
    "typescript",
    "html",
    "css",
    "machine",
    "learning",
    "nlp",
    "pandas",
    "numpy",
    "sklearn",
    "tensorflow",
    "pytorch",
    "communication",
    "leadership",
    "analytics",
    "testing",
    "git",
    "linux",
}


def decode_text_bytes(raw_bytes):
    """Decode TXT file bytes into plain text."""
    return raw_bytes.decode("utf-8", errors="ignore")


def clean_pdf_literal(value):
    """Clean a PDF text literal by removing escape codes and excess spacing."""
    value = value.replace(r"\n", " ").replace(r"\r", " ").replace(r"\t", " ")
    value = re.sub(r"\\[()\\]", lambda match: match.group(0)[1], value)
    value = re.sub(r"\\[0-7]{1,3}", " ", value)
    return value.strip()


def extract_text_from_pdf_stream(stream_bytes):
    """Extract readable text fragments from one decoded PDF stream."""
    text_parts = []
    stream_text = stream_bytes.decode("latin-1", errors="ignore")
    for literal in re.findall(r"\((.*?)\)\s*Tj", stream_text, flags=re.DOTALL):
        cleaned = clean_pdf_literal(literal)
        if cleaned:
            text_parts.append(cleaned)
    for array_body in re.findall(r"\[(.*?)\]\s*TJ", stream_text, flags=re.DOTALL):
        literals = re.findall(r"\((.*?)\)", array_body, flags=re.DOTALL)
        cleaned_literals = [clean_pdf_literal(item) for item in literals]
        joined = " ".join(item for item in cleaned_literals if item)
        if joined:
            text_parts.append(joined)
    return " ".join(text_parts)


def decode_pdf_bytes(pdf_bytes):
    """Read a simple text-based PDF using only the Python standard library."""
    text_parts = []
    for match in re.finditer(rb"stream\r?\n(.*?)\r?\nendstream", pdf_bytes, flags=re.DOTALL):
        stream_bytes = match.group(1)
        try:
            stream_bytes = zlib.decompress(stream_bytes)
        except zlib.error:
            pass
        stream_text = extract_text_from_pdf_stream(stream_bytes)
        if stream_text:
            text_parts.append(stream_text)
    if text_parts:
        return " ".join(text_parts)
    return pdf_bytes.decode("latin-1", errors="ignore")


def read_resume_bytes(file_name, raw_bytes):
    """Route resume bytes to the correct text extraction function."""
    lower_name = file_name.lower()
    if lower_name.endswith(".txt"):
        return decode_text_bytes(raw_bytes)
    if lower_name.endswith(".pdf"):
        return decode_pdf_bytes(raw_bytes)
    return ""


def tokenize(text):
    """Convert text to lowercase word tokens and remove common stopwords."""
    lowercase_text = text.lower()
    raw_tokens = re.findall(r"[a-z][a-z0-9+#.-]*", lowercase_text)
    return [
        token
        for token in raw_tokens
        if token not in ENGLISH_STOP_WORDS and len(token) > 1
    ]


def extract_keywords(tokens, limit=MAX_KEYWORDS):
    """Return the most frequent meaningful tokens as keywords."""
    keyword_counts = Counter(tokens)
    return [word for word, _count in keyword_counts.most_common(limit)]


def calculate_match_score(resume_keywords, jd_keywords):
    """Calculate a 0-100 percentage score based on JD keyword coverage."""
    if not jd_keywords:
        return 0.0
    matched_keywords = set(resume_keywords).intersection(jd_keywords)
    score = (len(matched_keywords) / len(set(jd_keywords))) * 100
    return round(score, 2)


def find_missing_keywords(resume_keywords, jd_keywords):
    """Find JD keywords that do not appear in the resume keywords."""
    return sorted(set(jd_keywords).difference(resume_keywords))


def identify_skill_gaps(missing_keywords):
    """Filter missing keywords down to likely skills and technical terms."""
    skill_gaps = []
    for keyword in missing_keywords:
        if keyword in SKILL_HINTS or "+" in keyword or "." in keyword:
            skill_gaps.append(keyword)
    return skill_gaps


def build_suggestions(score, missing_keywords, skill_gaps):
    """Create practical resume improvement suggestions from the analysis."""
    suggestions = []
    if score < 50:
        suggestions.append("Add more role-specific keywords from the job description.")
    elif score < 75:
        suggestions.append("Strengthen the resume by adding missing high-value skills.")
    else:
        suggestions.append("The resume is well aligned; refine wording for the top missing terms.")
    if skill_gaps:
        suggestions.append(f"Add evidence for these skills: {', '.join(skill_gaps[:8])}.")
    if missing_keywords:
        suggestions.append("Use missing keywords naturally in experience, projects, or summary sections.")
    suggestions.append("Quantify achievements with metrics where possible.")
    return suggestions


def analyze_resume(resume_text, jd_text):
    """Run preprocessing, keyword extraction, scoring, and report preparation."""
    resume_tokens = tokenize(resume_text)
    jd_tokens = tokenize(jd_text)
    resume_keywords = extract_keywords(resume_tokens)
    jd_keywords = extract_keywords(jd_tokens)
    score = calculate_match_score(resume_keywords, jd_keywords)
    missing_keywords = find_missing_keywords(resume_keywords, jd_keywords)
    skill_gaps = identify_skill_gaps(missing_keywords)
    suggestions = build_suggestions(score, missing_keywords, skill_gaps)
    return {
        "score": score,
        "resume_keywords": resume_keywords,
        "jd_keywords": jd_keywords,
        "missing_keywords": missing_keywords,
        "skill_gaps": skill_gaps,
        "suggestions": suggestions,
    }
