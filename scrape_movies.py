import io
import os
import re
import json
import requests
from dotenv import load_dotenv
from get_other_ids_from_ccc_v2 import get_other_ids
from ccc_scrape_upc import process_camel_search
from get_epid import get_epid
import boto3
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
import re

def sanitize_filename(title):
    # Remove all characters except alphanumeric, spaces, and underscores
    sanitized_title = re.sub(r'[^\w\s]', '', title)
    # Replace multiple spaces with a single space
    sanitized_title = re.sub(r'\s+', ' ', sanitized_title)
    # Strip leading and trailing spaces
    sanitized_title = sanitized_title.strip()
    # Optionally replace spaces with underscores
    sanitized_title = sanitized_title.replace(' ', '_')
    return sanitized_title

load_dotenv()

def get_text_between(td_element, start_text, end_text=None):

    # Ensure the element exists
    if not td_element:
        return ""

    # Get all text content inside the <td>
    full_text = td_element.inner_text().strip()

    # Find the start index
    start_idx = full_text.find(start_text)
    if start_idx == -1:
        return ""  # If start text is not found, return empty string

    # Determine the end index
    if end_text:
        end_idx = full_text.find(end_text, start_idx + len(start_text))
    else:
        end_idx = -1  # If no end text, capture everything after start_text

    # Extract the relevant text
    extracted_text = full_text[start_idx + len(start_text):].strip() if end_idx == -1 else full_text[start_idx + len(start_text):end_idx].strip()

    return extracted_text

