from tqdm.contrib.telegram import tqdm
import requests
from bs4 import BeautifulSoup
import errno
import os
import re
from functools import wraps
from castpod.models import User
from config import bot_token

def validate_user(func):
    @wraps(func)
    def wrapped(update, context, *args, **kwargs):
        user = User.objects(user_id=update.message.from_user.id).first()
        if not user:
            user = User(
                user_id=update.message.from_user.id,
                name=update.message.from_user.first_name,
                username=update.message.from_user.username
            ).save()
        return func(update, context, *args, **kwargs)
    return wrapped


# iTunes Search API

api_root = 'https://itunes.apple.com/search?'
endpoints = {
    'search_podcast': 'media=podcast&limit=25&term='
}


def search_itunes(keyword: str):
    res = requests.get(f"{api_root}{endpoints['search_podcast']}{keyword}")
    status = str(res.status_code)
    if not status.startswith('2'):
        return None
    results = res.json()['results']
    return results

# Spotify Search API
# def spotify_search(keyword:str):
#   headersAPI = {
#     'accept': 'application/json',
#     'Authorization': 'Bearer '+ 'BQC6unM9WV8GYYIrRhIpR-uJaQ9FLP7KF2xTlIanMXkxi5K1ii5O7ES0VxB3SVdacnvEGGOPqHcl5Hx9LKE',
#   }
#   response = requests.get(
#     'https://api.spotify.com/v1/search',
#     headers=headersAPI,
#     params=(
#       ('q', keyword),
#       ('type', 'show')
#     ),
#     verify=True
#   )
#   print(response.json())


# Local Download


def local_download(episode, context):
    res = requests.get(episode.audio.url, allow_redirects=True, stream=True)
    if res.status_code != 200:
        raise Exception(
            f"Error when downloading audio, status: {res.status_code}.")
    block_size = 1024  # 1 Kibibyte
    path = f"public/audio/{context.user_data['podcast']}/{episode.title}.mp3"
    if not os.path.exists(os.path.dirname(path)):
        try:
            os.makedirs(os.path.dirname(path))
        except OSError as exc:  # Guard against race condition
            if exc.errno != errno.EEXIST:
                raise
    if context.user_data:
        total = int(res.headers.get('content-length', 0))
        chat_id = context.user_data['chat_id']
        print(1)
        progress_bar = tqdm(
            total=total,
            unit='iB',
            token=bot_token,
            chat_id=chat_id,
            bar_format='{percentage:3.0f}% |{bar:8}|'
        )
        print(2)
        with open(path, 'wb') as f:
            print(3)
            for data in res.iter_content(block_size):
                print(4)
                progress_bar.update(len(data))
                print(5)
                f.write(data)
            message_id = progress_bar.tgio.message_id
        context.bot.delete_message(chat_id, message_id)
        progress_bar.close()
        if total != 0 and progress_bar.n != total:
            raise Exception("ERROR: something went wrong with progress bar.")
    else:
        with open(path, 'wb') as f:
            for data in res.iter_content(block_size):
                f.write(data)
    return path


# Parse Feed


def parse_doc(context, user, doc):
    doc_file = context.bot.getFile(doc['file_id'])
    doc_name = re.sub(r'.+(?=\.xml|\.opml?)',
                      str(user.user_id), doc['file_name'])
    path = doc_file.download(doc_name)
    with open(path, 'r') as f:
        feeds = parse_opml(f)
        return feeds


def parse_opml(f):
    feeds = []
    soup = BeautifulSoup(f, 'lxml', from_encoding="utf-8")
    for podcast in soup.find_all(type="rss"):
        feeds.append({"name": podcast.attrs.get('text'),
                      "url": podcast.attrs.get('xmlurl')})
    return feeds
