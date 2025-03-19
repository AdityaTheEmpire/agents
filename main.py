import streamlit as st
import pandas as pd
import os
from dotenv import load_dotenv
from JobDescriptionBuilder import run_graph  # Generates the JD file
from Employeegather import gather_people_csv  # Generates the candidate CSV
from Ranker import ranker_sort  # Generates the ranked CSV
from messageAgent import message_people  # Sends messages and generates a messaged CSV

# Load environment variables for API authentication
load_dotenv()
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
LI_AT_VALUE = os.getenv("LI_AT_VALUE")
JSESSIONID = os.getenv("JSESSIONID")

# Function to sanitize file names
def sanitize_filename(text):
    """Replace spaces and special characters with underscores."""
    return text.replace(" ", "_").replace("/", "_").replace("\\", "_")

# Function to display CSV data with images
def display_csv_with_images(csv_file, highlight_green=False):
    """Display CSV data with images and optionally highlight names in green."""
    try:
        df = pd.read_csv(csv_file)
        for index, row in df.iterrows():
            name = row.get('name', 'Unknown Name')
            if highlight_green:
                st.markdown(f"<span style='color:green'>**{name}** - Message Sent</span>", unsafe_allow_html=True)
            else:
                st.write(f"**{name}**")
            image_url = row.get('profile image URL') or row.get('image_link')
            if pd.notna(image_url):
                try:
                    st.image(image_url, width=100)
                except:
                    st.write("(Image unavailable)")
            skills = row.get('skills', 'N/A')
            job_title = row.get('job title', 'N/A')
            location = row.get('location', 'N/A')
            st.write(f"Skills: {skills}")
            st.write(f"Job Title: {job_title}")
            st.write(f"Location: {location}")
            st.write("---")
    except FileNotFoundError:
        st.error(f"CSV file {csv_file} not found.")

