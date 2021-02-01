from config import bot_token, mongo_uri, mongo_name
from pymongo import MongoClient
from telegram import InlineKeyboardMarkup
from tqdm.contrib.telegram import tqdm
from castpod.components import PodcastPage
import requests
from bs4 import BeautifulSoup
import errno
import os
import re
from functools import wraps

# Callback Query Helper


def toggle_save_podcast(update, context, to: str):
    podcast_name = re.match(r'(un)?save_podcast_(.+)',
                            update.callback_query.data)[2]
    podcast = context.bot_data['podcasts'].get(podcast_name)
    kwargs = {}

    if (to == 'saved'):
        kwargs = {
            'save_text': '⭐️',
            'save_action': "unsave_podcast"
        }
        context.user_data['saved_podcasts'].update({podcast_name: podcast})
    else:
        context.user_data['saved_podcasts'].pop(podcast_name)

    keyboard = PodcastPage(podcast, **kwargs).keyboard()
    context.dispatcher.run_async(
        update.callback_query.edit_message_reply_markup,
        InlineKeyboardMarkup(keyboard)
    )

# User Init


def check_login(func):
    @wraps(func)
    def wrapped(update, context, *args, **kwargs):
        user = context.user_data.get('user')
        if not user:
            update.message.reply_text("请先登录：/start")
            return
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
    res = requests.get(episode.audio_url, allow_redirects=True, stream=True)
    if res.status_code != 200:
        raise Exception(
            f"Error when downloading audio, status: {res.status_code}.")
    block_size = 1024  # 1 Kibibyte
    path = f'public/audio/{episode.podcast_name}/{episode.title}.mp3'
    if not os.path.exists(os.path.dirname(path)):
        try:
            os.makedirs(os.path.dirname(path))
        except OSError as exc:  # Guard against race condition
            if exc.errno != errno.EEXIST:
                raise
    if context.user_data:
        user = context.user_data['user']
        chat_id = user.user_id
        total = int(res.headers.get('content-length', 0))
        progress_bar = tqdm(
            total=total,
            unit='iB',
            token=bot_token,
            chat_id=chat_id,
            bar_format='{percentage:3.0f}% |{bar:8}|'
        )
        with open(path, 'wb') as f:
            for data in res.iter_content(block_size):
                progress_bar.update(len(data))
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
    # print(doc_file)
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


# MongoDB
client = MongoClient(mongo_uri)
db = client[mongo_name]
