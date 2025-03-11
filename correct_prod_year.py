import json
import re
import math
from tqdm import tqdm

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

def getMovieList(movies_list_page, year, existing=None):
    movies_list_page.goto(
        f'https://www.blu-ray.com/dvd/search.php?releaseyear={year}&submit=Search&action=search',
        timeout=120000
    )

    movies_list_page.wait_for_selector('.bevel', timeout=60000)
    movies = {'year': year}

    # Process the first page
    for movie in movies_list_page.query_selector_all('.bevel tbody tr td'):
        if movie.query_selector('a') and movie.query_selector('font'):
            url = movie.query_selector('a').get_attribute('href')
            production_year = movie.query_selector('font').text_content()[1:-1].strip()
            movies[url] = production_year

    # Get total number of results
    total_results = movies_list_page.query_selector('.oswaldcollection').text_content()
    match = re.search(r'\d+', total_results)
    
    if match:
        movies_number = int(match.group())
        tqdm.write(f'{movies_number} movies to scrape for year {year}')

        total_pages = math.ceil(movies_number / 20)
        if total_pages > 1:
            for page_no in tqdm(range(1, total_pages), desc="Scraping Pages", unit=" page"):
                url = f'https://www.blu-ray.com/dvd/search.php?releaseyear={year}&submit=Search&action=search&page={page_no}'
                tqdm.write(f"Scraping Page: {page_no}")

                while True:  # Retry mechanism for timeout errors
                    try:
                        movies_list_page.goto(url, timeout=120000)
                        movies_list_page.wait_for_selector('.bevel', timeout=120000)
                        break  # Break loop if successful
                    except PlaywrightTimeoutError:
                        tqdm.write(f"Timeout occurred on page {page_no}, retrying...")

                # Scrape movies from the current page
                for movie in movies_list_page.query_selector_all('.bevel tbody tr td'):
                    if movie.query_selector('a') and movie.query_selector('font'):
                        url = movie.query_selector('a').get_attribute('href')
                        production_year = movie.query_selector('font').text_content()[1:-1].strip()
                        movies[url] = production_year
                    if movie.query_selector('a') and not movie.query_selector('font'):
                        url = movie.query_selector('a').get_attribute('href')
                        movies[url] = year
    return movies

        
if __name__ == '__main__':
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        print('Opening browser')
        browser = p.chromium.launch(
            headless=True
        )  # Set headless=True for background execution
        context = browser.new_context(
            viewport={'width': 1280, 'height': 800},
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
        print('Browser opened, starting core process')
        # years = [1996, 1997, 1998]
        years = [1998]
        for year in years:
            print(f'Processing year {year}')
            movies_dict = None
            try:
                with open(f'data/DVD-{year}-temp.json', 'r', encoding='utf-8') as f:
                    movies_dict = json.load(f)
            except Exception as e:
                print(e)
                print('Scraping for the first time')

            if not movies_dict:
                movies_dict = getMovieList(context.new_page(), year)

            with open(f'data/DVD-{year}-temp.json', 'w', encoding='utf-8') as f:
                json.dump(movies_dict, f, indent=4)

            with open(f'data/DVD-{year}.json', 'r', encoding='utf-8') as f:
                existing_data = json.load(f)
            
            for movie in existing_data:
                if movie:
                    movie['production_year'] = movies_dict[movie['blu_ray_url']]

            with open(f'data/DVD-{year}.json', 'w', encoding='utf-8') as f:
                json.dump(existing_data, f, indent=4)
        print('Done')
