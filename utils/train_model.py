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
    df["has_certification"] = (df["Certifications"] != "None").astype(int)
    print(f"has_certification: {df['has_certification'].sum()} candidates with certs")

    # Map education to a numeric seniority level
    # This helps the model understand PhD > M.Tech > B.Tech etc
    edu_rank = {
        "B.Sc": 1,
        "B.Tech": 2,
        "MBA": 3,
        "M.Tech": 4,
        "PhD": 5,
    }
    df["education_rank"] = df["Education"].map(edu_rank).fillna(2)
    print(f"education_rank: mapped {len(edu_rank)} levels")

    # Is the candidate experienced? (5+ years)
    df["is_experienced"] = (df["Experience (years)"].astype(int) >= 5).astype(int)

    # High AI Score flag (the dataset's own Scoring)
    df["high_ai_score"] = (df["AI Score (0-100)"].astype(int) >= 70).astype(int)

    print()
    return df


# Step 3 PREPARE x and Y
def prepare_features(df: pd.DataFrame):
    """
    Splits the dataframe into:
    X_text     → the Skills text column (for TF-IDF)
    X_numeric  → numeric features (for scaling)
    y          → target labels encoded as 0/1

    Returns X_text, X_numeric, y, feature_names
    """
    print("=" * 60)
    print("STEP 3: Preparing Features")
    print("=" * 60)

    # Encode target: Hire ->1, Reject ->0
    y = (df[TARGET_COLUMN] == "Hire").astype(int)
    print(f"Target encoded: Hire=1, Reject=0")
    print(f"Class counts: {Counter(y)}")

    # Text feature - Skills Column
    X_text = df[TEXT_COLUMN].fillna("")

    # Numeric features - all engineered + original numeric cols
    numeric_feature_names = NUMERICAL_COLUMNS + [
        "skill_count",
        "has_certification",
        "education_rank",
        "is_experienced",
        "high_ai_score"
    ]

    # One-hot encode categorical columns
    # We do this manually so we can combine with sparse TF-IDF matrix
    cat_dummies = pd.get_dummies(
        df[CATEGORICAL_COLUMNS],
        prefix=CATEGORICAL_COLUMNS
    )

    # Combine numerical + one-hot categorical into one matrix
    X_numeric = pd.concat([
        df[numeric_feature_names].astype(float),
        cat_dummies
    ], axis=1)

    print(f"  Text features  : TF-IDF on '{TEXT_COLUMN}'")
    print(f"  Numeric features: {numeric_feature_names}")
    print(f"  Categorical features (one-hot): {CATEGORICAL_COLUMNS}")
    print(f"  Total numeric+cat columns: {X_numeric.shape[1]}")
    print()

    return X_text, X_numeric, y, X_numeric.columns.tolist()


# STEP 4 - BUILD AND TRAIN THE MODEL
def train_model(X_text, X_numeric, y):
    """
    Trains a Logistic Regression classifier Combining:
        - TF-IDF Vectors from the Skills Text
        - Numeric + categorical Features

    WHY LOGISTIC REGRESSION?
      - Trains in milliseconds on 1000 rows
      - Highly interpretable (you can see which features matter)
      - Works very well for text classification
      - class_weight="balanced" automatically handles our 81/19 split

    HOW TF-IDF WORKS:
      "Python, TensorFlow, NLP" becomes a vector of numbers
      where each number represents how important a word is
      relative to all other resumes in the dataset.
      Common words get low scores, rare-but-important words get high scores.

    Returns the trained model components.
    """
    print("=" * 60)
    print("STEP 4: Training model")
    print("=" * 60)

    # split into train (80%) and test (20%) sets
    # stratify=y ensures bot sets have the same Hire/Reject ratio
    (X_text_train, X_text_test,
     X_num_train, X_num_test,
     y_train, y_test) = train_test_split(
        X_text, X_numeric, y,
        test_size=0.2,
        random_state=42,
        stratify=y  # Keeps class ratio the same in bth splits
    )
    print(f"Training Set : {len(y_train)} samples")
    print(f"Test set :{len(y_test)} samples")
    print()

    # ── TF-IDF Vectorizer ────────────────────────────────────────────────────
    # ngram_range=(1,2) means we look at single words AND pairs:
    #   "Python" (unigram) and "Machine Learning" (bigram)
    # max_features limits vocabulary size for speed
    # min_df=2 ignores words that appear in fewer than 2 resumes

    tfidf = TfidfVectorizer(
        ngram_range=(1, 2),
        max_features=500,
        min_df=2,
        strip_accents="unicode",
        lowercase=True
    )

    # Fit on training data only - Never fit on test data
    # This prevents "data leakage" - the model shouldn't know test vocabulary
    X_text_train_vec = tfidf.fit_transform(X_text_train)
    X_text_test_vec = tfidf.transform(X_text_test)  # only transform, not fit

    # Combine TF-IDF + numeric features
    # hstack stacks sparse matrices side by side horizontally
    # Result shape: (n_samples, tfidf_features + numeric_features)
    from scipy.sparse import hstack, csr_matrix
    X_train_combined = hstack([
        X_text_train_vec,
        csr_matrix(X_num_train.values.astype(float))
    ])
    X_test_combined = hstack([
        X_text_test_vec,
        csr_matrix(X_num_test.values.astype(float))
    ])

    print(f"fCombined features matrix shape: {X_train_combined.shape}")

    # Train Logistic Regression
    print("Training Logistic Regression...")
    clf = LogisticRegression(
        class_weight="balanced",  # handles Hire/Reject imbalance automatically
        max_iter=1000,  # enough iterations to converge
        c=1.0,  # regularization strength (1.0 = default)
        random_state=42
    )
    clf.fit(X_train_combined, y_train)
    print("Training complete")
    print()

    return clf, tfidf, X_train_combined, X_test_combined, y_train, y_test


