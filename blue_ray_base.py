from playwright.sync_api import sync_playwright
from get_agents import get_agent
from get_proxies import get_proxies_credentials_list
import random
import json
import os
from playwright_stealth.stealth import stealth_sync
from getMovieList import getMovieList
from scrape_movies import scrape_movie_from_list

def get_random_proxy():
    # Randomly select a proxy from the pool
    proxies_list = get_proxies_credentials_list()
    return random.choice(proxies_list)


def visit_bluray_website():
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=False
        )  # Set headless=True for background execution
        context = browser.new_context(
            viewport={'width': 1280, 'height': 800},
            user_agent=get_agent(),
            proxy=get_random_proxy()
        )
        context.add_cookies([
            {
                "name": "country",
                "value": "us",
                "domain": ".blu-ray.com",
                "path": "/",
                "max_age": 30 * 24 * 60 * 60
            },
            {
                "name": "listlayout_21",
                "value": "simple",
                "domain": ".blu-ray.com",
                "path": "/",
                "max_age": 30 * 24 * 60 * 60
            },


        ])


        # release_years = [1996, 1997, 1998]
        release_years = [1996]

        for year in release_years:
            print('*'*50)
            print('scrapping for year ', year)
            page = context.new_page()
            stealth_sync(page)  
            try:
                movies_list = getMovieList(page, year)
                print(len(movies_list))
                print(movies_list)

                # scrape_movie_from_list(movies_list)

                print(f"Successfully scrapped movies for year {year}")
            except Exception as e:
                print(e)
            finally:
                page.close()

        browser.close()

if __name__ == "__main__":
    visit_bluray_website()
