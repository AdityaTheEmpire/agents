import os
import re
import csv
from typing import Annotated
from typing_extensions import TypedDict
from langgraph.graph import StateGraph, START, END
from requests.utils import cookiejar_from_dict
from linkedin_api import Linkedin
import time
import random
from langchain_core.prompts import PromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

# LinkedIn API setup
def initialize_linkedin_api():
    li_at_value = "AQEDAUF4XqYC5iCsAAABlWIJYlsAAAGVhhXmW1YAB666BIg-GhSjUc2n6yc-rRuLcoLB116udjDYCucTEvKkZ9lilc7w3qmqVg6oaNLkxULbOoMKBNQYVzw1sn8bbT8saMXGk8nR3h-HpZ0_gn923Mxr"
    cookie_dict = {"li_at": li_at_value, "JSESSIONID": "ajax:5172403101787511942"}
    cookie_jar = cookiejar_from_dict(cookie_dict)
    return Linkedin(username="", password="", cookies=cookie_jar)

# Define state for the graph
class State(TypedDict):
    """
    Represents the state object for the employee search workflow.
    
    Attributes:
        job_file (str): Path to the job description markdown file
        firm_name (str): Name of the company
        role (str): Job title/role
        location (str): Job location
        qualifications (str): Required qualifications
        industry (str): Industry of the company
        employees (list): List of employee profiles from LinkedIn
        filtered_employees (list): Filtered employee data for CSV
    """
    job_file: str
    firm_name: str
    role: str
    location: str
    qualifications: str
    industry: str
    employees: list
    filtered_employees: list

graph_builder = StateGraph(State)

# Node 1: Parse Job Description
def parse_jd_node(state: State):
    """
    Parses the job description markdown file to extract key details.
    """
    with open(state["job_file"], "r") as file:
        content = file.read()

    firm_name = re.search(r"Company Overview\n(.+?) is", content)
    firm_name = firm_name.group(1) if firm_name else "Unknown Company"

    role = re.search(r"Job Title\n(.+?)\n", content)
    role = role.group(1).strip() if role else "Unknown Role"

    location = re.search(r"Based in (.+?), we operate", content)
    location = location.group(1) if location else "Unknown Location"

    qualifications = re.search(r"# Qualifications\n([\s\S]+?)# Benefits", content)
    qualifications = qualifications.group(1).strip() if qualifications else "No qualifications specified"

    industry = re.search(r"we operate in the (.+?) sector", content)
    industry = industry.group(1) if industry else "Unknown Industry"

    return {
        "firm_name": firm_name,
        "role": role,
        "location": location,
        "qualifications": qualifications,
        "industry": industry,
        "employees": [],
        "filtered_employees": []
    }

graph_builder.add_node("parse_jd", parse_jd_node)

# Node 2: Search Employees on LinkedIn
def search_employees_node(state: State):
    """
    Searches LinkedIn for employees based on JD criteria.
    """
    api = initialize_linkedin_api()

    # Get company URN
    time.sleep(random.uniform(1, 3))
    search_results = api.search_companies(state["firm_name"])
    if not search_results:
        raise Exception(f'Company "{state["firm_name"]}" not found.')
    company_urn = search_results[0]['urn_id']

    # Extract filters from qualifications (e.g., experience, skills)
    qualifications = state["qualifications"].lower()
    experience = re.search(r"(\d+\+?) years", qualifications)
    experience_years = experience.group(1) if experience else None
    skills = re.findall(r"(strong|excellent|proficient|experience in) (.+?)( skills| experience|,|\.|and|\n)", qualifications)
    skills = [skill[1] for skill in skills] if skills else []

    # Perform LinkedIn search
    time.sleep(random.uniform(1, 3))
    employees = api.search_people(
        current_company=[company_urn],
        keyword_title=state["role"],
        industries=[state["industry"]] if state["industry"] != "Unknown Industry" else None,
        keywords=" ".join(skills) if skills else None,
        limit=50  # Adjust as needed
    )
    return {"employees": employees}

graph_builder.add_node("search_employees", search_employees_node)

# Node 3: Filter and Process Employees
llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash", google_api_key=GOOGLE_API_KEY)

def filter_employees_node(state: State):
    """
    Filters employees based on JD criteria and extracts relevant data.
    """
    qualifications = state["qualifications"]
    employees = state["employees"]
    filtered_employees = []

    prompt_template = PromptTemplate(
        input_variables=["employee_data", "qualifications"],
        template="""
        Given the employee data: {employee_data}
        And job qualifications: {qualifications}
        Extract and return a dictionary with:
        - urnid: Employee's URN ID
        - skills: List of skills (comma-separated)
        - experience: Total years of experience (numeric or 'Unknown')
        - location: Employee's location
        - industry: Employee's industry
        Only include fields relevant to filtering, no names or extra details.
        If data is missing, use 'Unknown'.
        """
    )

    for emp in employees:
        try:
            emp_data = str(emp)  # Convert dict to string for LLM
            prompt = prompt_template.format(employee_data=emp_data, qualifications=qualifications)
            result = llm.invoke(prompt)
            filtered_data = eval(result.content)  # Assuming LLM returns a valid dict string
            filtered_employees.append(filtered_data)
        except Exception:
            filtered_employees.append({
                "urnid": emp.get("urn_id", "Unknown"),
                "skills": "Unknown",
                "experience": "Unknown",
                "location": "Unknown",
                "industry": "Unknown"
            })

    return {"filtered_employees": filtered_employees}

graph_builder.add_node("filter_employees", filter_employees_node)

# Node 4: Save to CSV
def save_to_csv_node(state: State):
    """
    Saves filtered employee data to a CSV file.
    """
    filtered_employees = state["filtered_employees"]
    output_file = f"{state['firm_name']}_employees.csv"
    headers = ["urnid", "skills", "experience", "location", "industry"]

    with open(output_file, "w", newline="") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=headers)
        writer.writeheader()
        for emp in filtered_employees:
            writer.writerow({
                "urnid": emp.get("urnid", "Unknown"),
                "skills": emp.get("skills", "Unknown"),
                "experience": emp.get("experience", "Unknown"),
                "location": emp.get("location", "Unknown"),
                "industry": emp.get("industry", "Unknown")
            })

    return state  # No state change needed

graph_builder.add_node("save_to_csv", save_to_csv_node)

# Define edges
graph_builder.add_edge(START, "parse_jd")
graph_builder.add_edge("parse_jd", "search_employees")
graph_builder.add_edge("search_employees", "filter_employees")
graph_builder.add_edge("filter_employees", "save_to_csv")
graph_builder.add_edge("save_to_csv", END)

# Compile the graph
graph = graph_builder.compile()

# Main function to run the agent
def run_employee_search_agent(job_file: str):
    """
    Executes the employee search workflow based on a job description file.
    """
    if not os.path.exists(job_file):
        raise FileNotFoundError(f"Job description file '{job_file}' not found.")
    
    result = graph.invoke({"job_file": job_file})
    return result

if __name__ == "__main__":
    job_file = "moon-event_Event Planner.md"
    run_employee_search_agent(job_file)