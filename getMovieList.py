import re
import json
import math
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

def getMovieList(movies_list_page, year):
    
    movies_list_page.goto(
        f'https://www.blu-ray.com/dvd/search.php?releaseyear={year}&submit=Search&action=search',
        timeout = 120000
    )

    movies_list_page.wait_for_selector('.bevel', timeout=60000)
    movies = []

    movies.extend(
        [
            movie.get_attribute('href')
            for movie in movies_list_page.query_selector_all('.bevel tbody tr td a')
        ]
    )

    total_results = movies_list_page.query_selector('.oswaldcollection').text_content()

    match = re.search(r'\d+', total_results)
    if match:
        movies_number = int(match.group())
        print(f'{movies_number} movies to scrap for year {year}')

        total_pages = math.ceil(movies_number / 20)
        if total_pages > 1:
            for page_no in range(1, total_pages):
                url = f'https://www.blu-ray.com/dvd/search.php?releaseyear={year}&submit=Search&action=search&page={page_no}'
                print(url)
                
                while True:  # Retry until successful
                    try:
                        movies_list_page.goto(url, wait_until="domcontentloaded")
                        movies_list_page.wait_for_selector('.bevel', timeout=120000)
                        
                        # If it reaches here, the page loaded successfully, break retry loop
                        break  
                    except PlaywrightTimeoutError:
                        print(f"Timeout occurred on page {page_no}, retrying...")
                
                movies.extend(
                    [
                        movie.get_attribute('href')
                        for movie in movies_list_page.query_selector_all('.bevel tbody tr td a')
                    ]
                )

    return movies


if __name__ == '__main__':
    from playwright.sync_api import sync_playwright
    from get_agents import get_agent

    with sync_playwright() as p:
        browser = p.chromium.launch()
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
        page = context.new_page()
        movies_list = getMovieList(page, 1998)

        with open('1998-list.json', 'w') as f:
            json.dump(movies_list, f, indent=4, ensure_ascii=False)