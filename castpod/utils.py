from datetime import date
import errno
import os
import re
from PIL import Image
from bs4 import BeautifulSoup
import httpx
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Message, User
from telegram.error import BadRequest
from user_agent import generate_user_agent

# TODO: split utils.py into utils/...

# iTunes Search API
async def search_itunes(keyword: str = None, itunes_id: str = None):
    url = (
        f"https://itunes.apple.com/search?media=podcast&limit=50&term={keyword}"
        if keyword and not itunes_id
        else f"https://itunes.apple.com/lookup?id={itunes_id}"
    )
    async with httpx.AsyncClient() as client:
        ua = generate_user_agent(os="linux", device_type="desktop")
        res = await client.get(url, follow_redirects=True, headers={"User-Agent": ua})
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
    return path


async def streaming_download(path: str, url: str, progress_msg: Message):
    validate_path(path)
    with httpx.stream("GET", url, follow_redirects=True) as res:
        total = int(res.headers["Content-Length"])
        with open(path, "wb") as f:
            s = 0
            for chunk in res.iter_raw(4194304):
                s += len(chunk)
                percentage = round(s / total * 100)
                percentage_hint = str(percentage) + "%"
                try:
                    await progress_msg.edit_text(
                        f"<pre>{percentage_hint:<4}</pre> | {percentage // 10 * '■' }{(10 - percentage // 10) * '□'}"
                    )
                except BadRequest:
                    pass
                f.write(chunk)
    return path


async def parse_doc(context, user, doc):
    doc_file = await context.bot.getFile(doc["file_id"])
    doc_name = re.sub(r".+(?=\.xml|\.opml?)", str(user.id), doc["file_name"])
    path = f"public/import/{doc_name}"
    await doc_file.download(path)
    with open(path, "r") as f:
        feeds = parse_opml(f)
    return feeds


def parse_opml(file_handler):
    feeds = []
    soup = BeautifulSoup(markup=file_handler, features="lxml", from_encoding="utf-8")
    for podcast in soup.find_all(type="rss"):
        attrs = podcast.attrs
        feeds.append(
            {
                "name": attrs.get("title") or attrs.get("text"),
                "url": attrs.get("xmlurl"),
            }
        )
    # print(feeds)
    return feeds


def generate_opml(podcasts):
    body = ""
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
    tail = "\t\t\t</outline>\n" "\t\t</body>\n" "\t</opml>\n"
    opml = "".join(head, body, tail)
    path = f"public/subscriptions/castpod-{date.today()}.xml"
    with open(path, "w+") as f:
        f.write(opml)
    return path


async def send_error_message(user: User, text: str) -> None:
    # TODO：播客同名的情况，须返回多个结果。（虽然很少见）
    if not user:
        return
    await user.send_message(
        text,
        reply_markup=InlineKeyboardMarkup.from_row(
            [
                InlineKeyboardButton("联系我们", url="https://dahawong.t.me"),
                InlineKeyboardButton("查阅说明书", url="https://telegra.ph"),  # TODO: 重写说明书
            ]
        ),
    )


# TODO：unused function
def modify_logo(path: str, size: int):
    with Image.open(path) as im:
        # 1. to jpeg format
        im = im.convert("RGB")
        # 2. < 320*320
        size = (size, size)
        im.thumbnail(size)
        # 3. less than 200 kB !!
        im.save(path, "JPEG", optimize=True, quality=85)
