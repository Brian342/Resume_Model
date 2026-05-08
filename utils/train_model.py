"""
train_model.py - Resume Screening ML Model
Trains a TF-IDF + Logistic Regression Classifier on the
AI_RESUME_SCREENING.csv dataset

WHAT THIS SCRIPT DOES:
1. Loads and explores the dataset
2. Engineers features from skills, Experience, Education
3. Handles class imbalance (812 Hire vs 188 Reject)
4. Trains a Logistic Regression classifier
5. Evaluates accuracy, Precision, Recall
6. Saves the trained Model to resume_model.pkl
7. Saves a label encoder to label_encoder.pkl

DATASET COLUMNS USED:
    Skills              → text, TF-IDF vectorized
    Experience (Years)  → numeric
    Education           → categorical, encoded
    Certifications      → categorical, encoded
    Projects Count      → numeric
    AI Score (0-100)    → numeric (the dataset's own score — useful feature)
    Job Role            → categorical, encoded

TARGET COLUMN:
    Recruiter Decision -> "Hire" (1) or "Reject" (0)

CLASS DISTRIBUTION
    Hire:   812 (81.2%)
    Reject: 188 (18.8%)
    -> Imbalanced! we use class_weight="balanced" to handle this

OUTPUT FILES:
    resume_model.pkl    -> trained pipeline (Vectorized + Classifier)
    label_encoder.pkl   -> encodes categorical features

INSTALL:
    pip install scikit-learn pandas numpy joblib
"""
import pandas as pd
import numpy as np
import joblib
import os
from collections import Counter

from sklearn.pipeline import Pipeline
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import LabelEncoder
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.metrics import (
    classification_report,
    confusion_matrix,
    accuracy_score
)
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from scipy.sparse import hstack

# Config
DATASET_PATH = "/Resume_Screening/AI_Resume_Screening.csv"  # path to your csv file
MODEL_PATH = "resume_model.pkl"  # Where to save the trained model
ENCODER_PATH = "label_encoder.pkl"  # Where to save encoders

# The column we are trying to predict
TARGET_COLUMN = "Recruiter Decision"

# Text column - this is TF-IDF Vectorized
TEXT_COLUMN = "Skills"

# Numerical Columns - used as-is
NUMERICAL_COLUMNS = [
    "Experience (Years)",
    "Projects Count",
    "AI Score (0-100)"  # The dataset already has an AI score - great feature:
]

# Category Columns - one-hot encoded
CATEGORICAL_COLUMNS = [
    "Education",
    "Certifications",
    "Job Role"
]


# LOAD DATA
def load_data(path: str) -> pd.DataFrame:
    """
    Loads the CSV and does basic cleaning.
    Prints a summary so you can verify it loaded correctly
    """
    print("=" * 60)
    print("STEP 1: Loading Dataset")
    print("=" * 60)

    df = pd.read_csv(path)

    print(f"Rows Loaded :{len(df)}")
    print(f"Columns :{list(df.columns)}")
    print()

    # Check for missing Values
    missing = df.isnull().sum()
    if missing.any():
        print(" Missing Values Found:")
        print(missing[missing > 0])
        # Fill missing text with empty string numeric with 0
        df["Skills"] = df["Skills"].fillna("")
        df["Certifications"] = df["Certifications"].fillna("None")
    else:
        print("No Missing Values Found")

    # Show Class distribution
    dist = df[TARGET_COLUMN].value_counts()
    print()
    print(f"Target distribution ({TARGET_COLUMN}):")
    for label, count in dist.items():
        pct = count / len(df) * 100
        print(f"{label:10s}: {count:4d} ({pct:.1f}%)")

    print()
    return df


# Step 2 - Feature Engineering
def engineer_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Creates additional features from the raw data

    Why Feature Engineering?
    The raw Skills column is a comma-separated string like
    "Python, TensorFlow, NLP", We want to extract signals
    from the data that the model can learn from
    """
    print("=" * 60)
    print("STEP 2: Feature Engineering")
    print("=" * 60)

    df = df.copy()

    # Count how many skills the candidate has
    # "Python, TensorFlow, NLP" ->3
    df["skill_count"] = df["skills"].apply(
        lambda x: len([s.strip() for s in x.split(",") if s.strip()])
    )
    print(f"skill_count range: {df['skill_count'].min()} - {df['skill_count'].max()}")

    # Flag for having a certification (vs "None")
    df["has_certification"] = (df[])