def scrape_movie_from_list(movie_href, detail_page, year):
    try:
        blu_ray_id = movie_href.split('/')[-2]
        aws_bucket = 'salient-blu-ray-scrapping'
        print('-'*50)
        print(movie_href)
        if movie_href:
            detail_page.goto(movie_href, wait_until="domcontentloaded")
        
            movie_details = {
                'releaseYear': year,
                'blu_ray_url': movie_href,
                'missing_links': False
            }        

            # detail_page.wait_for_selector('#movie_info', timeout=30000)
            movie_info_section = detail_page.query_selector('#movie_info')
            '''
            movie production, runtime, release date etc stuff below.
            '''
            movie_details["production"] = ''
            core_info = detail_page.query_selector('.subheading.grey')
            core_text = core_info.text_content()
            if '|' in core_text:
                core_texts = list(map(str.strip, core_text.split("|")))
            else:
                core_texts = [core_text]

            for text in core_texts:
                if re.fullmatch(r"\d{4}(-\d{4})?", text):  # Production year (e.g., 2003 or 2003-2008)
                    movie_details["production_year"] = text
                elif 'min' in text:  # Runtime
                    movie_details["runtime"] = text
                elif 'rated' in text.lower():  # Age rating
                    movie_details["age_rating"] = text
                elif re.fullmatch(r"[A-Za-z]+ \d{2}, \d{4}", text):  # Release date (e.g., Feb 03, 2009)
                    movie_details["release_date"] = text
                elif not movie_details["production"]:  # First non-matching text is assumed to be production company
                    movie_details["production"] = text

            '''
            movie general info stuff below.
            '''
            movie_config_td = detail_page.query_selector("td[width='228px']")
            #getting dynamic subheaders:
            subheaders_list = movie_config_td.query_selector_all(".subheading")
            subheaders_list = [x.text_content() for x in subheaders_list]

            n = len(subheaders_list)
            for i in range(n):
                if subheaders_list[i] in ['Video', 'Discs', 'Disc', 'Playback', 'Packaging']:
                    next_header = subheaders_list[i+1] if i+1 < n else None
                    specs = get_text_between(movie_config_td, subheaders_list[i] , next_header)
                    if subheaders_list[i] == 'Video':
                        specs = specs.split('\n')
                        for spec in specs:
                            if 'Codec' in  spec:
                                movie_details['codec'] = spec.split(':', 1)[-1].strip()
                            elif 'Encoding' in  spec:
                                movie_details['encoding'] = spec.split(':', 1)[-1].strip()
                            elif 'Resolution' in  spec:
                                movie_details['resolution'] = spec.split(':', 1)[-1].strip()
                            elif 'Aspect ratio' in  spec:
                                movie_details['aspect_ratio'] = spec.split(':', 1)[-1].strip()
                            elif 'Original aspect ratio' in  spec:
                                movie_details['original_aspect_ratio'] = spec.split(':', 1)[-1].strip()

                    elif subheaders_list[i] == 'Discs' or subheaders_list[i] == 'Disc':
                        specs = specs.split('\n')
                        for spec in specs:
                            movie_details.setdefault('discs', []).append(spec)
                    
                    elif subheaders_list[i] == 'Playback':
                        specs = specs.split('\n')
                        for spec in specs:
                            movie_details.setdefault('playback', []).append(spec)
                    
                    elif subheaders_list[i] == 'Packaging':
                        specs = specs.split('\n')
                        for spec in specs:
                            movie_details.setdefault('packaging', []).append(spec)

            # audio specs
            audio_locator = detail_page.query_selector_all('div#shortaudio')
            if audio_locator:
                raw_text = audio_locator[0].inner_text().strip()  # Extract plain text
                if raw_text:
                    audio = [line.strip() for line in raw_text.split("\n") if line.strip()]


                movie_details['audio'] =  ", ".join(audio)

            # movie specs
            subtitles_locator = detail_page.query_selector_all('div#shortsubs')
            if subtitles_locator:
                subtitles_texts = [subtitle.inner_text() for subtitle in subtitles_locator]
                movie_details['subtitles'] =  ", ".join(subtitles_texts)

            '''
            movie Price related stuff beloe
            '''
            pricing_td = detail_page.query_selector("td[width='266px']")
            pricing_text = get_text_between(pricing_td, 'Price', 'Price')
            pricing_text = pricing_text.split('\n')
            for price_text in pricing_text:
                if 'Used' in price_text:
                    movie_details["used_price"] = (price_text.split("$")[-1].strip().split()[0]) if "Used" in price_text else movie_details.get("used_price")
                if 'New' in price_text:
                    movie_details["new_price"] = (price_text.split("$")[-1].strip().split()[0]) if "New" in price_text else movie_details.get("new_price")

            '''
            movie specific info related stuff below
            '''
            title = movie_info_section.query_selector('h3').text_content()
            subheading_title = detail_page.query_selector('.subheadingtitle')
            movie_details['subheading_title'] = subheading_title.text_content() if subheading_title else ''
            movie_details['title'] = title
            movie_info_text = movie_info_section.inner_text()  
            # movie_info_text = movie_info_text.replace("<br>", "\n").replace('&nbsp;', ' ').replace('&amp', '&')
            # movie_info_text = re.sub(r"<.*?>", "", movie_info_text).strip()
            movie_info_text = [x for x in movie_info_text.split('\n') if x != '' and 'Screenshots' not in x]
            description_texts = []
            stop_keywords = {"Directors:", "Producers:", "Starring:", "Writers:", "Director:", "Producer:", "Writer:", 'Narrator:'}

            for x in movie_info_text[1:]:
                if any(keyword in x for keyword in stop_keywords):
                    break
                description_texts.append(x)

            movie_details['description'] = '\n'.join(description_texts)

            # movie_details['description'] = movie_info_text[1].strip() if 'Screenshots' not in movie_info_text[1] else movie_info_text[2].strip()
            for text in movie_info_text:
                if 'Director:' in text or 'Directors:' in text:
                    movie_details['directors'] = text.split(':')[1].strip()
                elif 'Starring:' in text:
                    movie_details['starring'] = text.split(':')[1].strip()
                elif 'Writers:' in text or 'Writer:' in text:
                    movie_details['writers'] = text.split(':')[1].strip()
                elif 'Producers:' in text or 'Producer:' in text:
                    movie_details['producer'] = text.split(':')[1].strip()

            '''
            movie amazon buy link and rating
            '''
            amzn_link = detail_page.query_selector('#movie_buylink')
            if amzn_link:
                amzn_link = amzn_link.get_attribute('href')
                amzn_link = requests.get(amzn_link)
                amazon_id = amzn_link.url.split('?')[0].split('/')[-1]
                movie_details['amazon_id'] = amazon_id

                other_ids = get_other_ids(amazon_id)
                fields_to_copy = ['UPC', 'Manufacturer', 'ISBN', 'EAN', 'SKU']
                movie_details.update({k.lower(): other_ids.get(k, '') for k in fields_to_copy})
                upc = other_ids.get('UPC', None)
                movie_details['amazon_current_price'] = other_ids.get('amazon_current_price', '')
                movie_details['amazon_average_price'] = other_ids.get('amazon_average_price', '')
                movie_details['third_used_current_price'] = other_ids.get('third_used_current_price', '')
                movie_details['third_used_average_price'] = other_ids.get('third_used_average_price', '')

            # need logic to get ebay item number and do something with it. Camel Camel Camel does not have support to search items using UPC id.
            ebay_link_element = detail_page.query_selector('a[href*="ebay.com/sch/"]')
            if ebay_link_element:
                ebay_link = ebay_link_element.get_attribute('href')
                if not movie_details.get('upc', None): upc = ebay_link.split('_nkw=')[1].split('&')[0]
                movie_details['upc'] = upc
                
                if not amzn_link:
                    ccc_details = process_camel_search(f'https://camelcamelcamel.com/search?sq=DVD {upc} {movie_details["title"]}')
                    if ccc_details['success']: 
                        fields_to_copy = ['Manufacturer', 'ISBN', 'EAN', 'SKU']
                        other_ids = ccc_details['details']
                        movie_details.update({k.lower(): other_ids.get(k, '') for k in fields_to_copy})
                        movie_details['amazon_current_price'] = other_ids.get('amazon_current_price', '')
                        movie_details['amazon_average_price'] = other_ids.get('amazon_average_price', '')
                        movie_details['third_used_current_price'] = other_ids.get('third_used_current_price', '')
                        movie_details['third_used_average_price'] = other_ids.get('third_used_average_price', '')

            if not amzn_link and not ebay_link_element:
                movie_details['missing_links'] = True

            '''
            Getting top3 movie genres:
            '''
            genres=detail_page.query_selector_all('.genreappeal')[:3]
            genres=[x.text_content() for x in genres]
            movie_details['genres']=genres

            '''
            getting front and large image
            '''
            scripts = detail_page.locator("script").all_inner_texts()
            # Combine all script texts into one string
            script_text = "\n".join(scripts)

            # Define a dictionary to store categorized URLs
            image_urls = {
                "front_url": None,
                "overview_url": None,
                "back_url": None,
                "slip_url": None,
                "slipback_url": None
            }
            overview_s3_url = None
            front_s3_url = None
            back_s3_url = None
            slip_s3_url = None
            slipback_s3_url = None

            # Define patterns for categorization
            patterns = {
                "front_url": r"https://images\.static-bluray\.com/movies/covers/\d+_front\.jpg\?t=\d+",
                "overview_url": r"https://images\.static-bluray\.com/movies/covers/\d+_overview\.jpg\?t=\d+",
                "back_url": r"https://images\.static-bluray\.com/movies/covers/\d+_back\.jpg\?t=\d+",
                "slip_url": r"https://images\.static-bluray\.com/movies/covers/\d+_slip\.jpg\?t=\d+",
                "slipback_url": r"https://images\.static-bluray\.com/movies/covers/\d+_slipback\.jpg\?t=\d+"
            }

            # Extract and categorize URLs
            for key, pattern in patterns.items():
                match = re.search(pattern, script_text)
                if match:
                    image_urls[key] = match.group(0)

            print( image_urls)
            
            if image_urls.get('front_url', None):
                front_url = image_urls['front_url']
                print('front_url:', front_url)
                back_s3_url = ''
                response = requests.get(front_url)
                if response.status_code == 200:
                    image_content = response.content

                    _,ext = os.path.split(front_url)
                    if '?' in ext: ext = ext.split('?')[0]
                    ext = ext if ext else '.jpg'

                    s3_client = boto3.client('s3')

                    file_name = f'DVD/{year}/{sanitize_filename(movie_details['title'])}/{sanitize_filename(movie_details['title'])}_{blu_ray_id}_back{ext}'
                    contenttype = f"image/jpeg" if ext == '.jpg' else f"image/{ext[1:]}"
                    s3_client.upload_fileobj(
                        io.BytesIO(image_content),
                        aws_bucket,
                        file_name,
                        ExtraArgs = {
                            'ContentType':contenttype,
                            'ContentDisposition': 'inline'
                        }
                    )
                
                    front_s3_url = f"https://{aws_bucket}.s3.amazonaws.com/{file_name}"
                    movie_details['front_s3_url'] = front_s3_url
                    
            if image_urls.get('back_url', None):
                back_url = image_urls['back_url']
                print('back_url:', back_url)
                back_s3_url = ''
                response = requests.get(back_url)
                if response.status_code == 200:
                    image_content = response.content

                    _,ext = os.path.split(back_url)
                    if '?' in ext: ext = ext.split('?')[0]
                    ext = ext if ext else '.jpg'

                    s3_client = boto3.client('s3')

                    file_name = f'4K/{year}/{sanitize_filename(movie_details['title'])}/{sanitize_filename(movie_details['title'])}_{blu_ray_id}_back{ext}'
                    contenttype = f"image/jpeg" if ext == '.jpg' else f"image/{ext[1:]}"
                    s3_client.upload_fileobj(
                        io.BytesIO(image_content),
                        aws_bucket,
                        file_name,
                        ExtraArgs = {
                            'ContentType':contenttype,
                            'ContentDisposition': 'inline'
                        }
                    )
                
                    back_s3_url = f"https://{aws_bucket}.s3.amazonaws.com/{file_name}"
                    movie_details['back_s3_url'] = back_s3_url

            if image_urls.get('slip_url', None):
                slip_url = image_urls['slip_url']
                print('slip_url:', slip_url)
                slip_s3_url = ''
                response = requests.get(slip_url)
                if response.status_code == 200:
                    image_content = response.content

                    _,ext = os.path.split(slip_url)
                    if '?' in ext: ext = ext.split('?')[0]
                    ext = ext if ext else '.jpg'

                    s3_client = boto3.client('s3')

                    file_name = f'4K/{year}/{sanitize_filename(movie_details['title'])}/{sanitize_filename(movie_details['title'])}_{blu_ray_id}_slip{ext}'
                    contenttype = f"image/jpeg" if ext == '.jpg' else f"image/{ext[1:]}"
                    s3_client.upload_fileobj(
                        io.BytesIO(image_content),
                        aws_bucket,
                        file_name,
                        ExtraArgs = {
                            'ContentType':contenttype,
                            'ContentDisposition': 'inline'
                        }
                    )
                
                    slip_s3_url = f"https://{aws_bucket}.s3.amazonaws.com/{file_name}"
                    movie_details['slip_s3_url'] = slip_s3_url

            if image_urls.get('slipback_url', None):
                slipback_url = image_urls['slipback_url']
                print('slipback_url:', slipback_url)
                slipback_s3_url = ''
                response = requests.get(slipback_url)
                if response.status_code == 200:
                    image_content = response.content

                    _,ext = os.path.split(slipback_url)
                    if '?' in ext: ext = ext.split('?')[0]
                    ext = ext if ext else '.jpg'

                    s3_client = boto3.client('s3')

                    file_name = f'4K/{year}/{sanitize_filename(movie_details['title'])}/{sanitize_filename(movie_details['title'])}_{blu_ray_id}_slipback{ext}'
                    contenttype = f"image/jpeg" if ext == '.jpg' else f"image/{ext[1:]}"
                    s3_client.upload_fileobj(
                        io.BytesIO(image_content),
                        aws_bucket,
                        file_name,
                        ExtraArgs = {
                            'ContentType':contenttype,
                            'ContentDisposition': 'inline'
                        }
                    )
                
                    slipback_s3_url = f"https://{aws_bucket}.s3.amazonaws.com/{file_name}"
                    movie_details['slipback_s3_url'] = slipback_s3_url
            
            if image_urls.get('overview_url', None):
                overview_url = image_urls['overview_url']
                print('overview_url:', overview_url)
                overview_s3_url = ''
                response = requests.get(overview_url)
                if response.status_code == 200:
                    image_content = response.content

                    _,ext = os.path.split(overview_url)
                    if '?' in ext: ext = ext.split('?')[0]
                    ext = ext if ext else '.jpg'

                    s3_client = boto3.client('s3')

                    file_name = f'4K/{year}/{sanitize_filename(movie_details['title'])}/{sanitize_filename(movie_details['title'])}_{blu_ray_id}_overview{ext}'
                    contenttype = f"image/jpeg" if ext == '.jpg' else f"image/{ext[1:]}"
                    s3_client.upload_fileobj(
                        io.BytesIO(image_content),
                        aws_bucket,
                        file_name,
                        ExtraArgs = {
                            'ContentType':contenttype,
                            'ContentDisposition': 'inline'
                        }
                    )
                
                    overview_s3_url = f"https://{aws_bucket}.s3.amazonaws.com/{file_name}"
                    movie_details['overview_s3_url'] = overview_s3_url

            movie_details['front_s3_url'] = front_s3_url if front_s3_url else ''
            movie_details['back_s3_url'] = back_s3_url if back_s3_url else ''
            movie_details['slip_s3_url'] = slip_s3_url if slip_s3_url else ''
            movie_details['overview_s3_url'] = overview_s3_url if overview_s3_url else ''
            movie_details['slipback_s3_url'] = slipback_s3_url if slipback_s3_url else '' 

            '''
            getting screenshots
            '''
            screenshots = detail_page.query_selector_all('#movie_info table tbody tr td img')
            screenshots = [x.get_attribute('src') for x in screenshots]
            screenshot_s3_urls = []
            if screenshots:
                #upload to s3 bucket
                for index, sc in enumerate(screenshots):
                    print(f'screenshot {index}:', sc )
                    response = requests.get(sc)
                    if response.status_code == 200:
                        image_content = response.content

                        _,ext = os.path.split(sc)
                        ext = ext if ext else '.jpg'

                        s3_client = boto3.client('s3')

                        file_name = f'4K/{year}/{sanitize_filename(title)}/{sanitize_filename(title)}_{blu_ray_id}_screenshot_{index}{ext}'
                        contenttype = f"image/jpeg" if ext == '.jpg' else f"image/{ext[1:]}"
                        s3_client.upload_fileobj(
                            io.BytesIO(image_content),
                            aws_bucket,
                            file_name,
                            ExtraArgs = {
                                'ContentType': contenttype,
                                'ContentDisposition': 'inline'
                            }
                        )
                        screenshot_s3_urls.append(f"https://{aws_bucket}.s3.amazonaws.com/{file_name}")
                        movie_details['screenshot_s3_urls'] = screenshot_s3_urls

            '''Getting IMDB and rotten tomatoes URL'''
            imdb_atag = detail_page.query_selector('#imdb_icon')
            if imdb_atag:
                imdb_url = imdb_atag.get_attribute('href')
                movie_details['imdb_url'] = imdb_url
                
            rt_atag = detail_page.query_selector('#rt_icon')
            if rt_atag:
                rt_url = rt_atag.get_attribute('href')
                movie_details['rt_url'] = rt_url

            '''
            Get EPID
            '''
            # Then check if any exist before trying to access the first one
            if movie_details.get('upc',None):
                epid = get_epid(movie_details['upc'], movie_details['title'], year, movie_details['production'])
                if epid:
                    movie_details['epid'] = epid

            for key, value in movie_details.items():    
                print(f'{key}: {value}')

        return movie_details

    except PlaywrightTimeoutError:
        file_path = f'data/{year}-missed-movies.json'

        missed_movies = []
        if os.path.exists(file_path) and os.path.getsize(file_path) > 0:
            with open(file_path, 'r', encoding='utf-8') as f:
                try:
                    missed_movies = json.load(f)
                    if not isinstance(missed_movies, list):
                        missed_movies = []
                except json.JSONDecodeError:
                    missed_movies = []

        missed_movies.append(movie_href)

        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(missed_movies, f, indent=4)
        return None

    except Exception as e:
        print(e)


# if __name__ == '__main__':
#     from playwright.sync_api import sync_playwright

#     with sync_playwright() as p:
#         browser = p.chromium.launch(
#             headless=True
#         )  # Set headless=True for background execution
#         context = browser.new_context(
#             viewport={'width': 1280, 'height': 800},
#         )
#         context.add_cookies([
#             {
#                 "name": "country",
#                 "value": "us",
#                 "domain": ".blu-ray.com",
#                 "path": "/",
#                 "max_age": 30 * 24 * 60 * 60
#             },
#             {
#                 "name": "listlayout_21",
#                 "value": "simple",
#                 "domain": ".blu-ray.com",
#                 "path": "/",
#                 "max_age": 30 * 24 * 60 * 60
#             },
#         ])
#         page = context.new_page()
#         print(scrape_movie_from_list('https://www.blu-ray.com/dvd/Joseph-Campbell-Sukhavati-DVD/19096/', page, 2007))

#         page.close()