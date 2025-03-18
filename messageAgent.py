import pandas as pd
from langchain_google_genai import ChatGoogleGenerativeAI
from linkedin_api import Linkedin
import os
from dotenv import load_dotenv
from requests.utils import cookiejar_from_dict
from linkedin_api import Linkedin

# Load environment variables
load_dotenv()

# Initialize Gemini 2.0 Flash model using LangChain
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash", google_api_key=GOOGLE_API_KEY)

# Initialize LinkedIn API client
li_at_value = os.getenv("LI_AT_VALUE")
JSESSIONID = os.getenv("JSESSIONID")
cookie_dict = {"li_at": li_at_value, "JSESSIONID": JSESSIONID}
cookie_jar = cookiejar_from_dict(cookie_dict)
api = Linkedin(username="", password="", cookies=cookie_jar)
    
    
def parse_job_description(job_description_file):
    """
    Parse the job description file and extract key details.
    """
    with open(job_description_file, "r", encoding="utf-8") as f:
        job_description = f.read()
    
    # Extract key sections (you can enhance this with NLP if needed)
    responsibilities = "Responsibilities: Not specified"
    qualifications = "Qualifications: Not specified"
    preferred_qualifications = "Preferred Qualifications: Not specified"
    
    if "Responsibilities:" in job_description:
        responsibilities = job_description.split("Responsibilities:")[1].split("Qualifications:")[0].strip()
    if "Qualifications:" in job_description:
        qualifications = job_description.split("Qualifications:")[1].split("Preferred Qualifications:")[0].strip()
    if "Preferred Qualifications:" in job_description:
        preferred_qualifications = job_description.split("Preferred Qualifications:")[1].strip()
    
    return {
        "responsibilities": responsibilities,
        "qualifications": qualifications,
        "preferred_qualifications": preferred_qualifications
    }

def generate_personalized_message(candidate_profile, job_description):
    """
    Generate a personalized message for a candidate using Gemini 2.0 Flash.
    """
    template = f"""
    You are contacting a candidate based on their LinkedIn profile and the following job description:
    - Job Title: {candidate_profile.get('job title', 'Not specified')}
    - Skills: {candidate_profile.get('skills', 'Not specified')}
    - Location: {candidate_profile.get('location', 'Not specified')}
    
    Job Description Details:
    - Responsibilities: {job_description['responsibilities']}
    - Qualifications: {job_description['qualifications']}
    - Preferred Qualifications: {job_description['preferred_qualifications']}
    
    Write a concise and professional message to introduce yourself and express interest in discussing potential opportunities.
    Highlight how the candidate's skills and experience align with the job description.
    Make sure the tone is friendly but formal.
    """
    response = llm.invoke(template)
    return response.content.strip()

def message_people(job_description_file, ranked_csv_file, num_people):
    """
    Send personalized messages to the top N candidates from the ranked CSV file based on the job description.
    """
    # Parse the job description
    job_description = parse_job_description(job_description_file)
    
    # Read and sort CSV by total_score (descending)
    df = pd.read_csv(ranked_csv_file)
    df_sorted = df.sort_values(by='total_score', ascending=False)
    
    # Select top N candidates
    top_candidates = df_sorted.head(num_people)
    
    # Track messaged candidates
    messaged_candidates = []
    
    # Iterate through top candidates and send messages
    for index, row in top_candidates.iterrows():
        urn_id = row['urn id']
        name = row['name']
        
        try:
            # Generate personalized message using Gemini 2.0 Flash
            personalized_message = generate_personalized_message(row, job_description)
            
            # Send the message via LinkedIn API
            api.send_message(
                message=personalized_message,
                recipients=[urn_id]  # Uses profile URN directly
            )
            
            # Log successful messaging
            print(f"Message sent to {name} (URN: {urn_id})")
            messaged_candidates.append({
                "urn_id": urn_id,
                "name": name,
                "message": personalized_message
            })
        
        except Exception as e:
            print(f"Failed to send message to {name} (URN: {urn_id}): {e}")
    
    # Save messaged candidates to a new CSV file
    messaged_df = pd.DataFrame(messaged_candidates)
    output_file = f"messaged_{ranked_csv_file}"
    messaged_df.to_csv(output_file, index=False)
    print(f"Messaged candidates saved to {output_file}")
    
    return output_file

# Example usage:
if __name__ == "__main__":
    Messagedcsv = message_people(
        job_description_file="Google_Software Engineer.md",
        ranked_csv_file="ranked_candidates.csv",
        num_people=10
    )
