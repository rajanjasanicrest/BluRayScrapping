import json
import openpyxl

def write_data_to_file(data, year):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = f'DVD-{year}'

    headers = [
        'Title', 'Title Sub Heading', 'Production Company', 'Production Year', 'Film Time', 'Rating', 'Disc Release Date', 'Video Codec', 'Video Encoding', 'Video Resolution', 'Video Aspect Ratio', 'Original Aspect Ratio', 'Audio', 'Subtitles', 'Discs', 'Packaging', 'Playback', 'Genres', 'ISBN', 'EAN', 'UPC', 'SKU(Amazon)', 'eBay EPID', 'New Price', 'Used Price', '3rd Party Used Current', '3rd Party Used Average', 'Amazon Price Current', 'Amazon Price Average', 'Description', 'Director', 'Writer', 'Starring', 'Producers', 'Blu-Ray.com URL', 'Internet Movie Database URL', 'Rotten Tomatoes URL', 'SALIENT ID', 'Front Photo', 'Back Photo', 'Screenshots', ''
    ]

    ws.append(headers)
    
    for dvd in data:
        if dvd:
            row = [
                dvd.get('title', ''),
                dvd.get('subheading_title', ''),
                dvd.get('production', ''),
                dvd.get('production_year', ''),
                dvd.get('runtime', ''),
                dvd.get('age_rating', ''),
                dvd.get('release_date', ''),
                dvd.get('codec', ''),
                dvd.get('encoding', ''),
                dvd.get('resolution', ''),
                dvd.get('aspect_ratio', ''),
                dvd.get('original_aspect_ratio', ''),
                dvd.get('audio', ''),
                dvd.get('subtitles', ''),
                ','.join(dvd.get('discs', [])),
                ','.join(dvd.get('packaging', [])),
                ','.join(dvd.get('playback', [])),
                ','.join(dvd.get('genres', [])),
                dvd.get('isbn', ''),
                dvd.get('ean', ''),
                dvd.get('upc', ''),
                dvd.get('sku', ''),
                dvd.get('epid', ''),
                dvd.get('new_price', ''),
                dvd.get('used_price', ''),
                dvd.get('third_used_current_price', ''),
                dvd.get('third_used_average_price', ''),
                dvd.get('amazon_current_price', ''),
                dvd.get('amazon_average_price', ''),
                dvd.get('description', ''),
                dvd.get('directors', ''),
                dvd.get('writers', ''),
                dvd.get('starring', ''),
                dvd.get('producer', ''),
                dvd.get('blu_ray_url', ''),
                dvd.get('imdb_url', ''),
                dvd.get('rt_url', ''),
                dvd.get('', ''),
                dvd.get('front_s3_url', ''),
                dvd.get('back_s3_url', ''),
                ','.join(dvd.get('screenshot_s3_urls', [])),
            ]

            ws.append(row)

    file_name = f'excels/DVD-{year}.xlsx'
    wb.save(file_name)
    print(f'Data successfully written to {file_name}')

if __name__ == '__main__':
    with open('data/DVD-1998.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    write_data_to_file(data, 1998)