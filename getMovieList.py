import re
import math

def getMovieList(movies_list_page, year):
    
    movies_list_page.goto(
        f'https://www.blu-ray.com/dvd/search.php?releaseyear={year}&submit=Search&action=search'
    )

    movies = []

    movies.extend(
        movies_list_page.query_selector_all('.bevel tbody tr td a')
    )

    total_results = movies_list_page.query_selector('.oswaldcollection').text_content()

    match = re.search(r'\d+', total_results)
    if match:
        movies_number = int(match.group())
        print(f'{movies_number} movies to scrap for year {year}')

        total_pages = math.ceil(movies_number / 20)
        if total_pages > 1:
            for page_no in (1,total_pages):
                movies_list_page.goto(
                    f'https://www.blu-ray.com/dvd/search.php?releaseyear={year}&submit=Search&action=search&page={page_no}'
                )
                movies.extend(
                    movies_list_page.query_selector_all('.bevel tbody tr td a')
                )

    return movies
        



