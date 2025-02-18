import requests
import os
import random 
import logging
from dotenv import load_dotenv
load_dotenv()

apiKey = os.getenv('WEBSHARE_API_KEY')

logger = logging.getLogger("scrappers")

def get_proxies_credentials_list():
    """
    Fetches a list of proxy credentials from the Webshare API and returns them in a randomized order.
    The function sends a GET request to the Webshare API to retrieve a list of proxies. It then extracts
    the necessary credentials (server, username, and password) for each proxy and shuffles the list before
    returning it.
    Returns:
        list of dict: A list of dictionaries, each containing the following keys:
            - "server" (str): The proxy server address and port in the format "address:port".
            - "username" (str): The username for the proxy.
            - "password" (str): The password for the proxy.
    """

    response = requests.get(
        "https://proxy.webshare.io/api/v2/proxy/list/?mode=direct&page=1&page_size=25",
        headers={"Authorization": f"Token {apiKey}"}
    )

    logger.info(response)
    proxies = response.json()['results']
    
    proxies_creds = [
        {
            "server": f"{proxy['proxy_address']}:{proxy['port']}",
            "username": proxy['username'],
            "password": proxy['password']
        } for proxy in proxies
    ]
    random.shuffle(proxies_creds)

    return proxies_creds

print(get_proxies_credentials_list())