# Evaluate
def evaluate_model(clf, X_train, X_test, y_train, y_test):
    """
    Prints a full evaluation report:
      - Train vs test accuracy (to detect overfitting)
      - Precision, Recall, F1-score per class
      - Confusion matrix

    WHAT THESE METRICS MEAN:
      Precision : of all predicted "Hire", what % were actually Hire?
      Recall    : of all actual "Hire", what % did we correctly predict?
      F1-score  : harmonic mean of precision + recall (best single metric)
      Confusion Matrix:
            Predicted Reject | Predicted Hire
        Actual Reject  [TN]  |  [FP]   ← False Positives (rejected but predicted hire)
        Actual Hire    [FN]  |  [TP]   ← True Positives (hired and predicted hire)
    """
    print("=" * 60)
    print("STEP 5: Evaluation")
    print("=" * 60)

    y_pred_train = clf.predict(X_train)
    y_pred_test = clf.predict(X_test)

    train_acc = accuracy_score(y_train, y_pred_train)
    test_acc = accuracy_score(y_test, y_pred_test)

    print(f"Train accuracy :{train_acc:.4f} ({train_acc * 100:.1f}%)")
    print(f"Test accuracy :{test_acc:.4f} ({test_acc * 100:.1f}%)")

    if train_acc - test_acc > .1:
        print("Possible Overfitting - Train much higher test")
    else:
        print("Good generalisation - train and test are close")

    print()
    print("Classification Report:")
    print(classification_report(
        y_test, y_pred_test,
        target_names=["Reject (0)", "Hire (1)"]
    ))

    print("Confusion Matrix:")
    cm = confusion_matrix(y_test, y_pred_test)
    print(f"                Predicted Reject Predicted Hire")
    print(f"Actual Reject   {cm[0][0]:3d}    {cm[0][1]:3d}")
    print(f"Actual Hire     {cm[1][0]:3d}    {cm[1][1]:3d}")
    print()


# Save Model
def save_model(clf, tfidf, numeric_columns: list):
    """
    Saves everything needed for inference into one .pkl file.

    We save a dict containing:
      clf             → the trained classifier
      tfidf           → the fitted TF-IDF vectorizer
      numeric_columns → column names (to build features consistently)
      edu_rank        → the education ranking dict
      label_map       → maps 1→Hire, 0→Reject back to strings

    WHY SAVE AS A DICT (not just the model)?
      When predicting on a new resume, we need the SAME tfidf vectorizer
      that was fitted during training. If we only saved clf, we couldn't
      transform new text. Saving everything together keeps it simple.
    """
    print("=" * 60)
    print("STEP 6: Saving model")
    print("=" * 60)

    model_bundle = {
        "clf": clf,
        "tfidf": tfidf,
        "numeric_columns": numeric_columns,
        "edu_rank": {
            "B.Sc": 1, "B.Tech": 2, "MBA": 3, "M.Tech": 4, "PhD": 5
        },
        "label_map": {1: "Hire", 0: "Reject"},
        "categorical_cols": CATEGORICAL_COLUMNS,
    }

    joblib.dump(model_bundle, MODEL_PATH)
    size_kb = os.path.getsize(MODEL_PATH) / 1024
    print(f"Model saved to : {MODEL_PATH} ({size_kb:.1f} KB")
    print()

# Predict Function
def predict_single(model_bundle: dict, resume_data: dict) -> tuple:
    """
        Predicts Hire/Reject and a 0-100 score for a single resume.

        This is the function that score_resume() in apply.py will call.

        resume_data dict keys:
          skills          : str  — "Python, Machine Learning, SQL"
          experience_years: int  — years of experience
          education       : str  — "B.Sc" | "B.Tech" | "MBA" | "M.Tech" | "PhD"
          certifications  : str  — "None" | "AWS Certified" | "Google ML" | etc.
          job_role        : str  — "Data Scientist" | "Software Engineer" | etc.
          projects_count  : int  — number of projects

        Returns:
          score (float) : 0-100 match score
          label (str)   : "Qualified" | "Not Qualified" | "Review Needed"
        """
    from scipy.sparse import hstack, csr_matrix

    clf = model_bundle["clf"]
    tfidf = model_bundle["tfidf"]
    edu_rank = model_bundle["edu_rank"]

    skills = resume_data.get("skills", "")
    experience_years = int(resume_data.get("experience_years", 0))
    education = resume_data.get("education", "B.Sc")
    certifications = resume_data.get("certifications", "None")
    job_role = resume_data.get("job_role", "")
    projects_count = int(resume_data.get("projects_count", 0))

    # Replicate the same feature engineering from training
    skill_list = [s.strip() for s in skills.split(",") if s.strip()]
    skill_count = len(skill_list)
    has_cert = int(certifications := "None")
    edu_level = edu_rank.get(education, 2)
    is_experienced = int(experience_years >= 5)


