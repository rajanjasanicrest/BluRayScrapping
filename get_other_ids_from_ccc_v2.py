import os
import logging
import requests
from base64 import b64decode
from bs4 import BeautifulSoup
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from dotenv import load_dotenv
load_dotenv()
# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@retry(
    stop=stop_after_attempt(3),  # Retry up to 3 times
    wait=wait_exponential(multiplier=2, min=2, max=10),  # Exponential backoff
    retry=retry_if_exception_type(requests.exceptions.RequestException),  # Retry only on request failures
    reraise=True  # Raise exception if all retries fail
)
def fetch_data(url):
    """Make a request to Zyte API and return response JSON."""
    ZYTE_KEY = os.getenv("ZYTE_KEY")
    api_response = requests.post(
        "https://api.zyte.com/v1/extract",
        auth=(ZYTE_KEY, ""),
        json={"url": url, "httpResponseBody": True},
        timeout=60
    )
    api_response.raise_for_status()
    return api_response.json()

def get_other_ids(amazon_id):
    """
    Fetch product identifiers from CamelCamelCamel for a given Amazon ID with retry logic.
    
    Args:
        amazon_id (str): Amazon product ID
        
    Returns:
        dict: Dictionary containing product identifiers
    """
    url = f'https://camelcamelcamel.com/product/{amazon_id}'
    product_details = {}
    
    try:
        response_data = fetch_data(url)
        
        if "httpResponseBody" not in response_data:
            logger.error("No response body in API response")
            return product_details
        
        http_response_body = b64decode(response_data["httpResponseBody"])
        soup = BeautifulSoup(http_response_body, 'html.parser')
        
        table = (soup.find('table', class_='product_fields') or 
                 soup.find('table', {'id': 'product_fields'}) or
                 soup.find('table', string=lambda text: text and any(
                     key in text.lower() for key in ["manufacturer", "isbn", "ean", "upc", "sku"]
                 )))
        
        if not table:
            logger.error("Product details table not found")
        else:
            key_mappings = {
                'manufacturer': 'Manufacturer',
                'isbn': 'ISBN',
                'ean': 'EAN',
                'upc': 'UPC',
                'sku': 'SKU',
                'asin': 'ASIN'
            }
            
            for row in table.find_all('tr'):
                cols = row.find_all('td')
                if len(cols) >= 2:
                    raw_key = cols[0].get_text(strip=True).lower().replace(':', '').strip()
                    
                    value_cell = cols[1]
                    for wbr in value_cell.find_all('wbr'):
                        wbr.decompose()
                    
                    value = value_cell.get_text(strip=True).replace('\u200b', '').strip()
                    
                    for key_pattern, standard_key in key_mappings.items():
                        if key_pattern in raw_key:
                            if value:
                                product_details[standard_key] = value
                                logger.debug(f"Found {standard_key}: {value}")
                            break
        
        price_table = soup.find('tbody')
        if price_table:
            for row in price_table.find_all('tr'):
                category = row.get('data-field', '').strip()
                prices = row.find_all('td')
                
                if category == 'amazon':
                    product_details['amazon_current_price'] = prices[-1].get_text(strip=True).replace('$', '').split('(')[0]
                    product_details['amazon_average_price'] = prices[-2].get_text(strip=True).replace('$', '').split('(')[0]
                elif category == 'used':
                    product_details['third_used_current_price'] = prices[-1].get_text(strip=True).replace('$', '').split('(')[0]
                    product_details['third_used_average_price'] = prices[-2].get_text(strip=True).replace('$', '').split('(')[0]
        else:
            logger.error("Price table not found")
    
    except requests.exceptions.RequestException as e:
        logger.error(f"Request failed: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
    
    return product_details


if __name__ == '__main__':
    amazon_id = '157330039X'
    product_details = get_other_ids(amazon_id)
    print(product_details)