import re

def scrape_movie_from_list(movie, detail_page, year):
    
    movie_href = movie.get_attribute('href')
    if movie_href:
        detail_page.goto(movie_href)

        detail_page.wait_for_selector('#movie_info', timeout=30000)
        movie_info_section = detail_page.query_selector('#movie_info')

        movie_info_text = movie_info_section.inner_html()  
        movie_info_text = re.sub(r"<.*?>", "", movie_info_text).strip()
        movie_info_text = movie_info_text.replace("<br>", "\n")

        for text in movie_info_text:
            if text != '': print(text)


            