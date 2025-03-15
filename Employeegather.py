import csv
import time
import random
from linkedin_api import Linkedin
from requests.cookies import cookiejar_from_dict
from requests.exceptions import TooManyRedirects, RequestException

# Initialize 2 API clients with different cookies for detail fetching
api_list = [
    Linkedin("", "", cookies=cookiejar_from_dict({
        'li_at': '',
        'JSESSIONID': ""
    })),
    Linkedin("", "", cookies=cookiejar_from_dict({
        'li_at': '',
        'JSESSIONID': ""
    }))
]

# Primary search API (use a different cookie)
primary_api = Linkedin("", "", cookies=cookiejar_from_dict({
    'li_at': '',
    'JSESSIONID': ""
}))

def search_people_and_save_csv(search_params: dict, output_csv: str = "candidates.csv", limit: int = 100):
    """
    Search LinkedIn for people, fetch their profiles, and save to a CSV file.
    
    Args:
        search_params (dict): Parameters for the search (e.g., {'keywords': 'software engineer'}).
        output_csv (str): Output CSV filename.
        limit (int): Maximum number of profiles to fetch.
    
    Returns:
        str: The CSV filename.
    """
    csv_filename = output_csv
    processed_count = 0
    total_profiles = []
    current_api_index = 0  # For rotating detail APIs

    # Define fieldnames for CSV
    fieldnames = ["urn_id", "jobtitle", "location", "experience", 
                  "certifications", "skills", "open_to_work", "interests"]

    # Initialize CSV with headers using DictWriter
    with open(csv_filename, mode="w", newline="", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()

    while processed_count < limit:
        try:
            # Fetch next batch of profiles
            batch_size = min(limit - processed_count, 50)
            search_params['limit'] = batch_size
            search_params['offset'] = processed_count
            results = primary_api.search_people(**search_params)

            if not results:
                print("No more search results found")
                break

            for candidate in results:
                urn_id = candidate.get("urn_id")
                if not urn_id:
                    print(f"Skipping candidate due to missing urn_id: {candidate}")
                    continue

                try:
                    # Rotate between detail APIs
                    detail_api = api_list[current_api_index % len(api_list)]
                    current_api_index += 1

                    # Fetch detailed profile
                    detailed_profile = detail_api.get_profile(urn_id)
                    if not detailed_profile:
                        print(f"Failed to fetch profile for {urn_id}")
                        continue

                    # Parse profile data
                    processed_profile = {
                        "urn_id": urn_id,
                        "jobtitle": candidate.get("headline", ""),
                        "location": candidate.get("locationName", ""),
                        "experience": _parse_experience(detailed_profile.get("experience", [])),
                        "certifications": _parse_list(detailed_profile.get("certifications", [])),
                        "skills": _parse_list(detailed_profile.get("skills", [])),
                        "open_to_work": detailed_profile.get("openToOpportunities", False),
                        "interests": _parse_list(detailed_profile.get("interests", []))
                    }

                    total_profiles.append(processed_profile)
                    processed_count += 1

                    # Write to CSV in batches
                    if len(total_profiles) >= 10:
                        _append_to_csv(csv_filename, total_profiles, fieldnames)
                        total_profiles = []

                    # Add delay to avoid rate limiting
                    time.sleep(random.uniform(1, 3))

                except TooManyRedirects:
                    print(f"TooManyRedirects for {urn_id}, rotating API")
                    current_api_index += 1
                    continue
                except RequestException as e:
                    print(f"Network error fetching {urn_id}: {str(e)}")
                    continue
                except Exception as e:
                    print(f"Unexpected error fetching {urn_id}: {str(e)}")
                    continue

            # Write remaining profiles after batch
            if total_profiles:
                _append_to_csv(csv_filename, total_profiles, fieldnames)
                total_profiles = []

        except Exception as e:
            print(f"Search error: {str(e)}")
            break

    print(f"Processed {processed_count} profiles successfully")
    return csv_filename

def _parse_experience(experience_data: list) -> str:
    """Parse experience data into a formatted string."""
    if not isinstance(experience_data, list):
        return "No experience data"
    return " | ".join([
        f"{exp.get('companyName', '')}: {exp.get('title', '')} "
        f"({exp.get('timePeriod', {}).get('startDate', '')} - "
        f"{exp.get('timePeriod', {}).get('endDate', 'Present')})"
        for exp in experience_data
    ]) if experience_data else "No experience data"

def _parse_list(items: list) -> str:
    """Parse a list of items (e.g., skills, certifications) into a string."""
    if not isinstance(items, list):
        return "None"
    return ", ".join([item.get("name", "") for item in items]) if items else "None"

def _append_to_csv(filename: str, data: list, fieldnames: list):
    """Append a list of profile dictionaries to the CSV file."""
    with open(filename, mode="a", newline="", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writerows(data)

# Example usage
if __name__ == "__main__":
    result = search_people_and_save_csv({'keywords': 'software engineer'})
    print(f"Results saved to {result}")
