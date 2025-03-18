import streamlit as st
from dotenv import load_dotenv
import os
from linkedin_api import Linkedin
from requests.utils import cookiejar_from_dict
from langchain_google_genai import ChatGoogleGenerativeAI
import pandas as pd
import time

# Load environment variables
load_dotenv()
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
LI_AT_VALUE = os.getenv("LI_AT_VALUE")
JSESSIONID = os.getenv("JSESSIONID")

# Initialize LinkedIn API
cookie_dict = {"li_at": LI_AT_VALUE, "JSESSIONID": JSESSIONID}
cookie_jar = cookiejar_from_dict(cookie_dict)
api = Linkedin(username="", password="", cookies=cookie_jar)

# Initialize language model
llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash", google_api_key=GOOGLE_API_KEY)

# Import functions from other scripts
# Note: These functions need to be modified to accept `api` and `llm` where necessary
from JobDescriptionBuilder import run_graph
from Employeegather import gather_people_csv
from Ranker import ranker_sort
from messageAgent import message_people

def main():
    st.title("LinkedIn Job Outreach App")

    # Initialize session state for step tracking
    if 'step' not in st.session_state:
        st.session_state.step = 1

    # Step 1: Collect user inputs
    if st.session_state.step == 1:
        st.header("Step 1: Enter Job Details")
        job_role = st.text_input("Job Role (e.g., Event Planner)")
        num_people = st.number_input("Number of People to Message", min_value=1, step=1)
        company_id = st.text_input("LinkedIn Company ID (e.g., urn:li:organization:123456)")
        if st.button("Generate Job Description"):
            if job_role and num_people and company_id:
                st.session_state.job_role = job_role
                st.session_state.num_people = num_people
                # Assuming LinkedIn ID is the URN; we'll use it as company_name for simplicity
                st.session_state.company_name = company_id
                st.session_state.step = 2
            else:
                st.error("Please fill in all fields.")

    # Step 2: Generate and review job description
    elif st.session_state.step == 2:
        st.header("Step 2: Review Job Description")
        job_description_file = f"{st.session_state.company_name}_{st.session_state.job_role}.md"
        with st.spinner("Generating job description..."):
            # Pass company_id as company_name; adjust run_graph if it can use URN directly
            run_graph(st.session_state.company_name, st.session_state.job_role, llm, api)
        with open(job_description_file, "r") as f:
            job_description = f.read()
        st.markdown(job_description)
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Regenerate"):
                with st.spinner("Regenerating job description..."):
                    run_graph(st.session_state.company_name, st.session_state.job_role, llm, api)
                st.rerun()
        with col2:
            if st.button("Accept"):
                st.session_state.step = 3

    # Step 3: Gather and rank candidates
    elif st.session_state.step == 3:
        st.header("Step 3: Gather and Rank Candidates")
        candidate_csv_file = f"candidates_{st.session_state.job_role.replace(' ', '_')}.csv"
        ranked_csv_file = "ranked_candidates.csv"
        job_description_file = f"{st.session_state.company_name}_{st.session_state.job_role}.md"
        with st.spinner("Gathering candidates..."):
            gather_people_csv(st.session_state.job_role, 100, api)  # Gather up to 100 candidates
        with st.spinner("Ranking candidates..."):
            ranker_sort(job_description_file, candidate_csv_file, ranked_csv_file)
        # Display top candidates with images
        df = pd.read_csv(ranked_csv_file)
        st.subheader("Top Candidates")
        for index, row in df.head(10).iterrows():
            st.write(f"**{row['name']}**")
            if 'profile image URL' in row and pd.notna(row['profile image URL']) and row['profile image URL'] != 'N/A':
                st.image(row['profile image URL'], width=100)
            st.write(f"Skills: {row['skills']}")
            st.write(f"Job Title: {row['job title']}")
            st.write(f"Location: {row['location']}")
            st.write("---")
        if st.button("Proceed to Messaging"):
            st.session_state.step = 4

    # Step 4: Message top candidates
    elif st.session_state.step == 4:
        st.header("Step 4: Message Top Candidates")
        ranked_csv_file = "ranked_candidates.csv"
        job_description_file = f"{st.session_state.company_name}_{st.session_state.job_role}.md"
        num_people = st.session_state.num_people
        with st.spinner(f"Messaging top {num_people} candidates..."):
            message_people(job_description_file, ranked_csv_file, num_people, llm, api)
        st.success(f"Successfully messaged top {num_people} candidates!")
        # Display messaged candidates
        messaged_csv_file = f"messaged_{ranked_csv_file}"
        df = pd.read_csv(messaged_csv_file)
        st.subheader("Messaged Candidates")
        for index, row in df.iterrows():
            st.write(f"**{row['name']}**")
            st.write(f"Message: {row['message']}")
            st.write("---")

if __name__ == "__main__":
    main()
