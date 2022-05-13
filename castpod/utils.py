from tqdm.contrib.telegram import tqdm
import httpx
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
    res = httpx.get(f"{api_root}{endpoints['search_podcast']}{keyword}")
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


def download(episode, context):
    with httpx.stream("GET", episode.url) as res:
        if context.user_data:
            chat_id = context.user_data['chat_id']
            path = f"public/audio/{context.user_data['podcast']}/{episode.title}.mp3"
            validate_path(path)
            total = int(res.headers['Content-Length'])
            progress_bar = tqdm(
                total=total,
                unit='iB',
                token=bot_token,
                chat_id=chat_id,
                bar_format='{percentage:3.0f}% |{bar:6}|'
            )
            with open(path, 'wb') as f:
                for data in res.iter_raw(1024): # 1024 bytes
                    progress_bar.update(len(data))
                    f.write(data)
                message_id = progress_bar.tgio.message_id
            progress_bar.close()
            if total != 0 and progress_bar.n != total:
                raise Exception(
                    "Error: Something went wrong with progress bar.")
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
    return (path, message_id)


# Parse Feed


async def parse_doc(context, user, doc):
    doc_file = await context.bot.getFile(doc['file_id'])
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


def save_manage_starter(chat_data, message):
    if chat_data.get('manage_starter'):
        chat_data['manage_starter'].append(message)
    else:
        chat_data.update({'manage_starter': [message]})


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
