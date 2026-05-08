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
DATASET_PATH = "/Resume_Screening/AI_Resume_Screening.csv"
MODEL_PATH = "resume_model.pkl"
