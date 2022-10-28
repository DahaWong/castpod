import asyncio
import re
from datetime import datetime, timedelta
from time import mktime
from html import unescape
from pprint import pprint
from uuid import uuid4
from bs4 import BeautifulSoup
import httpx
from telegraph.aio import Telegraph
from telegraph.utils import ALLOWED_TAGS
from telegraph.exceptions import RetryAfterError, TelegraphException
from pypinyin import Style, pinyin
from zhconv import convert
from user_agent import generate_user_agent

import feedparser
from peewee import (
    BooleanField,
    CharField,
    DateTimeField,
    ForeignKeyField,
    IntegerField,
    Model,
    TextField,
    UUIDField,
)
from playhouse.sqlite_ext import SqliteExtDatabase, FTS5Model, SearchField, RowIDField
from castpod.constants import SHORT_DOMAIN

from config import manifest, EXT_PATH

db = SqliteExtDatabase(
    database="castpod.db",
    pragmas=(
        ("cache_size", -1024 * 64),  # 64MB page-cache.
        ("journal_mode", "wal"),  # Use WAL-mode (you should always use this!).
        ("foreign_keys", 1),
    ),  # Enforce foreign-key constraints.
)
# is_fts5_installed = FTS5Model.fts5_installed()
# print(is_fts5_installed)
db.load_extension("/home/daha/tool/libsimple")


class BaseModel(Model):
    """A base model that will use Sqlite database."""

    class Meta:
        database = db


class User(BaseModel):
    id = IntegerField(primary_key=True)
    name = TextField(null=True)


class Channel(BaseModel):
    """a telegram channel."""

    id = IntegerField(primary_key=True)
    name = TextField(null=True)


class Group(BaseModel):
    """a telegram group."""

    id = IntegerField(primary_key=True)
    name = TextField(null=True)


class Logo(BaseModel):
    url = TextField()
    file_id = TextField(null=True)
    thumb_url = TextField(null=True)
    thumb_file_id = TextField(null=True)


class Podcast(BaseModel):
    id = UUIDField(primary_key=True)
    feed = TextField(unique=True)
    name = CharField(null=True, max_length=64)
    language = CharField(null=True, max_length=11)  # max length eg. {3}-{3}-{3}
    logo = ForeignKeyField(Logo, null=True)
    host = TextField(null=True)
    website = TextField(null=True)
    email = TextField(null=True)
    pinyin_abbr = TextField(null=True)
    pinyin_full = TextField(null=True)
    etag = TextField(null=True)
    last_modified = DateTimeField(null=True)

    @classmethod
    def get_or_create(cls, **kwargs):
        is_created = False
        try:
            podcast = cls.get(**kwargs)
        except cls.DoesNotExist:
            podcast = cls.create(id=uuid4(), **kwargs)
            is_created = True
        return podcast, is_created

    async def initialize(self):
        parsed = await parse_feed("https://" + self.feed)
        is_success = True
        if not parsed:
            parsed = await parse_feed("http://" + self.feed)
        if not (parsed and parsed["name"]):
            is_success = False
            return self, is_success
        self.name = parsed["name"]
        match = re.search(
            r"[\u4E00-\u9FFF\u3400-\u4DBF\u20000-\u2A6DF\u2A700-\u2B73F\u2B740-\u2B81F\u2B820-\u2CEAF\u2CEB0-\u2EBEF\u30000-\u3134F\uF900-\uFAFF\u2E80-\u2EFF\u31C0-\u31EF\u3000-\u303F\u2FF0-\u2FFF\u3300-\u33FF\uFE30-\uFE4F\uF900-\uFAFF\u2F800-\u2FA1F\u3200-\u32FF\u1F200-\u1F2FF\u2F00-\u2FDF]+",
            parsed["name"],
        )
        if match:
            self.pinyin_abbr = "".join(
                x[0] for x in pinyin(match[0], style=Style.FIRST_LETTER, strict=False)
            )
            self.pinyin_full = "".join(
                x[0] for x in pinyin(match[0], style=Style.NORMAL, strict=False)
            )
        self.logo = parsed["logo"]
        self.host = parsed["host"]
        self.website = parsed["website"]
        self.email = parsed["email"]
        with db.atomic():
            for item in parsed["entries"]:
                kwargs, shownotes = parse_episode(item, self)
                episode = Episode.create(id=uuid4(), **kwargs)
                if shownotes:
                    shownotes.episode = episode
                    shownotes.save()
                    # print(episode.title)
                    store_shownotes(shownotes)
        return self, is_success


