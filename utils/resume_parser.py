"""
resume_parser.py - Resume PDF Parser

Extracts structured information from a resume PDF so the ML model
can make a real prediction based on the actual resume content.

WHAT IT EXTRACTS:
  - Raw full text          (for TF-IDF vectorization)
  - Skills                 (matched against a known skills list)
  - Years of experience    (detected from date ranges in the text)
  - Education level        (B.Sc / B.Tech / MBA / M.Tech / PhD)
  - Certifications         (matched against known cert names)
  - Projects count         (counted from project section keywords)

HOW IT WORKS
    1.pdfplumber reads the PDF and extracts all raw text
    2.Regex patterns scan the text for dates, degree keywords, etc
    3.A skills dictionary matches known tech skills in the text
    4.Results are returned as a clean dict ready for predict_single()

INSTALL:
    pip install pdfplumber

USAGE:
    from resume_parser import parse_resume
    resume_data = parse_resume(uploaded_file)   # streamlit UploadedFile object
"""

import re
import io
from datetime import datetime

# KNOWN SKILLS DICTIONARY
# These are matched case-insensitively against the resume text
# Add more skills relevant to your job roles here

KNOWN_SKILLS = [
    # Programming Languages
    "python", "java", "javascript", "typescript", "c++", "c#", "r", "scala",
    "go", "rust", "kotlin", "swift", "php", "ruby", "matlab", "julia",

    # ML / AI
    "machine learning", "deep learning", "neural networks", "nlp",
    "natural language processing", "computer vision", "reinforcement learning",
    "tensorflow", "pytorch", "keras", "scikit-learn", "sklearn", "xgboost",
    "lightgbm", "huggingface", "transformers", "bert", "gpt", "llm",
    "opencv", "yolo", "pandas", "numpy", "scipy", "matplotlib", "seaborn",
    "plotly",

    # Data & Databases
    "sql", "mysql", "postgresql", "mongodb", "redis", "elasticsearch",
    "cassandra", "snowflake", "bigquery", "spark", "hadoop", "hive",
    "airflow", "dbt", "etl", "data warehouse", "data pipeline",

    # Cloud & DevOps
    "aws", "azure", "gcp", "google cloud", "docker", "kubernetes",
    "terraform", "jenkins", "ci/cd", "github actions", "linux", "bash",

    # Web & APIs
    "react", "angular", "vue", "node.js", "django", "flask", "fastapi",
    "rest api", "graphql", "html", "css",

    # Cybersecurity
    "cybersecurity", "penetration testing", "ethical hacking", "network security",
    "firewalls", "siem", "vulnerability assessment", "wireshark", "kali linux",

    # Tools & Methodologies
    "git", "agile", "scrum", "jira", "tableau", "power bi", "excel",
    "microsoft office", "figma", "postman",
]

# KNOWN CERTIFICATIONS
KNOWN_CERTIFICATIONS = {
    # AWS
    "aws certified": "AWS Certified",
    "aws solutions architect": "AWS Certified",
    "aws developer": "AWS Certified",
    "aws cloud practitioner": "AWS Certified",

    # Google
    "google ml": "Google ML",
    "google machine learning": "Google ML",
    "google cloud certified": "Google ML",
    "tensorflow developer": "Google ML",

    # Deep Learning
    "deep learning specialization": "Deep Learning Specialization",
    "deeplearning.ai": "Deep Learning Specialization",
    "andrew ng": "Deep Learning Specialization",

    # Others
    "azure certified": "AWS Certified",  # mapped to closest
    "comptia": "AWS Certified",
    "cissp": "AWS Certified",
    "pmp": "None",
    "certified scrum": "None",
}

# EDUCATION KEYWORDS
EDUCATION_PATTERNS = [
    # Highest degree first — we want the highest one found
    (r"\bph\.?d\b|\bdoctor(?:ate|al)?\b", "PhD"),
    (r"\bm\.?tech\b|\bmaster of technology\b", "M.Tech"),
    (r"\bmba\b|\bmaster of business\b", "MBA"),
    (r"\bm\.?sc\b|\bmaster of science\b|\bm\.?s\b", "M.Tech"),  # map MSc to M.Tech
    (r"\bb\.?tech\b|\bbachelor of technology\b", "B.Tech"),
    (r"\bb\.?sc\b|\bbachelor of science\b|\bb\.?s\b", "B.Sc"),
    (r"\bbachelor\b|\bundergraduate\b", "B.Sc"),
]

# JOB ROLE KEYWORDS

JOB_ROLE_PATTERNS = {
    "Data Scientist": ["data scientist", "data science", "ml engineer",
                       "machine learning engineer"],
    "Software Engineer": ["software engineer", "software developer",
                          "backend developer", "frontend developer",
                          "full stack", "fullstack", "web developer"],
    "AI Researcher": ["ai researcher", "research scientist",
                      "artificial intelligence researcher",
                      "nlp researcher", "computer vision researcher"],
    "Cybersecurity Analyst": ["cybersecurity", "security analyst",
                              "information security", "penetration tester",
                              "ethical hacker", "soc analyst"],
}


# CORE EXTRACTION FUNCTION

def extract_text_from_pdf(uploaded_file) -> str:
    """
    Extracts all raw text from a PDF using pdfplumber.

    pdfplumber is better than PyPDF2 for resumes because it
        - Handles multi-column layouts
        - Preserves text order better
        - Handles tables and formatted sections

    uploaded_file: Streamlit UploadedFile object OR a file Path string

    Returns: Clean String of all text in the PDF
    """
    try:
        import pdfplumber

        # Streamlit's UploadedFile needs to be read as bytes first
        if hasattr(uploaded_file, "read"):
            pdf_bytes = uploaded_file.read()
            uploaded_file.seek(0)  # reset so it can be read again later
            pdf_file = io.BytesIO(pdf_bytes)
        else:
            pdf_file = uploaded_file  # it's already a file path

        full_text = ""
        with pdfplumber.open(pdf_file) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    full_text += text + "\n"

        return full_text.strip()

    except Exception as e:
        print(f"pdfplumber failed: {e}, trying PyPDF2...")
        # Fallback to PyPDF2 if pdfplumber fails
        try:
            import PyPDF2
            if hasattr(uploaded_file, "read"):
                uploaded_file.seek(0)
            reader = PyPDF2.PdfReader(uploaded_file)
            text = ""
            for page in reader.pages:
                text += page.extract_text() or ""
            if hasattr(uploaded_file, "seek"):
                uploaded_file.seek(0)
            return text.strip()
        except Exception as e2:
            print(f"PyPDF2 also failed: {e2}")
            return ""


def extract_skills(text: str) -> list:
    """
        Scans resume text for known skills and returns a list of matches.

        Uses word boundary matching so "R" doesn't match inside "React",
        and skills with spaces like "machine learning" are found correctly.

        Returns: list of matched skill strings
    """
    text_lower = text.lower()
    found = []

    for skill in KNOWN_SKILLS:
        # Use Word boundary for single words, simple 'in' for phrases
        if " " in skill:
            if skill in text_lower:
                found.append(skill)
        else:
            pattern = r"\b" + re.escape(skill) + r"\b"
            if re.search(pattern, text_lower):
                found.append(skill)

    return found
