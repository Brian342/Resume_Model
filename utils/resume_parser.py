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