class Episode(BaseModel):
    id = UUIDField(primary_key=True)
    link = TextField(null=True, unique=True)  # some sites also call it 'guid'
    from_podcast = ForeignKeyField(Podcast, backref="episodes", on_delete="CASCADE")
    title = TextField(null=True)
    subtitle = TextField(null=True)
    summary = TextField(null=True)
    logo = ForeignKeyField(Logo, null=True)
    published_time = DateTimeField(null=True)
    updated_time = DateTimeField(null=True)
    message_id = IntegerField(null=True)
    file_id = TextField(null=True)
    url = TextField(null=True)  # audio file url
    performer = TextField(null=True)
    size = IntegerField(null=True)
    duration = IntegerField(null=True)
    is_downloaded = BooleanField(default=False)  # remove this


class Shownotes(BaseModel):
    content = TextField()
    url = TextField(null=True)
    episode = ForeignKeyField(
        Episode, null=True, backref="shownotes", on_delete="CASCADE"
    )

    def extract_chapters(self):
        INLINE = r"<\/?(?:s|strong|b|em|i|del|u|cite|span|a).*?>"
        content = re.sub(INLINE, "", self.content)
        # content = re.sub(r"<br *\/>", "\n", self.content)
        TIME_DELTA = r"(?:[0-9]{1,2}[:：])?[0-9]{1,3}[:：][0-5][0-9]"
        soup = BeautifulSoup(markup=content, features="html.parser")
        results = soup.find_all(string=re.compile(TIME_DELTA))
        if not results:
            return False
        if len(results) > 1:
            for result in results:
                result = str(result)
                start_time = re.search(TIME_DELTA, result)[0]
                start_time = start_time.replace("：", ":")
                title = re.sub(TIME_DELTA, "", result).strip()
                title = re.sub(r"^(?:\(\)|\{\}|\<\>|【】|（|\[]|\||·|)", "", title)
                Chapter.create(
                    from_episode=self.episode, start_time=start_time, title=title
                )
        else:
            CHAPTER_ITEM = r"((?:[0-9]{1,2}[:：'])?[0-9]{1,3}[:：'][0-5][0-9])(.+?)(?=(?:(?:[0-9]{1,2}[:：'])?[0-9]{1,3}[:：'][0-5][0-9])|\n)"
            matches = re.finditer(CHAPTER_ITEM, results[0])
            for match in matches:
                start_time = match[1].replace("：", ":").replace("'", "")
                title = match[2].lstrip("]】>|｜ ").rstrip("[【<|｜ ")
                Chapter.create(
                    from_episode=self.episode, start_time=start_time, title=title
                )
        return True

    async def generate_telegraph(self):
        telegraph = Telegraph()
        await telegraph.create_account(
            short_name=manifest.name,
            author_name=manifest.name,
            author_url=manifest.author_url,
        )
        content = format_html(self.content)
        self.content = content
        episode = self.episode
        podcast = episode.from_podcast
        logo_url = episode.logo.url or podcast.logo.url
        episode_link = episode.link
        if not re.search(SHORT_DOMAIN, episode_link):
            episode_link = podcast.website
        date_content = f"<p><blockquote><a href='{episode_link}'>{podcast.name}</a> 发布于 {episode.updated_time.date()}</blockquote></p>"
        img_content = (
            f"\n<h3>Cover Image</h3><figure><img src='{logo_url}'/><figcaption>{podcast.name}·《{episode.title}》</figcaption></figure>"
            if logo_url and ("img" not in content)
            else ""
        )
        content = "".join([date_content, content, img_content])
        content = content.replace("\n", "<br />")
        metadata = {
            "title": f"{podcast.name} · {episode.title}",
            "author_name": f"{manifest.name} Bot",
            "author_url": f"https://t.me/{manifest.bot_id}?start=episode_{episode.id}",
            "html_content": content,
        }
        res, trial_times = None, 3
        while not res and trial_times > 0:
            try:
                res = await telegraph.create_page(**metadata)
                self.url = res.get("url")
            except RetryAfterError as e:
                await asyncio.sleep(e.retry_after)
            except TelegraphException:
                await asyncio.sleep(30)
            finally:
                trial_times -= 1
                continue
        return self


