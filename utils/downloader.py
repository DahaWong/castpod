from tqdm.contrib.telegram import tqdm, tqdm_telegram
from config import bot_token
import requests

def local_download(url, chat_id):
    res = requests.get(url, allow_redirects=True, stream=True)
    total_size_in_bytes= int(res.headers.get('content-length', 0))
    print(total_size_in_bytes)
    if res.status_code != 200: 
        raise Exception("Error when downloading file.")
    progress_bar = tqdm(
        total = total_size_in_bytes, 
        unit='it', 
        unit_scale=True,
        token = bot_token,
        chat = chat_id
        )
    print(progress_bar)
    file_path = f'public/audio/audio-temp.mp3'
    with open(file_path, 'wb') as f:
        for data in res.iter_content(block_size):
            progress_bar.update(len(data))
            file.write(data)
    return file_path

import requests

url = "http://www.ovh.net/files/10Mb.dat" #big file test
block_size = 1024 #1 Kibibyte
progress_bar = tqdm(total=total_size_in_bytes, unit='it', unit_scale=True)
with open('test.dat', 'wb') as file:
    for data in response.iter_content(block_size):
        progress_bar.update(len(data))
        file.write(data)
progress_bar.close()
if total_size_in_bytes != 0 and progress_bar.n != total_size_in_bytes:
    print("ERROR, something went wrong")
