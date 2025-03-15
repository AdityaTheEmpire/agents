import os
from jd_generator import run_graph
from candidate_search import search_people_and_save_csv
from candidate_ranker import CandidateRanker
from messenger import messagePeople

def main():
    # Get initial inputs from the user
    firm_name = input("Enter the companyid in linkedin(moon-events): ")
    role = input("Enter the job role: ")

    # Step 1: Prepare the Job Description (JD)
    run_graph(firm_name, role)
    jd_file = f"{firm_name}_{role}.md"
    print(f"Job description generated and saved to: {jd_file}")

    # Step 2: Take Approval to Gather Candidates
    approval = input("Do you approve the JD to proceed with gathering candidates? (yes/no): ")
    if approval.lower() != 'yes':
        print("Approval not granted. Exiting the workflow.")
        return

    # Step 3: Gather Candidates in a CSV File
    print("Please specify search parameters for gathering candidates.")
    keywords = input("Keywords (e.g., job title, skills): ")
    search_params = {'keywords': keywords}  # Can be extended with more filters if needed
    candidates_csv = search_people_and_save_csv(search_params, output_csv="candidates.csv")
    print(f"Candidates gathered and saved to: {candidates_csv}")

    # Step 4: Rank the Candidates
    print("Please provide the following details for candidate ranking:")
    skills = input("Required skills (comma-separated): ")
    location = input("Required location: ")
    experience = input("Required experience level (entry/mid/senior): ")
    certifications = input("Required certifications (comma-separated): ")
    job_description = {
        'skills': skills,
        'location': location,
        'experience': experience,
        'certifications': certifications
    }
    ranker = CandidateRanker()
    ranked_csv = ranker.rank_candidates(job_description, candidates_csv, "ranked_candidates.csv")
    print(f"Candidates ranked and saved to: {ranked_csv}")

    # Step 5: Take Approval to Message Candidates
    approval = input("Do you approve messaging the top candidates? (yes/no): ")
    if approval.lower() != 'yes':
        print("Approval not granted. Exiting the workflow.")
        return

    # Step 6: Message the Top Candidates
    num_people = int(input("Enter the number of top candidates to message: "))
    messagePeople(ranked_csv, num_people)
    print(f"Messages sent to the top {num_people} candidates.")

if __name__ == "__main__":
    main()
