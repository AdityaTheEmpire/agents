import streamlit as st
import pandas as pd
import os
from dotenv import load_dotenv
from JobDescriptionBuilder import run_graph  # Generates the JD file
from Employeegather import gather_people_csv  # Generates the candidate CSV
from Ranker import ranker_sort  # Generates the ranked CSV

# Load environment variables
load_dotenv()
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
LI_AT_VALUE = os.getenv("LI_AT_VALUE")
JSESSIONID = os.getenv("JSESSIONID")

# Function to sanitize file names
def sanitize_filename(text):
    """Replace spaces and special characters with underscores."""
    return text.replace(" ", "_").replace("/", "_").replace("\\", "_").lower()

# Function to display CSV data with images, links, and optional scores
def display_csv_with_data(csv_file, show_scores=False):
    """Display CSV data with images, clickable profile links, and optionally scores."""
    try:
        df = pd.read_csv(csv_file)
        for index, row in df.iterrows():
            name = row.get('name', 'Unknown Name')
            st.write(f"**{name}**")

            # Display profile link
            profile_link = row.get('link to profile')
            if pd.notna(profile_link) and profile_link != 'N/A':
                st.markdown(f"[View LinkedIn Profile]({profile_link})", unsafe_allow_html=True)
            else:
                st.write("Profile link unavailable")

            # Display image
            image_url = row.get('profile image URL')
            if pd.notna(image_url) and image_url != 'N/A':
                try:
                    st.image(image_url, width=100, caption=f"Profile image for {name}")
                except Exception:
                    st.write("Image unavailable")
            else:
                st.write("No image available")

            # Display other details
            skills = row.get('skills', 'N/A')
            job_title = row.get('job title', 'N/A')
            location = row.get('location', 'N/A')
            st.write(f"Skills: {skills}")
            st.write(f"Job Title: {job_title}")
            st.write(f"Location: {location}")

            # Display score if applicable
            if show_scores and 'total_score' in row:
                score = row.get('total_score', 'N/A')
                st.write(f"Ranking Score: {score:.2f}")

            st.write("---")
    except FileNotFoundError:
        st.error(f"CSV file {csv_file} not found.")

# Function to display previously generated files
def display_previous_files(files):
    """Display links to previously generated files."""
    st.sidebar.header("Previous Files")
    for file_name in files:
        if os.path.exists(file_name):
            st.sidebar.write(file_name)
        else:
            st.sidebar.write(f"{file_name} (not found)")

