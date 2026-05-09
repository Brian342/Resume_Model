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


def extract_experience_years(text: str) -> int:
    """
        Estimates total years of experience from the resume text.

        Strategy 1 — look for explicit statements:
          "5 years of experience", "3+ years", "over 4 years"

        Strategy 2 — scan for date ranges and sum them up:
          "Jan 2019 – Mar 2022" → 3 years
          "2020 – Present"      → calculated from current year

        Returns: integer years (0 if nothing found)
    """
    text_lower = text.lower()
    current_year = datetime.now().year

    # Strategy 1: Explicit mention
    # Matches "5 years", "3+ years", "over 4 years", "two years"
    explicit_patterns = [
        r"(\d+)\+?\s*years?\s*(?:of\s*)?(?:experience|exp)",
        r"(\d+)\s*years?\s*(?:in|of|working)",
        r"experience\s*(?:of\s*)?(\d+)\+?\s*years?",
    ]
    for pattern in explicit_patterns:
        match = re.search(pattern, text_lower)
        if match:
            years = int(match.group(1))
            if 0 < years < 50:  # Sanity check
                return years

    # Strategy 2 Date range scanning
    # find all 4-digit years in the document
    years_found = [int(y) for y in re.findall(r"\b(20\d{2}|19\d{2})\b", text)]
    years_found = [y for y in years_found if 1990 <= y <= current_year]

    if len(years_found) >= 2:
        # Check for "present" or "current" alongside years
        has_present = bool(re.search(
            r"\b(present|current|now|ongoing)\b", text_lower
        ))
        earliest = min(years_found)
        latest = current_year if has_present else max(years_found)
        estimated = latest - earliest

        # Cap at reasonable bounds
        if 0 < estimated < 40:
            return estimated

    return 0


def extract_education(text: str) -> str:
    """
        Detects the highest education level mentioned in the resume.
        Returns the highest match found (PhD > M.Tech > MBA > B.Tech > B.Sc).

        Falls back to "B.Sc" if nothing is found.
    """
    text_lower = text.lower()

    # Patterns are ordered highest to lowest - return first match
    for pattern, label in EDUCATION_PATTERNS:
        if re.search(pattern, text_lower, re.IGNORECASE):
            return label

    return "B.Sc"  # Default


def extract_certifications(text: str) -> str:
    """
    Detects certifications mentioned in the resume.
    Returns the first matched Certification label, or "None".

    Matches against KNOWN_CERTIFICATIONS dict keys (case-insensitive).
    """
    text_lower = text.lower()

    for keyword, cert_label in KNOWN_CERTIFICATIONS.items():
        if keyword in text_lower:
            return cert_label

    return "None"


def extract_projects_count(text: str) -> int:
    """
    Estimates the number of projects from the resume.

    Counts occurrences of project indicators:
        - Numbered lists in a Projects section
        - Lines starting with bullet points after "Projects"
        - "Project:" labels

    Returns an integer count (capped at 20 for sanity)
    """
    text_lower = text.lower()

    # Look for a Projects section and count items within it
    projects_section = re.search(
        r"projects?\s*\n(.*?)(?:\n[A-Z]{2,}|\Z)",
        text,
        re.IGNORECASE | re.DOTALL
    )

    if projects_section:
        section_text = projects_section.group(1)
        # Count bullet points or numbered items
        bullets = len(re.findall(r"^[\•\-\*\✓\▪]", section_text, re.MULTILINE))
        numbered = len(re.findall(r"^\d+[\.\)]\s+\w", section_text, re.MULTILINE))
        count = max(bullets, numbered)
        if count > 0:
            return min(count, 20)

    # Fallback: count "project" keyword occurrences divided by 2
    # (project name + project description each mention it once)
    mentions = len(re.findall(r"\bproject\b", text_lower))
    return min(max(mentions // 2, 0), 10)


def extract_job_role(text: str) -> str:
    """
    Detects the candidate's target or current job role from resume text.
    Matches against JOB_ROLE_PATTERNS.

    Returns the matched role label or empty string if not found
    """
    text_lower = text.lower()

    for role_label, keywords in JOB_ROLE_PATTERNS.items():
        for keyword in keywords:
            if keyword in text_lower:
                return role_label

    return ""


# MAIN PARSE FUNCTION

def parse_resume(uploaded_file) -> dict:
    """
    Master function - extracts all structured fields from a resume PDF

    This is the only function you need to call from apply.py

    uploaded_file: Streamlit UploadedFile object

    Returns a dict with all fields needed by predict_single():
    {
        "raw_text"         : str   — full extracted text (for TF-IDF)
        "skills"           : str   — comma-separated matched skills
        "skills_list"      : list  — list of matched skills
        "experience_years" : int   — estimated years of experience
        "education"        : str   — highest degree found
        "certifications"   : str   — certification label or "None"
        "projects_count"   : int   — estimated number of projects
        "job_role"         : str   — detected job role or ""
        "skill_count"      : int   — number of skills found
    }
    """
    print(" Parsing resume PDF...")

    # Step 1: Extract raw text from PDF
    raw_text = extract_text_from_pdf(uploaded_file)

    if not raw_text:
        print("Could not extract text from PDF - using empty defaults")
        return {
            "raw_text": "",
            "skills": "",
            "skills_list": [],
            "experience_years": 0,
            "education": "B.Sc",
            "certifications": "None",
            "projects_count": 0,
            "job_role": "",
            "skill_count": 0,
        }
    print(f" Extracted {len(raw_text)} characters from PDF")

    # Step 2: Extract each field
    skills_list = extract_skills(raw_text)
    experience_years = extract_experience_years(raw_text)
    education = extract_education(raw_text)
    certifications = extract_certifications(raw_text)
    projects_count = extract_projects_count(raw_text)
    job_role = extract_job_role(raw_text)

    skills_str = ", ".join(skills_list) if skills_list else raw_text[:500]
    # If no skills matched our dictionary, pass the raw text to TF-IDF
    # so the model still has something meaningful to work with

    result = {
        "raw_text": raw_text,
        "skills": skills_str,
        "skills_list": skills_list,
        "experience_years": experience_years,
        "education": education,
        "certifications": certifications,
        "projects_count": projects_count,
        "job_role": job_role,
        "skill_count": len(skills_list),
    }

    print(f"  Skills found     : {len(skills_list)} — {skills_list[:5]}...")
    print(f"  Experience       : {experience_years} years")
    print(f"  Education        : {education}")
    print(f"  Certifications   : {certifications}")
    print(f"  Projects count   : {projects_count}")
    print(f"  Job role         : {job_role or 'not detected'}")

    return result