class ShownotesIndex(FTS5Model):
    # Full-text search index.
    rowid = RowIDField()
    title_hans = SearchField()
    title_hant = SearchField()
    content_hans = SearchField()
    content_hant = SearchField()

    class Meta:
        database = db
        options = {"tokenize": "simple"}


class Chapter(BaseModel):
    """Represent a single chapter item which contains title, start time, and end time."""

    from_episode = ForeignKeyField(Episode, backref="chapters", on_delete="CASCADE")
    start_time = TextField()
    title = TextField()


# Middle models
class UserSubscribePodcast(BaseModel):
    """Model for user's subscription."""

    user = ForeignKeyField(User, on_delete="CASCADE")
    podcast = ForeignKeyField(Podcast, on_delete="CASCADE")


class FavPodcast(BaseModel):
    user = ForeignKeyField(User, on_delete="CASCADE")
    podcast = ForeignKeyField(Podcast, on_delete="CASCADE")


class SaveEpisode(BaseModel):
    user = ForeignKeyField(User, on_delete="CASCADE")
    episode = ForeignKeyField(Episode, on_delete="CASCADE")


class ChannelPodcast(BaseModel):
    """Model for channel's subscription."""

    channel = ForeignKeyField(Channel, on_delete="CASCADE")
    podcast = ForeignKeyField(Podcast, on_delete="CASCADE")


class GroupPodcast(BaseModel):
    """Model for group's subscribtion."""

    group = ForeignKeyField(Group, on_delete="CASCADE")
    podcast = ForeignKeyField(Podcast, on_delete="CASCADE")


def db_init():
    db.connect()
    # db.load_extension(EXT_PATH + "libsimple")
    db.create_tables(
        [
            User,
            Channel,
            Group,
            Logo,
            Podcast,
            Shownotes,
            ShownotesIndex,
            Chapter,
            Episode,
            UserSubscribePodcast,
            FavPodcast,
            SaveEpisode,
            ChannelPodcast,
            GroupPodcast,
        ]
    )
    # p = Podcast.get(Podcast.name == None)
    # print(p.name)
    # p.delete_instance()
    # ShownotesIndex.drop_table()
    # Construct index
    # shownotes = Shownotes.select()
    # for s in shownotes:
    #     print(s.episode.title)
    #     store_shownotes(s)
    # print("done!!!!!!!!")
    ShownotesIndex.rebuild()
    ShownotesIndex.optimize()


async def parse_feed(feed, etag="", if_modified_since=""):
    user_agent = generate_user_agent(os="linux", device_type="desktop")
    headers = {
        "User-Agent": user_agent,
        "ETag": etag,
        "If-Modified-Since": if_modified_since,
    }
    async with httpx.AsyncClient() as client:
        res = await client.get(feed, follow_redirects=True, timeout=12, headers=headers)
    if res.status_code != httpx.codes.OK:
        return
    result = feedparser.parse(res.content)
    feed = result.feed
    podcast = {}
    if not result.entries:
        return
        # self.delete_instance()
        # raise Exception(f"Feed has no entries.")
    podcast["feed"] = feed
    name = feed.get("title")
    podcast["name"] = unescape(name) if len(name) <= 63 else unescape(name)[:63] + "…"
    podcast["description"] = feed.get("subtitle") or feed.get("")
    podcast["language"] = feed.get("language")
    author = feed.get("author_detail")
    if author:
        podcast["host"] = unescape(author.get("name") or "")
        podcast["email"] = unescape(author.get("email") or "")
    podcast["logo"] = Logo.create(url=feed["image"]["href"])
    podcast["website"] = feed.get("link")
    podcast["entries"] = result.entries
    podcast["etag"] = result.get("etag")
    last_modified: str = result.get("last-modified")
    if last_modified:
        podcast["last_modified"] = datetime.strptime(
            last_modified, "%a, %d %b %Y %H:%M:%S GMT"
        )
    return podcast


