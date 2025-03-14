import pandas as pd
from langchain_google_genai import ChatGoogleGenerativeAI
from linkedin_api import Linkedin

# Initialize Gemini 2.0 Flash model using LangChain
llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash", google_api_key="YOUR_GOOGLE_API_KEY") [[1]]

def generate_personalized_message(candidate_profile):
    """
    Generate a personalized message for a candidate using Gemini 2.0 Flash.
    """
    # Template for summarizing job description and personalizing the message
    template = f"""
    You are contacting a candidate based on their LinkedIn profile:
    - Job Title: {candidate_profile['jobtitle']}
    - Skills: {candidate_profile['skills']}
    - Location: {candidate_profile['location']}
    
    Write a concise and professional message to introduce yourself and express interest in discussing potential opportunities.
    Make sure the tone is friendly but formal and highlights their skills.
    """
    response = llm.invoke(template) [[1]]
    return response.content.strip()

def messagePeople(file_name, num_people):
    # Authenticate LinkedIn API (replace with your credentials)
    linkedin = Linkedin('your-email', 'your-password')
    
    # Read and sort CSV by total_score (descending)
    df = pd.read_csv(file_name)
    df_sorted = df.sort_values(by='total_score', ascending=False)
    
    # Select top N candidates
    top_candidates = df_sorted.head(num_people)
    
    # Add names column and send messages
    names = []
    for index, row in top_candidates.iterrows():
        urn_id = row['urn_id']
        
        # Fetch profile details to get name
        profile = linkedin.get_profile(urn_id)
        name = profile.get('firstName', 'N/A') + ' ' + profile.get('lastName', 'N/A')
        names.append(name)
        
        # Generate personalized message using Gemini 2.0 Flash
        personalized_message = generate_personalized_message(row)
        
        # Send the message via LinkedIn API
        linkedin.send_message(
            message=personalized_message,
            recipients=[urn_id]  # Uses profile URN directly [[8]]
        )
    
    # Update DataFrame and save
    top_candidates['names'] = names
    output_file = f"messaged_{file_name}"
    top_candidates.to_csv(output_file, index=False)
    return output_file

# Example usage:
# Messagedcsv = messagePeople("candidates.csv", 10)
