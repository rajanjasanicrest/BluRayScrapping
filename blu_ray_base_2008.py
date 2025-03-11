from playwright.sync_api import sync_playwright
from get_agents import get_agent
from get_proxies import get_proxies_credentials_list
import random
import json
import os
from playwright_stealth.stealth import stealth_sync
from getMovieList import getMovieList
from scrape_movies import scrape_movie_from_list
import traceback
import logging
from excel_helper import write_data_to_file

logger = logging.getLogger(__name__)  # Use __name__ without quotes
logger.setLevel(logging.INFO)

def get_random_proxy():
    # Randomly select a proxy from the pool
    proxies_list = get_proxies_credentials_list()
    return random.choice(proxies_list)


def visit_bluray_website():
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True
        )  # Set headless=True for background execution
        context = browser.new_context(
            viewport={'width': 1280, 'height': 800},
            user_agent=get_agent(),
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

        release_years = [2008]

        for year in release_years:
            print('*'*50)
            print('scrapping for year ', year)
            scrapped_movies_list = []
            existing_data = []
            try:
                dir_path = f"data/"
                os.makedirs(dir_path, exist_ok=True)
                dir_path = f"excels/"
                os.makedirs(dir_path, exist_ok=True)

                with open(f'data/DVD-{year}.json', 'r', encoding='utf-8') as f:
                    existing_data = json.load(f)
            except Exception as e:
                print(e)
                print('scrapping for the first time')
            existing_movie_urls = [x['blu_ray_url'] for x in existing_data if x]
            scrapped_movies_list.extend(existing_data) 
            try:
                page = context.new_page()
                movies_list = []
                try:
                    with open(f'data/{year}-list.json', 'r', encoding='utf-8') as f:
                        movies_list = json.load(f)
                except Exception as e:
                    print(e)
                    print('scrapping for the first time')
                
                if not movies_list:
                    movies_list = getMovieList(page, year)
                    with open(f'data/{year}-list.json', 'w', encoding='utf-8') as f:
                        json.dump(movies_list, f, indent=4, ensure_ascii=False)

                page.close()
                print(len(movies_list))
                number_of_movies = len(movies_list) 
                for index, movie_href in enumerate(movies_list):
                    detail_page = context.new_page()
                    try:
                        if movie_href not in existing_movie_urls:
                            print(f"Scraping movie {index+1} of {number_of_movies} for year {year}" )
                            scrapped_movies_list.append(scrape_movie_from_list(movie_href, detail_page, year))
                    except Exception as e:
                        logging.error(f"Exception: {e.__class__.__name__} - {e}")
                        logging.error(traceback.format_exc())
                        return 'restart'
                    finally:
                        detail_page.close()

                    if index%40 == 0 and index!=0:
                        with open(f'data/DVD-{year}.json', 'w', encoding='utf-8') as f:
                            json.dump(scrapped_movies_list, f, indent=4, ensure_ascii=False)

                with open(f'data/DVD-{year}.json', 'w', encoding='utf-8') as f:
                    json.dump(scrapped_movies_list, f, indent=4, ensure_ascii=False)

                write_data_to_file(scrapped_movies_list, year)

                print(f"Successfully scrapped movies for year {year}")
            except Exception as e:
                logging.error(f"Exception: {e.__class__.__name__} - {e}")
                logging.error(traceback.format_exc())
                return 'restart'

            finally:
                page.close()

        browser.close()
        return 'Done'

if __name__ == "__main__":
    status = visit_bluray_website()
    while status not in ['Done']:
        print('-'*100)
        print('Restarting the Scraper')
        status = visit_bluray_website()
