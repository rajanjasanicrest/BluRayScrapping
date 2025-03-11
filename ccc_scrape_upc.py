import requests
import os
from base64 import b64decode
from typing import Dict, Optional, Tuple
from bs4 import BeautifulSoup
from get_other_ids_from_ccc_v2 import get_other_ids
from dotenv import load_dotenv

load_dotenv()

def make_zyte_request(url) :
    """
    Makes request to Zyte API and returns decoded response body.
    """
    try:
        ZYTE_KEY = os.getenv("ZYTE_KEY")
        api_response = requests.post(
            "https://api.zyte.com/v1/extract",
            auth=(ZYTE_KEY, ''),
            
            json={
                "url": url,
                "browserHtml": True,

                "requestHeaders": {
                    "referer": "https://www.google.com/"
                }
            },
            timeout=60
        )
        response_data = api_response.json()
        http_response_body = response_data['browserHtml']
        
        return http_response_body

    except Exception as e:
        print(f"Zyte API request failed: {e}")
        return None

def check_camel_search_results(html_content: str) :
    """
    Checks if there's exactly one search result and returns its product URL if true.
    """
    try:
        soup = BeautifulSoup(html_content, 'html.parser')
        search_results = soup.find_all('div', class_='search-result')
        
        # Get product URL from the first (and only) result
        product_link = search_results[0].find('p', class_='product-title').find('a')
        if product_link and product_link.get('href'):
            return True, product_link['href']
            
        return False, None
        
    except Exception as e:
        print(f"Error processing search results: {e}")
        return False, None

def extract_asin(url: str):
    """
    Extracts product details from the CamelCamelCamel product page HTML.
    """

    asin = url.split('?')[0].split('/')[-1]
        
    return asin

def process_camel_search(search_url: str):
    """
    Main function to process CamelCamelCamel search using Zyte API.
    """
    try:
        # Get search results page
        search_html = make_zyte_request(search_url)
        if not search_html:
            return {
                'success': False,
                'message': 'Failed to fetch search results'
            }
        
        # Check if single result
        is_single_result, product_url = check_camel_search_results(search_html)
        if not is_single_result:
            return {
                'success': False,
                'message': 'Multiple or no results found'
            }
       
        
        asin = extract_asin(product_url)
        details = get_other_ids(asin)
        
        return {
            'success': True,
            'details': details
        }
        
    except Exception as e:
        return {
            'success': False,
            'message': f'Error during processing: {str(e)}'
        }

# Example usage
# def main():
#     search_url = "https://camelcamelcamel.com/search?sq=014381475920"
#     result = process_camel_search(search_url)
    
#     if result['success']:
#         print(f"Product Details: {result['details']}")
#     else:
#         print(f"Error: {result['message']}")

# if __name__ == "__main__":
#     main()
