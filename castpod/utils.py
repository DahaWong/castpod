from tqdm.contrib.telegram import tqdm
import requests
from bs4 import BeautifulSoup
import errno
import os
import re
from functools import wraps
from config import bot_token
from datetime import date

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


# Download
def validate_path(path):
    if not os.path.exists(os.path.dirname(path)):
        try:
            os.makedirs(os.path.dirname(path))
        except OSError as exc:  # Guard against race condition
            if exc.errno != errno.EEXIST:
                raise


def download(episode, context) -> str:
    res = requests.get(episode.url, allow_redirects=True, stream=True)
    if res.status_code != 200:
        raise Exception(
            f"Error when downloading audio, status: {res.status_code}.")
    block_size = 1024  # 1 Kb
    if context.user_data:
        chat_id = context.user_data['chat_id']
        path = f"public/audio/{context.user_data['podcast']}/{episode.title}.mp3"
        validate_path(path)
        total = int(res.headers.get('content-length', 0))
        progress_bar = tqdm(
            total=total,
            unit='iB',
            token=bot_token,
            chat_id=chat_id,
            bar_format='{percentage:3.0f}% |{bar:6}|'
        )
        with open(path, 'wb') as f:
            for data in res.iter_content(block_size):
                progress_bar.update(len(data))
                f.write(data)
            message_id = progress_bar.tgio.message_id
        context.bot.delete_message(chat_id, message_id)
        progress_bar.close()
        if total != 0 and progress_bar.n != total:
            raise Exception("Error: Something went wrong with progress bar.")
    else:
        path = f"public/audio/new/{episode.title}.mp3"
        validate_path(path)
        if not os.path.exists(os.path.dirname(path)):
            try:
                os.makedirs(os.path.dirname(path))
            except OSError as exc:  # Guard against race condition
                if exc.errno != errno.EEXIST:
                    raise
        with open(path, 'wb') as f:
            for data in res.iter_content(block_size):
                f.write(data)
    return path


# Parse Feed


def parse_doc(context, user, doc):
    doc_file = context.bot.getFile(doc['file_id'])
    doc_name = re.sub(r'.+(?=\.xml|\.opml?)',
                      str(user.user_id), doc['file_name'])
    path = f'public/import/{doc_name}'
    doc_file.download(path)
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

# Manage page


def delete_update_message(func):
    @wraps(func)
    def wrapped(update, context, *args, **kwargs):
        func(update, context, *args, **kwargs)
        if update.message:
            context.dispatcher.run_async(update.effective_message.delete)
    return wrapped


def save_manage_starter(chat_data, message):
    if chat_data.get('manage_starter'):
        chat_data['manage_starter'].append(message)
    else:
        chat_data.update({'manage_starter': [message]})


def delete_manage_starter(context):
    run_async = context.dispatcher.run_async
    if not context.chat_data.get('manage_starter'):
        return
    for message in context.chat_data['manage_starter']:
        run_async(message.delete)
    context.chat_data['manage_starter'] = []


def generate_opml(user, podcasts):
    body = ''
    for podcast in podcasts:
        outline = f'\t\t\t\t<outline type="rss" text="{podcast.name}" xmlUrl="{podcast.feed}"/>\n'
        body += outline
    head = (
        "<?xml version='1.0' encoding='UTF-8' standalone='yes' ?>\n"
        "\t<opml version='1.0'>\n"
        "\t\t<head>\n"
        f"\t\t\t<title>Castpod 订阅 {date.today()}</title>\n"
        "\t\t</head>\n"
        "\t\t<body>\n"
        "\t\t\t<outline text='feeds'>\n"
    )
    tail = (
        "\t\t\t</outline>\n"
        "\t\t</body>\n"
        "\t</opml>\n"
    )
    opml = head + body + tail
    path = f"./public/subscriptions/Castpod_{date.today().strftime('%Y%m%d')}.xml"
    with open(path, 'w+') as f:
        f.write(opml)
    return path
