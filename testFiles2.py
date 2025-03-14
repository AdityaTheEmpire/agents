from requests.utils import cookiejar_from_dict
from linkedin_api import Linkedin
import time
import random

def get_company_details_and_posts(api, company_name):
    """
    Fetches LinkedIn company details and recent posts for a given company name.

    Parameters:
    - api (Linkedin): An authenticated Linkedin object.
    - company_name (str): The official name of the company.

    Returns:
    - dict: A dictionary containing company details and recent posts.
    """
    time.sleep(random.uniform(30, 50))
    search_results = api.search_companies(company_name)
    if not search_results:
        raise Exception(f'Company "{company_name}" not found.')
    company_urn = search_results[0].get('urn_id')
    if not company_urn:
        raise Exception(f'URN ID for company "{company_name}" not found.')
    time.sleep(random.uniform(30, 60))
    company_details = api.get_company(company_urn)
    time.sleep(random.uniform(40, 50))
    company_posts = api.get_company_updates(company_urn)
    return {
        'company_details': company_details,
        'company_posts': company_posts
    }

def main():
    # Authentication setup (replace with your own cookie values)
    li_at_value = "YOUR_LI_AT_COOKIE_VALUE_HERE"  # Replace with your li_at cookie value
    cookie_dict = {"li_at": li_at_value, "JSESSIONID": "ajax:5172403101787511942"}
    cookie_jar = cookiejar_from_dict(cookie_dict)
    api = Linkedin(username="", password="", cookies=cookie_jar)

    company_name = 'moon-event'  # Replace with your target company name
    
    # Fetch company details and posts
    results = get_company_details_and_posts(api, company_name)
    
    # Extract company details and posts
    company_details = results['company_details']
    company_posts = results['company_posts']
    
    # Print company details
    print("company")
    print("details:")
    print(f"           {company_details.get('description', 'No description available')}")
    print()
    
    # Print each post
    for i, post in enumerate(company_posts, 1):
        # Navigate the nested structure to get the post text
        update_v2 = post.get('value', {}).get('com.linkedin.voyager.feed.render.UpdateV2', {})
        commentary = update_v2.get('commentary', {})
        text_data = commentary.get('text', {})
        text = text_data.get('text', 'No text available')
        print(f"post {i}:")
        print(text)
        print()

if __name__ == "__main__":
    main()