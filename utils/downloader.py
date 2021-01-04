from tqdm.contrib.telegram import tqdm, tqdm_telegram
from config import bot_token
import requests

def local_download(url, chat_id):
    res = requests.get(url, allow_redirects=True, stream=True)
    total = int(res.headers.get('content-length', 0))
    if res.status_code != 200: raise Exception("Error when downloading file.")
    progress_bar = tqdm(
        total = total, 
        unit='it', 
        unit_scale=total,
        token = bot_token,
        chat = chat_id
    )
    with open('public/audio/audio-temp.mp3', 'wb') as f:
        for data in res.iter_content(block_size):
            progress_bar.update(len(data))
            file.write(data)
    progress_bar.close()
    if total != 0 and progress_bar.n != total:
        print("ERROR, something went wrong")
    return file_path
