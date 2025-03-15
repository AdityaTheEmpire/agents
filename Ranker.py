import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from langchain.embeddings import HuggingFaceEmbeddings
import numpy as np



class CandidateRanker:
    def __init__(self):
        # Initialize embedding model for semantic similarity
        self.embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")

    def preprocess_data(self, df):
        """Preprocess candidate data for consistency."""
        df['skills'] = df['skills'].str.lower().fillna('')
        df['interests'] = df['interests'].str.lower().fillna('')
        df['certifications'] = df['certifications'].str.lower().fillna('')
        df['location'] = df['location'].str.lower().fillna('')
        df['experience'] = df['experience'].str.lower().fillna('')
        df['open_to_work'] = df['open_to_work'].str.lower().fillna('no')
        return df

    def calculate_skill_score(self, jd_skills, candidate_skills):
        """Calculate semantic similarity for skills using embeddings."""
        try:
            jd_embedding = self.embeddings.embed_query(jd_skills)
            candidate_embedding = self.embeddings.embed_query(candidate_skills)
            return cosine_similarity([jd_embedding], [candidate_embedding])[0][0]
        except Exception:
            return 0.0

    def calculate_location_score(self, required_location, candidate_location):
        """Score based on location match."""
        return 1.0 if candidate_location == required_location else 0.0

    def calculate_experience_score(self, required_exp, candidate_exp):
        """Score based on experience level."""
        exp_map = {'entry': 1, 'mid': 2, 'senior': 3}
        jd_level = exp_map.get(required_exp.lower(), 1)
        candidate_level = exp_map.get(candidate_exp.lower(), 1)
        return max(0, 1 - abs(jd_level - candidate_level) / 2)

    def calculate_certification_score(self, required_certs, candidate_certs):
        """Score based on certifications."""
        required = set(required_certs.split(','))
        candidate = set(candidate_certs.split(','))
        return len(required.intersection(candidate)) / len(required) if required else 1.0

    def rank_candidates(self, job_description, candidates_csv, output_csv):
        """
        Rank candidates based on job description and save results to a CSV file.
        
        Args:
            job_description (dict): Dictionary containing job description details.
            candidates_csv (str): Path to the input CSV file with candidate data.
            output_csv (str): Path to save the ranked CSV file.
        
        Returns:
            str: Path to the output CSV file.
        """
        # Load and preprocess candidate data
        df = pd.read_csv(candidates_csv)
        df = self.preprocess_data(df)

        # Extract job description components
        required_skills = job_description.get('skills', '').lower()
        required_location = job_description.get('location', '').lower()
        required_experience = job_description.get('experience', 'mid').lower()
        required_certifications = job_description.get('certifications', '')
        weights = {
            'skill_score': 0.4,
            'location_score': 0.2,
            'exp_score': 0.3,
            'cert_score': 0.1
        }

        # Calculate scores for each candidate
        df['skill_score'] = df['skills'].apply(lambda x: self.calculate_skill_score(required_skills, x))
        df['location_score'] = df['location'].apply(lambda x: self.calculate_location_score(required_location, x))
        df['exp_score'] = df['experience'].apply(lambda x: self.calculate_experience_score(required_experience, x))
        df['cert_score'] = df['certifications'].apply(lambda x: self.calculate_certification_score(required_certifications, x))

        # Calculate total score
        df['total_score'] = (
            df['skill_score'] * weights['skill_score'] +
            df['location_score'] * weights['location_score'] +
            df['exp_score'] * weights['exp_score'] +
            df['cert_score'] * weights['cert_score']
        )

        # Sort by total score and save to CSV
        ranked_df = df.sort_values(by='total_score', ascending=False)
        ranked_df.to_csv(output_csv, index=False)
        return output_csv


# Function to invoke ranking from another file
def csvRanke(job_description_file, candidates_csv):
    """
    Invoke the ranking system and return the path to the ranked CSV file.
    
    Args:
        job_description_file (str): Path to the job description Markdown file.
        candidates_csv (str): Path to the input CSV file with candidate data.
    
    Returns:
        str: Path to the output ranked CSV file.
    """
    # Try reading the file with different encodings
    try:
        with open(job_description_file, 'r', encoding='utf-8') as f:
            jd_content = f.read()
    except UnicodeDecodeError:
        try:
            # If UTF-8 fails, try 'latin-1' or other suitable encodings
            with open(job_description_file, 'r', encoding='latin-1') as f:  # Or 'iso-8859-1'
                jd_content = f.read()
        except UnicodeDecodeError:
            print(f"Error: Could not decode file '{job_description_file}' with common encodings.")
            return None

    # Extract key components from job description (customize parsing logic as needed)
    job_description = {
        'skills': 'event planning, client management, vendor coordination',
        'location': 'paris',
        'experience': 'mid',
        'certifications': 'event management,cvent'
    }  # Replace with actual parsing logic

    # Initialize ranker and perform ranking
    ranker = CandidateRanker()
    output_csv = "ranked_candidates.csv"
    return ranker.rank_candidates(job_description, candidates_csv, output_csv)



# Example usage in another file
if __name__ == "__main__":
    resultRankedCsv = csvRanke("job_description.md", "candidates.csv")
    print(f"Ranked CSV saved at: {resultRankedCsv}")