def main():
    st.title("Dynamic LinkedIn Job Outreach Application")

    # Initialize session state
    if 'workflows' not in st.session_state:
        st.session_state.workflows = {}  # Store workflow states
    if 'current_workflow_id' not in st.session_state:
        st.session_state.current_workflow_id = None

    # Sidebar for workflow management
    with st.sidebar:
        st.header("Workflow Management")
        if st.button("Start New Workflow"):
            workflow_id = f"workflow_{len(st.session_state.workflows) + 1}"
            st.session_state.workflows[workflow_id] = {
                'step': 1,
                'inputs_collected': False,
                'jd_accepted': False,
                'ranking_accepted': False,
                'company_id': None,
                'job_role': None,
                'num_search': None,
                'num_message': None
            }
            st.session_state.current_workflow_id = workflow_id
        if st.session_state.workflows:
            selected_workflow = st.selectbox(
                "Select Workflow",
                options=list(st.session_state.workflows.keys()),
                index=list(st.session_state.workflows.keys()).index(st.session_state.current_workflow_id) if st.session_state.current_workflow_id else 0
            )
            st.session_state.current_workflow_id = selected_workflow

    # Main content area
    if not st.session_state.current_workflow_id:
        st.write("Please start a new workflow to begin.")
        return

    workflow = st.session_state.workflows[st.session_state.current_workflow_id]
    st.write(f"Current Workflow: {st.session_state.current_workflow_id}")

    # Generate dynamic file names
    if workflow['company_id'] and workflow['job_role']:
        prefix = f"{sanitize_filename(workflow['company_id'])}_{sanitize_filename(workflow['job_role'])}"
        jd_file = f"jd_{prefix}.md"
        candidate_csv = f"candidates_{sanitize_filename(workflow['job_role'])}.csv"
        ranked_csv = f"ranked_{prefix}.csv"
        messaged_csv = f"messaged_{prefix}.csv"
    else:
        jd_file = candidate_csv = ranked_csv = messaged_csv = None

    # **Step 1: Collect User Inputs**
    if workflow['step'] == 1:
        st.header("Enter Job Details")
        job_role = st.text_input("Job Role (e.g., Event Planner)")
        company_id = st.text_input("Company ID (e.g., moon-events)")
        num_search = st.number_input("Number of Employees to Search", min_value=1, step=1)
        num_message = st.number_input("Number of Employees to Message", min_value=1, step=1)

        if st.button("Submit"):
            if job_role and company_id and num_search >= num_message:
                workflow['job_role'] = job_role
                workflow['company_id'] = company_id
                workflow['num_search'] = num_search
                workflow['num_message'] = num_message
                workflow['inputs_collected'] = True
                workflow['step'] = 2
                st.rerun()
            else:
                st.error("Please fill all fields correctly. Ensure 'Number to Message' <= 'Number to Search'.")

    # **Step 2: Generate and Display Job Description**
    elif workflow['step'] == 2 and workflow['inputs_collected']:
        st.header("Review Job Description")
        if not os.path.exists(jd_file):
            with st.spinner("Generating Job Description..."):
                try:
                    run_graph(workflow['company_id'], workflow['job_role'])
                except Exception as e:
                    st.error(f"Error generating job description: {e}")
                    return
        try:
            with open(jd_file, "r", encoding="utf-8") as f:
                jd_content = f.read()
            st.markdown("### Generated Job Description")
            st.markdown(jd_content)
        except FileNotFoundError:
            st.error(f"Job description file {jd_file} not found.")
            return

        col1, col2 = st.columns(2)
        with col1:
            if st.button("Regenerate Job Description"):
                if os.path.exists(jd_file):
                    os.remove(jd_file)
                with st.spinner("Regenerating Job Description..."):
                    run_graph(workflow['company_id'], workflow['job_role'])
                st.rerun()
        with col2:
            if st.button("Accept Job Description"):
                workflow['jd_accepted'] = True
                workflow['step'] = 3
                st.rerun()

    # **Step 3: Gather Candidates and Display CSV**
    elif workflow['step'] == 3 and workflow['jd_accepted']:
        st.header("Candidate Gathering")
        if not os.path.exists(candidate_csv):
            with st.spinner("Gathering Candidates..."):
                try:
                    gather_people_csv(workflow['job_role'], workflow['num_search'])
                except Exception as e:
                    st.error(f"Error gathering candidates: {e}")
                    return
        st.subheader("Collected Candidates")
        display_csv_with_images(candidate_csv)
        if st.button("Proceed to Ranking"):
            workflow['step'] = 4
            st.rerun()

    # **Step 4: Rank Candidates and Display Ranked CSV**
    elif workflow['step'] == 4 and workflow['jd_accepted']:
        st.header("Candidate Ranking")
        if not os.path.exists(ranked_csv):
            with st.spinner("Ranking Candidates..."):
                try:
                    ranker_sort(jd_file, candidate_csv, ranked_csv)
                except Exception as e:
                    st.error(f"Error ranking candidates: {e}")
                    return
        st.subheader("Ranked Candidates")
        display_csv_with_images(ranked_csv)
        if st.button("Accept Ranking"):
            workflow['ranking_accepted'] = True
            workflow['step'] = 5
            st.rerun()

    # **Step 5: Message Candidates and Display Results**
    elif workflow['step'] == 5 and workflow['ranking_accepted']:
        st.header("Messaging Candidates")
        if not os.path.exists(messaged_csv):
            with st.spinner(f"Messaging {workflow['num_message']} Candidates..."):
                try:
                    message_people(jd_file, ranked_csv, workflow['num_message'])
                except Exception as e:
                    st.error(f"Error messaging candidates: {e}")
                    return
        st.subheader("Messaged Candidates")
        display_csv_with_images(messaged_csv, highlight_green=True)
        st.success(f"Successfully messaged {workflow['num_message']} candidates!")
        if st.button("Finish Workflow"):
            st.write("Workflow completed. Start a new workflow from the sidebar if desired.")

if __name__ == "__main__":
    main()
