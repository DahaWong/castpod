import errno
import os
from pprint import pprint
import re
from datetime import date, datetime
from functools import wraps

import httpx
from bs4 import BeautifulSoup
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Message, Update
from telegram.ext import CallbackContext


# iTunes Search API
async def search_itunes(keyword: str = None, itunes_id: str = None):
    url = (
        f"https://itunes.apple.com/search?media=podcast&limit=25&term={keyword}"
        if keyword and not itunes_id
        else f"https://itunes.apple.com/lookup?id={itunes_id}"
    )
    async with httpx.AsyncClient() as client:
        res = await client.get(url, follow_redirects=True)
    if res.status_code != httpx.codes.OK:
        return None
    results = res.json()["results"]
    return results


def validate_path(path):
    if not os.path.exists(os.path.dirname(path)):
        try:
            os.makedirs(os.path.dirname(path))
        except OSError as exc:  # Guard against race condition
            if exc.errno != errno.EEXIST:
                raise


async def streaming_download(
    from_podcast: str, title: str, url: str, progress_msg: Message
):
    file_path = f"public/audio/{from_podcast}/{title}.mp3"
    validate_path(file_path)
    with httpx.stream("GET", url, follow_redirects=True) as res:
        total = int(res.headers["Content-Length"])
        with open(file_path, "wb") as f:
            s = 0
            for chunk in res.iter_raw(4194304):
                s += len(chunk)
                percentage = round(s / total * 100)
                await progress_msg.edit_text(
                    f"<pre>{percentage}%</pre> | {percentage // 10 * '■' }{(10 - percentage // 10) * '□'}"
                )
                f.write(chunk)
    return file_path


# Parse Feed
# async def parse_doc(context, user, doc):
#     doc_file = await context.bot.getFile(doc['file_id'])
#     doc_name = re.sub(r'.+(?=\.xml|\.opml?)',
#                       str(user.user_id), doc['file_name'])
#     path = f'public/import/{doc_name}'
#     doc_file.download(path)
#     with open(path, 'r') as f:
#         feeds = parse_opml(f)
#         return feeds


# def parse_opml(f):
#     feeds = []
#     soup = BeautifulSoup(f, 'lxml', from_encoding="utf-8")
#     for podcast in soup.find_all(type="rss"):
#         feeds.append({"name": podcast.attrs.get('text'),
#                       "url": podcast.attrs.get('xmlurl')})
#     return feeds

# # Manage page


# def save_manage_starter(chat_data, message):
#     if chat_data.get('manage_starter'):
#         chat_data['manage_starter'].append(message)
#     else:
#         chat_data.update({'manage_starter': [message]})


# def generate_opml(user, podcasts):
#     body = ''
#     for podcast in podcasts:
#         outline = f'\t\t\t\t<outline type="rss" text="{podcast.name}" xmlUrl="{podcast.feed}"/>\n'
#         body += outline
#     head = (
#         "<?xml version='1.0' encoding='UTF-8' standalone='yes' ?>\n"
#         "\t<opml version='1.0'>\n"
#         "\t\t<head>\n"
#         f"\t\t\t<title>Castpod 订阅 {date.today()}</title>\n"
#         "\t\t</head>\n"
#         "\t\t<body>\n"
#         "\t\t\t<outline text='feeds'>\n"
#     )
#     tail = (
#         "\t\t\t</outline>\n"
#         "\t\t</body>\n"
#         "\t</opml>\n"
#     )
#     opml = head + body + tail
#     path = f"./public/subscriptions/Castpod_{date.today().strftime('%Y%m%d')}.xml"
#     with open(path, 'w+') as f:
#         f.write(opml)
#     return path


async def send_error_message(update: Update, text: str) -> None:
    await update.message.reply_text(
        text,
        reply_markup=InlineKeyboardMarkup.from_button(
            InlineKeyboardButton("联系我们", url="https://dahawong.t.me")
        ),
    )
