import csv
from linkedin_api import Linkedin
from requests.cookies import cookiejar_from_dict
from requests.exceptions import TooManyRedirects, RequestException

def gather_people_csv(keyWord, limit, api):
    """
    Gather candidate details from LinkedIn based on a keyword and save to a CSV file.

    :param keyWord: Keyword to search for (e.g., "fullstack developer")
    :type keyWord: str
    :param limit: Maximum number of people to search for
    :type limit: int
    :return: Path to the generated CSV file
    :rtype: str
    """
    # Step 1: Search for people using the keyword
    people = api.search_people(keywords=keyWord, limit=limit)

    # CSV file setup
    csv_file = f"candidates_{keyWord.replace(' ', '_')}.csv"
    headers = [
        "urn id", "skills", "job title", "experience", "location",
        "Certifications", "Education", "Past Job Titles",
        "link to profile", "name", "profile image URL"
    ]

    # Open CSV file for writing
    with open(csv_file, mode='w', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        writer.writerow(headers)

        # Step 2: Gather detailed profile data for each person
        for person in people:
            urn_id = person.get("urn_id", "")
            name = person.get("name", "N/A")
            job_title = person.get("jobtitle", "N/A")
            location = person.get("location", "N/A")
            profile_link = f"https://www.linkedin.com/in/{person.get('public_id', urn_id)}" if urn_id else "N/A"

            # Fetch full profile details using get_profile
            try:
                profile = api.get_profile(urn_id=urn_id) if urn_id else {}
            except Exception as e:
                print(f"Error fetching profile for {urn_id}: {e}")
                profile = {}

            # Extract skills
            skills = "; ".join([skill.get("name", "") for skill in profile.get("skills", [])]) if profile.get("skills") else "N/A"

            # Extract experience details
            experience = []
            past_job_titles = []
            for exp in profile.get("experience", []):
                title = exp.get("title", "N/A")
                company = exp.get("companyName", "N/A")
                duration = exp.get("timePeriod", {}).get("duration", "N/A")
                experience.append(f"{title} at {company} ({duration})")
                past_job_titles.append(title)
            experience_str = "; ".join(experience) if experience else "N/A"
            past_job_titles_str = "; ".join(past_job_titles) if past_job_titles else "N/A"

            # Extract certifications
            certifications = "; ".join([cert.get("name", "") for cert in profile.get("certifications", [])]) if profile.get("certifications") else "N/A"

            # Extract education
            education = []
            for edu in profile.get("education", []):
                school = edu.get("schoolName", "N/A")
                degree = edu.get("degreeName", "N/A")
                field = edu.get("fieldOfStudy", "N/A")
                education.append(f"{degree} in {field} from {school}")
            education_str = "; ".join(education) if education else "N/A"

            # Extract profile image URL
            image_url = "N/A"
            if "displayPictureUrl" in profile:
                image_keys = [key for key in profile if key.startswith("img_")]
                if image_keys:
                    largest_key = max(image_keys, key=lambda k: int(k.split("_")[1]))
                    image_url = profile["displayPictureUrl"] + profile[largest_key]

            # Write row to CSV
            writer.writerow([
                urn_id,
                skills,
                job_title,
                experience_str,
                location,
                certifications,
                education_str,
                past_job_titles_str,
                profile_link,
                name,
                image_url  # New image field
            ])

    return csv_file

# Example usage
if __name__ == "__main__":
    # Initialize LinkedIn API connection
    EMAIL = ""
    PASSWORD = ""

    api = Linkedin(username=EMAIL, password=PASSWORD, cookies=cookiejar_from_dict({
    'li_at': '',
    'JSESSIONID': ""
    }))

    keyword = "fullstack developer"
    limit = 3  # Limiting to 5 for testing; increase as needed
    csv_file_path = gather_people_csv(keyword, limit, api)
    print(f"CSV file generated: {csv_file_path}")
