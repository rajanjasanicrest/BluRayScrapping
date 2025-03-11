import re
import os
import requests
from base64 import b64decode
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
from bs4 import BeautifulSoup
from dotenv import load_dotenv
load_dotenv()
def clean_text(text):
    """Remove special characters and extra spaces from the title."""
    return re.sub(r'[^a-zA-Z0-9 ]', '', text).strip().lower()


def is_title_match(target_title, ebay_title, threshold=80):
    # Remove special characters and convert to lowercase
    def clean_text(text):
        return re.sub(r'[^a-zA-Z0-9\s]', '', text).lower()

    target_words = clean_text(target_title).split()
    ebay_words = clean_text(ebay_title).split()

    # Count matching words
    match_count = sum(1 for word in target_words if word in ebay_words)
    match_percentage = (match_count / len(target_words)) * 100 if target_words else 0

    return match_percentage >= threshold, match_percentage



def get_epid(upc, title, year, prod_company, max_results=10):
    # Make a request to the Zyte API
    url = f'https://www.ebay.com/sch/i.html?_nkw=DVD {upc} {title} {prod_company} {year}'
    print(url)
    ZYTE_KEY = os.getenv("ZYTE_KEY")
    api_response = requests.post(
        "https://api.zyte.com/v1/extract",
        auth=(ZYTE_KEY, ""),
        json={
            "url": url,
            "browserHtml": True,

            "requestHeaders": {
                "referer": "https://www.google.com/"
            }
        },
        timeout=60
    )
    api_response.raise_for_status()

    # # Decode response from the API
    response_data = api_response.json()
    # if "httpResponseBody" not in response_data:
    #     return None

    # Decode the base64 encoded response body to get HTML content
    http_response_body = response_data['browserHtml']

    # Use BeautifulSoup to parse the HTML content
    soup = BeautifulSoup(http_response_body, 'html.parser')

    # Extract search results
    items = soup.select('ul.srp-results > li.s-item')[:max_results]
    
    first_three_items = items[:min(3, len(items))]

    # Clean the title
    title_clean = clean_text(title)

    for item in first_three_items:
        title_element = item.find(class_='s-item__title')
        if title_element:
            ebay_title = title_element.text.strip()
            if not is_title_match(title_clean, ebay_title):
                continue
        product_link = item.find('a', class_='s-item__link')
        if product_link:
            product_url = product_link.get('href')
            parsed_product_url = urlparse(product_url)
            query_params = parse_qs(parsed_product_url.query)
            epid = query_params.get("epid", [None])[0]
            if epid:
                print(product_url)
                return epid  # Found ePID in URL


    return None  # No match found

# if __name__ == '__main__':
     
#     print(get_epid("025493222128", "Elvis The Complete Story"))