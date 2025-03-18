import pandas as pd
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import re

# Load the Sentence-BERT model for embeddings
model = SentenceTransformer('all-MiniLM-L6-v2')

def preprocess_text(text):
    """Preprocess text by removing special characters and converting to lowercase."""
    if not isinstance(text, str):
        return ""
    text = re.sub(r"[^a-zA-Z0-9\s]", "", text)
    return text.lower()

def get_embedding(text):
    """Generate an embedding for the given text."""
    return model.encode(preprocess_text(text))

def ranker_sort(job_description_file, candidate_csv_file, output_csv_file):
    # Load job description
    with open(job_description_file, "r", encoding="utf-8") as f:
        job_description = f.read()
    
    # Generate embedding for the job description
    job_desc_embedding = get_embedding(job_description)

    # Load candidate data
    candidates_df = pd.read_csv(candidate_csv_file)

    # Define field mappings (adjust these based on your CSV file's column names)
    field_mappings = {
        "skills": "Skills",
        "job title": "Job Title",
        "experience_str": "Experience",
        "location": "Location",
        "certifications": "Certifications",
        "education_str": "Education",
        "past_job_titles_str": "Past Job Titles"
    }

    # Preprocess candidate fields
    for field in field_mappings.values():
        if field in candidates_df.columns:
            candidates_df[field] = candidates_df[field].apply(preprocess_text)

    # Define weights for scoring
    weights = {
        "Skills": 0.3,
        "Job Title": 0.2,
        "Experience": 0.2,
        "Location": 0.1,
        "Certifications": 0.05,
        "Education": 0.05,
        "Past Job Titles": 0.1
    }

    # Initialize scores
    candidates_df["skills_score"] = 0.0
    candidates_df["job_title_score"] = 0.0
    candidates_df["experience_score"] = 0.0
    candidates_df["location_score"] = 0.0
    candidates_df["certifications_score"] = 0.0
    candidates_df["education_score"] = 0.0
    candidates_df["past_job_titles_score"] = 0.0
    candidates_df["total_score"] = 0.0

    # Compute scores for each field
    for field, weight in weights.items():
        if field in candidates_df.columns:
            # Generate embeddings for the candidate field
            candidate_embeddings = candidates_df[field].apply(get_embedding).tolist()

            # Compute cosine similarity between job description and candidate field embeddings
            similarities = [cosine_similarity([job_desc_embedding], [emb])[0][0] for emb in candidate_embeddings]
            candidates_df[f"{field.lower().replace(' ', '_')}_score"] = similarities

    # Compute total score
    for field, weight in weights.items():
        if field in candidates_df.columns:
            candidates_df["total_score"] += candidates_df[f"{field.lower().replace(' ', '_')}_score"] * weight

    # Sort candidates by total score
    ranked_candidates = candidates_df.sort_values(by="total_score", ascending=False)

    # Save the ranked candidates to a new CSV file
    ranked_candidates.to_csv(output_csv_file, index=False)

# Example usage
ranker_sort(
    job_description_file="Google_Software Engineer.md",
    candidate_csv_file="candidates.csv",
    output_csv_file="ranked_candidates.csv"
)
