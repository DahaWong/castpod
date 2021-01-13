from tqdm.contrib.telegram import tqdm
from config import bot_token
import requests

def local_download(url, context):
    res = requests.get(url, allow_redirects=True, stream=True)
    if res.status_code != 200: raise Exception(f"Error when downloading audio, status: {res.status_code}.")
    block_size = 1024 #1 Kibibyte
    if context.user_data: 
        user = context.user_data['user']
        chat_id = user.user_id
        total = int(res.headers.get('content-length', 0))
        progress_bar = tqdm(
            total = total, 
            unit='iB',
            token = bot_token,
            chat_id = chat_id,
            bar_format= '{percentage:3.0f}% |{bar:8}|'
        )
        with open('public/audio/audio-temp.mp3', 'wb') as f:
            for data in res.iter_content(block_size):
                progress_bar.update(len(data))
                f.write(data)
            message_id = progress_bar.tgio.message_id
        context.bot.delete_message(chat_id, message_id)
        progress_bar.close()
        if total != 0 and progress_bar.n != total:
            raise Exception("ERROR: something went wrong with progress bar.")
    else:
        with open('public/audio/audio-temp.mp3', 'wb') as f:
            for data in res.iter_content(block_size):
                f.write(data)
    return 'public/audio/audio-temp.mp3'
