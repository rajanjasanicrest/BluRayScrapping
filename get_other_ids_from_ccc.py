import os
import requests
from bs4 import BeautifulSoup
from base64 import b64decode
import logging
from dotenv import load_dotenv

load_dotenv()

def get_other_ids(amazon_id):
    """
    Fetch product identifiers from CamelCamelCamel for a given Amazon ID.
    
    Args:
        amazon_id (str): Amazon product ID
        
    Returns:
        dict: Dictionary containing product identifiers
    """
    print(os.getenv('ZYTE_KEY'))
    # Set up logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    
    url = f'https://camelcamelcamel.com/product/{amazon_id}'
    product_details = {}
    
    try:
        # Make API request
        ZYTE_KEY = os.getenv("ZYTE_KEY")
        api_response = requests.post(
            "https://api.zyte.com/v1/extract",
            auth=(ZYTE_KEY, ""),
            json={
                "url": url,
                "httpResponseBody": True,
            },
            timeout=60
        )
        api_response.raise_for_status()
        
        # Decode response
        response_data = api_response.json()
        if "httpResponseBody" not in response_data:
            logger.error("No response body in API response")
            return product_details
            
        http_response_body = b64decode(response_data["httpResponseBody"])
        
        # Parse HTML
        soup = BeautifulSoup(http_response_body, 'html.parser')
        
        # Try multiple ways to find the product details table
        table = (
            soup.find('table', class_='product_fields') or 
            soup.find('table', {'id': 'product_fields'}) or
            soup.find('table', string=lambda text: text and any(
                key in text.lower() for key in ["manufacturer", "isbn", "ean", "upc", "sku"]
            ))
        )
        
        if not table:
            logger.error("Product details table not found")
            # return product_details
        else:    
            # Define expected keys and their variations
            key_mappings = {
                'manufacturer': 'Manufacturer',
                'isbn': 'ISBN',
                'ean': 'EAN',
                'upc': 'UPC',
                'sku': 'SKU',
                'asin': 'ASIN'
            }
            
            # Process table rows
            for row in table.find_all('tr'):
                cols = row.find_all('td')
                if len(cols) >= 2:
                    # Get raw key and clean it
                    raw_key = cols[0].get_text(strip=True).lower()
                    raw_key = raw_key.replace(':', '').strip()
                    
                    # Clean up the value cell
                    value_cell = cols[1]
                    
                    # Remove any <wbr> tags
                    for wbr in value_cell.find_all('wbr'):
                        wbr.decompose()
                        
                    # Get clean value text
                    value = value_cell.get_text(strip=True)
                    value = value.replace('\u200b', '').strip()
                    
                    # Map the key to standard format if it exists in our mappings
                    for key_pattern, standard_key in key_mappings.items():
                        if key_pattern in raw_key:
                            if value:  # Only add if value is not empty
                                product_details[standard_key] = value
                                logger.debug(f"Found {standard_key}: {value}")
                            break

        # Extract price data
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

# Example usage with error handling
# def test_scraper(amazon_id):
#     try:
#         results = get_other_ids(amazon_id)
#         print(f"\nResults for Amazon ID {amazon_id}:")
#         if results:
#             # for key, value in results.items():
#             #     print(f"{key}: {value}")
#         else:
#             print("No product details found")
#     except Exception as e:
#         print(f"Error testing scraper: {str(e)}")

# # Test the function
# amazon_id = "B00008H2KY"
# test_scraper(amazon_id)