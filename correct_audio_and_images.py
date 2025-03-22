from playwright.sync_api import sync_playwright
from get_agents import get_agent
from get_proxies import get_proxies_credentials_list
import random
import json
import os
from getMovieList import getMovieList
from scrape_movies import scrape_movie_from_list
import traceback
import logging
from excel_helper import write_data_to_file
from get_epid import get_epid
import boto3
import botocore

logger = logging.getLogger(__name__)  # Use __name__ without quotes
logger.setLevel(logging.INFO)

def get_random_proxy():
    # Randomly select a proxy from the pool
    proxies_list = get_proxies_credentials_list()
    return random.choice(proxies_list)

def delete_s3_object(bucket_name, object_key):
    """Deletes an object from S3 if it exists."""
    s3 = boto3.client("s3")

    try:
        # Check if the object exists
        s3.head_object(Bucket=bucket_name, Key=object_key)
        
        # Object exists, proceed with deletion
        s3.delete_object(Bucket=bucket_name, Key=object_key)
        print(f"Deleted: {object_key} from {bucket_name}")

    except botocore.exceptions.ClientError as e:
        # Handle 'Not Found' case
        if e.response['Error']['Code'] == "404":
            print(f"Object {object_key} does not exist in {bucket_name}.")
        else:
            raise  # Re-raise other errors

def visit_bluray_website(year):
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True
            )  # Set headless=True for background execution
            proxy = get_random_proxy()
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
                    "name": "listlayout_7",
                    "value": "simple",
                    "domain": ".blu-ray.com",
                    "path": "/",
                    "max_age": 30 * 24 * 60 * 60
                },
            ])
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
            # existing_movie_urls = [x['blu_ray_url'] for x in existing_data if x]
            # scrapped_movies_list.extend(existing_data) 
            try:
                import requests, boto3, io
                from scrape_movies import sanitize_filename
                page = context.new_page()
                movies_list = []
                aws_bucket = 'salient-blu-ray-scrapping'
                for data in existing_data:
                    if not data:
                        continue
                    blu_ray_id = data['blu_ray_url'].split('/')[-2]
                    print(f'Processing {data['blu_ray_url']}')
                    if 'slip_s3_url' not in data.keys():
                        

                        image_urls = {}
                        import re

                        page.goto(data['blu_ray_url'], wait_until='domcontentloaded', timeout=600000)

                        if data['audio'] == data['subtitles']:
                            audio_locator = page.query_selector_all('div#shortaudio')
                            if audio_locator:
                                raw_text = audio_locator[0].inner_text().strip()  # Extract plain text
                                if raw_text:
                                    audio = [line.strip() for line in raw_text.split("\n") if line.strip()]


                                data['audio'] =  ", ".join(audio)
                                
                        scripts = page.locator("script").all_inner_texts()
                        # Combine all script texts into one string
                        script_text = "\n".join(scripts)

                        # Define a dictionary to store categorized URLs
                        image_urls = {
                            "overview_url": None,
                            "back_url": None,
                            "slip_url": None,
                            "slipback_url": None
                        }
                        overview_s3_url = None
                        back_s3_url = None
                        slip_s3_url = None
                        slipback_s3_url = None

                        # Define patterns for categorization
                        patterns = {
                            "overview_url": r"https://images\.static-bluray\.com/movies/dvdcovers/\d+_overview\.jpg\?t=\d+",
                            "back_url": r"https://images\.static-bluray\.com/movies/dvdcovers/\d+_back\.jpg\?t=\d+",
                            "slip_url": r"https://images\.static-bluray\.com/movies/dvdcovers/\d+_slip\.jpg\?t=\d+",
                            "slipback_url": r"https://images\.static-bluray\.com/movies/dvdcovers/\d+_slipback\.jpg\?t=\d+"
                        }

                        # Extract and categorize URLs
                        for key, pattern in patterns.items():
                            match = re.search(pattern, script_text)
                            if match:
                                image_urls[key] = match.group(0)

                        print( image_urls)

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

                                file_name = f'DVD/{year}/{sanitize_filename(data['title'])}/{sanitize_filename(data['title'])}_{blu_ray_id}_back{ext}'
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
                                data['back_s3_url'] = back_s3_url

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

                                file_name = f'DVD/{year}/{sanitize_filename(data['title'])}/{sanitize_filename(data['title'])}_{blu_ray_id}_slip{ext}'
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
                                data['slip_s3_url'] = slip_s3_url

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

                                file_name = f'DVD/{year}/{sanitize_filename(data['title'])}/{sanitize_filename(data['title'])}_{blu_ray_id}_slipback{ext}'
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
                                data['slipback_s3_url'] = slipback_s3_url
                        
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

                                file_name = f'DVD/{year}/{sanitize_filename(data['title'])}/{sanitize_filename(data['title'])}_{blu_ray_id}_overview{ext}'
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
                                data['overview_s3_url'] = overview_s3_url

                        data['back_s3_url'] = back_s3_url if back_s3_url else ''
                        data['slip_s3_url'] = slip_s3_url if slip_s3_url else ''
                        data['overview_s3_url'] = overview_s3_url if overview_s3_url else ''
                        data['slipback_s3_url'] = slipback_s3_url if slipback_s3_url else '' 

                        with open(f'data/DVD-{year}.json', 'w', encoding='utf-8') as f:
                            json.dump(existing_data, f, indent=4, ensure_ascii=False)

                page.close()

                with open(f'data/DVD-{year}.json', 'w', encoding='utf-8') as f:
                    json.dump(existing_data, f, indent=4, ensure_ascii=False)

                write_data_to_file(existing_data, year)

                print(f"Successfully scrapped movies for year {year}")
            except Exception as e:
                logging.error(f"Exception: {e.__class__.__name__} - {e}")
                logging.error(traceback.format_exc())
                return 'restart'

            finally:
                page.close()

            browser.close()
            return 'Done'
    except Exception as e:
        print(e)
        return 'restart'

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Blu-ray.com website scraper for Blu-ray movies")
    parser.add_argument("--year", type=int, required=True, help="Year to scrape data for (e.g., 2024)")

    args = parser.parse_args()


    year = args.year
    # year = 2016
    # years = list(range(2016,2025))
    # for year in years:
    status = visit_bluray_website(year)
    while status not in ['Done']:
        print('-'*100)
        print('Restarting the Scraper')
        status = visit_bluray_website(year)