def parse_episode(item, podcast):
    episode = {}
    episode["from_podcast"] = podcast.id
    # print(item.title)
    enclosures = item.enclosures
    if enclosures:
        audio = enclosures[0]
        episode["url"] = audio.get("href")
        size = audio.get("length")
        if not size:
            episode["size"] = 0
        else:
            episode["size"] = size
    episode["title"] = unescape(item.get("title") or "")
    # print(episode["title"])
    if item.get("image"):
        episode["logo"] = Logo.get_or_create(url=item.image.href)[0]
    else:
        episode["logo"] = podcast.logo

    episode["duration"] = set_duration(item.get("itunes_duration"))
    episode["link"] = item.get("link")
    episode["summary"] = unescape(item.get("summary") or "")
    # TODO: error
    shownotes_content = (
        item.get("content")[0]["value"] if item.get("content") else episode["summary"]
    )
    shownotes = None
    if shownotes_content:
        shownotes = Shownotes.create(content=shownotes_content)
    excerpt = re.sub(r"\<.*?\>", "", episode["summary"]).strip()
    if len(excerpt) >= 47:
        excerpt = excerpt[:47] + "…"
    episode["subtitle"] = unescape(item.get("subtitle") or excerpt or "")
    episode["published_time"] = datetime.fromtimestamp(mktime(item.created_parsed))
    episode["updated_time"] = datetime.fromtimestamp(mktime(item.updated_parsed))
    return episode, shownotes


def set_duration(duration: str) -> int:
    if not duration:
        return 0
    duration = duration.replace("：", ":")
    duration_timedelta = None
    if ":" in duration:
        time = duration.split(":")
        if len(time) == 3:
            duration_timedelta = timedelta(
                hours=int(time[0] or 0),
                minutes=int(time[1] or 0),
                seconds=int(time[2] or 0),
            ).total_seconds()
        elif len(time) == 2:
            duration_timedelta = timedelta(
                hours=0, minutes=int(time[0]), seconds=int(time[1])
            ).total_seconds()
        return duration_timedelta
    elif not re.match(r"^[0-9]+$", duration):
        return 0
    else:
        return int(duration)


def format_html(text):
    """Format html texts to Telegraph allowed forms."""
    soup = BeautifulSoup(markup=text, features="html.parser")

    # Find all possible heading types, and convert them to proper h3,h4,strong tags.
    headings = soup.find_all(["h1", "h2", "h3", "h4", "h5", "h6"])
    heading_types = sorted(set([x.name for x in headings]))
    if headings:
        for heading in headings:
            if heading.name == heading_types[0]:
                heading.name = "h3"
            elif len(headings) >= 2 and heading.name == heading_types[1]:
                heading.name = "h4"
            else:
                heading.name = "strong"

    # a) Unwrap all unallowed tags and b) Remove all empty tags.
    ALLOWED_VOID_TAGS = {
        "br",
        "img",
        "figure",
        "aside",
        "iframe",
        "ol",
        "ul",
        "hr",
        "li",
    }
    for tag in soup.find_all():
        if tag.name not in ALLOWED_TAGS or (
            tag.name not in ALLOWED_VOID_TAGS and len(tag.get_text()) == 0
        ):
            tag.unwrap()
    return str(soup)


def filter_subscription(user_id, keywords):
    keywords_hans = convert(keywords, "zh-hans")
    keywords_hant = convert(keywords, "zh-hant")
    podcasts = (
        Podcast.select()
        .where(
            Podcast.name.contains(keywords_hans)
            | Podcast.name.contains(keywords_hant)
            | Podcast.pinyin_abbr.startswith(keywords)
            | Podcast.pinyin_full.startswith(keywords)
            | Podcast.host.contains(keywords_hans)
            | Podcast.host.contains(keywords_hant)
        )  # TODO: shownotes full text search, and extract the matched line to description.
        .join(UserSubscribePodcast)
        .join(User)
        .where(User.id == user_id)
    )
    return podcasts


def show_subscription(user_id):
    # TODO: 检查这里的查询是不是限制在了本用户之内？
    podcasts = (
        Podcast.select().join(UserSubscribePodcast).join(User).where(User.id == user_id)
    )
    return podcasts


def store_shownotes(shownotes: Shownotes):
    title = shownotes.episode.title
    content = shownotes.content
    title_hans = convert(title, "zh-hans")
    content_hans = convert(content, "zh-hans")
    title_hant = convert(title, "zh-hant")
    content_hant = convert(content, "zh-hant")
    ShownotesIndex.insert(
        {
            ShownotesIndex.rowid: shownotes.id,
            ShownotesIndex.title_hans: title_hans,
            ShownotesIndex.title_hant: title_hant,
            ShownotesIndex.content_hans: content_hans,
            ShownotesIndex.content_hant: content_hant,
        }
    ).execute()
