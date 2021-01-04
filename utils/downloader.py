from tqdm.contrib.telegram import tqdm
from config import bot_token
import requests

def local_download(url, chat_id):
    res = requests.get(url, allow_redirects=True, stream=True)
    total = int(res.headers.get('content-length', 0))
    block_size = 1024 #1 Kibibyte
    if res.status_code != 200: raise Exception("Error when downloading file.")
    progress_bar = tqdm(
        desc= "正在下载节目…",
        total = total, 
        unit='iB', 
        unit_scale=True,
        token = bot_token,
        chat_id = chat_id,
        bar_format= '{percentage:3.0f}%  {bar:8} {post_fix}',
        postfix= '\n{remaining_s}秒后下载完成'
    )
    with open('public/audio/audio-temp.mp3', 'wb') as f:
        for data in res.iter_content(block_size):
            progress_bar.update(len(data))
            f.write(data)
        progress_bar.set_postfix('')
        progress_bar.set_description('下载完毕！')
        progress_bar.disable=True
    progress_bar.close()
    if total != 0 and progress_bar.n != total:
        raise Exception("ERROR, something went wrong with progress bar.")
    return 'public/audio/audio-temp.mp3'
