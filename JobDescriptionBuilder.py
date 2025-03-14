import os
from typing import Annotated
from typing_extensions import TypedDict
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langchain_community.tools.tavily_search import TavilySearchResults
from dotenv import load_dotenv
from requests.utils import cookiejar_from_dict
from linkedin_api import Linkedin
import time
import random

# Load environment variables
load_dotenv()
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")

# LinkedIn API setup function
def get_linkedin_data(company_name):
    li_at_value = ""
    cookie_dict = {"li_at": li_at_value, "JSESSIONID": ""}
    cookie_jar = cookiejar_from_dict(cookie_dict)
    api = Linkedin(username="", password="", cookies=cookie_jar)

    time.sleep(random.uniform(1, 3))
    search_results = api.search_companies(company_name)
    if not search_results:
        raise Exception(f'Company "{company_name}" not found.')
    company_urn = search_results[0]['urn_id']
    if not company_urn:
        raise Exception(f'URN ID for company "{company_name}" not found.')
    time.sleep(random.uniform(1, 3))
    company_details = api.get_company(company_urn)
    time.sleep(random.uniform(1, 3))
    company_posts = api.get_company_updates(company_urn)
    return {
        'company_details': company_details,
        'company_posts': company_posts
    }

# Define state for the graph
class State(TypedDict):
    """
    Represents the state object that flows through the graph.
    
    Attributes:
        firm_name (str): Name of the company hiring
        role (str): Job title/role being hired for
        company_details (dict): LinkedIn company details
        company_posts (list): LinkedIn company posts
        search_results (list): Results from Tavily search about role
        job_description (str): Final generated job description
    """
    firm_name: str
    role: str
    company_details: dict
    company_posts: list
    search_results: list
    job_description: str

graph_builder = StateGraph(State)

# Input node
def input_node(state: State):
    """
    Validates and initializes the state with LinkedIn data.
    """
    firm = state["firm_name"]
    role = state["role"]
    if not firm or not role:
        raise ValueError("Firm name and role must be provided.")
    
    # Fetch LinkedIn data
    linkedin_data = get_linkedin_data(firm)
    return {
        "firm_name": firm,
        "role": role,
        "company_details": linkedin_data["company_details"],
        "company_posts": linkedin_data["company_posts"],
        "search_results": [],
        "job_description": ""
    }

graph_builder.add_node("input", input_node)

# Search node (for role info only)
tavily_search = TavilySearchResults(max_results=2, api_key=TAVILY_API_KEY)

def search_node(state: State):
    """
    Performs a web search to gather role responsibilities.
    Uses LinkedIn data for company info directly from state.
    """
    role = state["role"]
    role_info = tavily_search.invoke(f"Responsibilities of a {role}")
    return {
        "search_results": [role_info]
    }

graph_builder.add_node("search", search_node)

# Job description generation node
llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash", google_api_key=GOOGLE_API_KEY)

def job_description_node(state: State):
    """
    Generates a job description using LinkedIn company details and role info.
    """
    firm = state["firm_name"]
    role = state["role"]
    company_details = state["company_details"]
    company_posts = state["company_posts"]
    search_results = state["search_results"]

    # Extract company info from LinkedIn data
    try:
        firm_description = company_details['description']
    except KeyError:
        firm_description = "No description available"
    try:
        firm_name = company_details['name']
    except KeyError:
        firm_name = firm
    try:
        industry = company_details['industries'][0]
    except (KeyError, IndexError):
        industry = "Industry not specified"
    try:
        location = f"{company_details['headquarter']['city']}, {company_details['headquarter']['country']}"
    except KeyError:
        location = "Location not specified"
    try:
        employee_count = company_details['staffCount']
        size = f"{employee_count} employees"
    except KeyError:
        size = "Size not specified"

    # Optional: Include recent post for culture/context
    post_text = "No recent posts available"
    if company_posts:
        try:
            post_text = company_posts[0]['value']['com.linkedin.voyager.feed.render.UpdateV2']['commentary']['text']['text']
        except KeyError:
            pass

    role_info = search_results[0] if search_results else "No role info available"

    prompt = f"""
    Create a comprehensive job description for the role of {role} at {firm_name}. 
    Use the following information about the company from LinkedIn:
    - Description: {firm_description}
    - Industry: {industry}
    - Location: {location}
    - Size: {size}
    - Recent Post (for culture insight): {post_text}

    Here are general responsibilities of the role from web search:
    {role_info}

    Generate a detailed job description that includes:
    - Job Title
    - Company Overview
    - Responsibilities
    - Qualifications
    - Benefits
    """

    job_desc = llm.invoke(prompt)
    return {
        "job_description": job_desc.content
    }

graph_builder.add_node("generate_job_description", job_description_node)

# Define edges
graph_builder.add_edge(START, "input")
graph_builder.add_edge("input", "search")
graph_builder.add_edge("search", "generate_job_description")
graph_builder.add_edge("generate_job_description", END)

# Compile the graph
graph = graph_builder.compile()

# Function to run graph and save output
def run_graph(firm_name: str, role: str) -> None:
    """
    Executes the job description generation workflow and saves the result as a markdown file.
    """
    result = graph.invoke({"firm_name": firm_name, "role": role})
    with open(f"{firm_name}_{role}.md", "w") as file:
        file.write(result["job_description"])

if __name__ == "__main__":
    run_graph("moon-event", "Event Planner")