def main():
    st.title("LinkedIn Job Outreach Application")

    # Initialize session state
    if 'step' not in st.session_state:
        st.session_state.step = 1
    if 'files' not in st.session_state:
        st.session_state.files = []
    if 'job_role' not in st.session_state:
        st.session_state.job_role = None
    if 'company_id' not in st.session_state:
        st.session_state.company_id = None
    if 'num_search' not in st.session_state:
        st.session_state.num_search = None

    # Sidebar to display previous files
    display_previous_files(st.session_state.files)

    # Step 1: Take Input
    if st.session_state.step == 1:
        st.header("Enter Job Details")
        job_role = st.text_input("Job Role (e.g., Event Planner)", value=st.session_state.job_role or "")
        company_id = st.text_input("Company LinkedIn ID (e.g., moon-events)", value=st.session_state.company_id or "")
        num_search = st.number_input("Number of People to Search (min 10)", min_value=10, step=1, value=st.session_state.num_search or 10)

        if st.button("Submit"):
            if job_role and company_id and num_search >= 10:
                st.session_state.job_role = job_role
                st.session_state.company_id = company_id
                st.session_state.num_search = num_search
                st.session_state.step = 2
                st.rerun()
            else:
                st.error("Please fill all fields correctly. Number of People to Search must be at least 10.")

    # Step 2: Display Job Description File and Take Permission
    elif st.session_state.step == 2:
        st.header("Review Job Description")
        prefix = f"{sanitize_filename(st.session_state.company_id)}_{sanitize_filename(st.session_state.job_role)}"
        jd_file = f"jd_{prefix}.md"

        if not os.path.exists(jd_file):
            with st.spinner("Generating Job Description..."):
                try:
                    generated_file = run_graph(st.session_state.company_id, st.session_state.job_role)
                    if generated_file != jd_file:
                        os.rename(generated_file, jd_file)
                    st.session_state.files.append(jd_file)
                except Exception as e:
                    st.error(f"Error generating job description: {e}")
                    return

        if os.path.exists(jd_file):
            with open(jd_file, "r", encoding="utf-8") as f:
                jd_content = f.read()
            st.markdown("### Generated Job Description")
            st.markdown(jd_content)
        else:
            st.error(f"Job description file {jd_file} not found.")
            return

        col1, col2 = st.columns(2)
        with col1:
            if st.button("Regenerate Job Description"):
                if os.path.exists(jd_file):
                    os.remove(jd_file)
                    st.session_state.files.remove(jd_file)
                with st.spinner("Regenerating Job Description..."):
                    try:
                        generated_file = run_graph(st.session_state.company_id, st.session_state.job_role)
                        if generated_file != jd_file:
                            os.rename(generated_file, jd_file)
                        st.session_state.files.append(jd_file)
                    except Exception as e:
                        st.error(f"Error regenerating job description: {e}")
                        return
                st.rerun()
        with col2:
            if st.button("Accept and Proceed"):
                st.session_state.step = 3
                st.rerun()

    # Step 3: Gather People
    elif st.session_state.step == 3:
        st.header("Gathering Candidates")
        candidate_csv = f"candidates_{sanitize_filename(st.session_state.job_role)}.csv"

        if not os.path.exists(candidate_csv):
            with st.spinner("Gathering Candidates..."):
                try:
                    gather_people_csv(st.session_state.job_role, st.session_state.num_search)
                    st.session_state.files.append(candidate_csv)
                except Exception as e:
                    st.error(f"Error gathering candidates: {e}")
                    return

        if os.path.exists(candidate_csv):
            st.success(f"Candidates gathered and saved to {candidate_csv}")
            if st.button("Proceed to Review Candidates"):
                st.session_state.step = 4
                st.rerun()
        else:
            st.error(f"Candidate file {candidate_csv} not found.")
            return

    # Step 4: Display Candidate Profiles
    elif st.session_state.step == 4:
        st.header("Review Candidates")
        candidate_csv = f"candidates_{sanitize_filename(st.session_state.job_role)}.csv"
        display_csv_with_data(candidate_csv)

        if st.button("Proceed to Ranking"):
            st.session_state.step = 5
            st.rerun()

    # Step 5: Rank the People
    elif st.session_state.step == 5:
        st.header("Ranking Candidates")
        prefix = f"{sanitize_filename(st.session_state.company_id)}_{sanitize_filename(st.session_state.job_role)}"
        jd_file = f"jd_{prefix}.md"
        candidate_csv = f"candidates_{sanitize_filename(st.session_state.job_role)}.csv"
        ranked_csv = f"ranked_{prefix}.csv"

        if not os.path.exists(ranked_csv):
            with st.spinner("Ranking Candidates..."):
                try:
                    ranker_sort(jd_file, candidate_csv, ranked_csv)
                    st.session_state.files.append(ranked_csv)
                except Exception as e:
                    st.error(f"Error ranking candidates: {e}")
                    return

        if os.path.exists(ranked_csv):
            st.success(f"Candidates ranked and saved to {ranked_csv}")
            if st.button("View Ranked Candidates"):
                st.session_state.step = 6
                st.rerun()
        else:
            st.error(f"Ranked file {ranked_csv} not found.")
            return

    # Step 6: Display Ranked Candidates with Scores
    elif st.session_state.step == 6:
        st.header("Ranked Candidates")
        prefix = f"{sanitize_filename(st.session_state.company_id)}_{sanitize_filename(st.session_state.job_role)}"
        ranked_csv = f"ranked_{prefix}.csv"
        display_csv_with_data(ranked_csv, show_scores=True)

        if st.button("Finish Workflow"):
            st.success("Workflow completed. Start a new workflow if desired.")
            st.session_state.step = 1  # Reset to start a new workflow
            st.rerun()

if __name__ == "__main__":
    main()
