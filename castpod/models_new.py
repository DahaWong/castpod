from distutils.text_file import TextFile
import re
from datetime import date, datetime, timedelta
from html import unescape
from time import mktime
from pprint import pprint
from bs4 import BeautifulSoup
from telegraph.aio import Telegraph
from telegraph.utils import ALLOWED_TAGS
import urllib.parse

import feedparser
from peewee import (
    BooleanField,
    CharField,
    DateTimeField,
    ForeignKeyField,
    IntegerField,
    Model,
    SqliteDatabase,
    TextField,
    TimeField,
)
from PIL import Image
from playhouse.sqlite_ext import FTSModel, SearchField

from config import manifest

db = SqliteDatabase(
    database="castpod.db",
    pragmas={
        "journal_mode": "wal",
        "cache_size": -1 * 64000,  # 64MB
        "foreign_keys": 1,
        "ignore_check_constraints": 0,
        "synchronous": 0,
    },
)


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


class Podcast(BaseModel):
    # id = UUIDField(primary_key=True)
    feed = TextField(unique=True)
    name = CharField(null=True, max_length=64)
    logo = ForeignKeyField(Logo, null=True)
    host = TextField(null=True)
    website = TextField(null=True)
    email = TextField(null=True)

    def initialize(self):
        parsed = parse_feed(self.feed)
        self.name = parsed["name"]
        self.logo = parsed["logo"]
        self.host = parsed["host"]
        self.website = parsed["website"]
        self.email = parsed["email"]
        with db.atomic():
            for item in parsed["items"]:
                kwargs, shownotes = parse_episode(item, self)
                episode = Episode.create(**kwargs)
                shownotes.episode = episode
                shownotes.save()


class Episode(BaseModel):
    # guid = TextField(unique=True)
    from_podcast = ForeignKeyField(
        Podcast, null=True, backref="episodes", on_delete="CASCADE"
    )
    title = TextField()
    link = TextField()
    subtitle = TextField(null=True)
    summary = TextField(null=True)
    logo = ForeignKeyField(Logo, null=True)
    published_time = DateTimeField(default=datetime.now)
    updated_time = DateTimeField(default=datetime.now)
    message_id = IntegerField(null=True)
    file_id = TextField(null=True)
    is_downloaded = BooleanField(default=False)
    url = TextField(null=True)
    performer = TextField(null=True)
    size = IntegerField(null=True)
    duration = IntegerField(null=True)


class Shownotes(BaseModel):
    content = TextField()
    url = TextField(null=True)
    episode = ForeignKeyField(
        Episode, null=True, backref="shownotes", on_delete="CASCADE"
    )

    def extract_chapters(self):
        INLINE = r"<\/?(?:s|strong|b|em|i|del|u|cite|span|a).*?>"
        # print(self.content)
        content = re.sub(INLINE, "", self.content)
        TIME_DELTA = r"(?:[0-9]{1,2}[:：\'])?[0-9]{1,3}[:：\'][0-5][0-9]"
        soup = BeautifulSoup(content, "html.parser")
        results = soup.find_all(string=re.compile(TIME_DELTA))
        # print(results)
        if not results:
            return
        for result in results:
            # print(result.parent)
            result = str(result)
            # print(result)
            start_time = re.search(TIME_DELTA, result)[0]
            # print(start_time)
            title = re.sub(TIME_DELTA, "", result).strip()
            title = re.sub(r"^(?:\(\)|\{\}|\<\>|【】|（|\[]|\||·|)", "", title)
            Chapter.create(
                from_episode=self.episode, start_time=start_time, title=title
            )

    async def generate_telegraph(self):
        telegraph = Telegraph()
        await telegraph.create_account(
            short_name={manifest.bot_id},
        )
        content = format_html(self.content)
        # content = re.sub(
        #     r"https?:\/\/(www\.)?[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b([-a-zA-Z0-9()!@:%_\+.~#?&\/\/=\u4E00-\u9FFF\u3400-\u4DBF\u20000-\u2A6DF\u2A700-\u2B73F\u2B740-\u2B81F\u2B820-\u2CEAF\u2CEB0-\u2EBEF\u30000-\u3134F\uF900-\uFAFF\u2E80-\u2EFF\u31C0-\u31EF\u3000-\u303F\u2FF0-\u2FFF\u3300-\u33FF\uFE30-\uFE4F\uF900-\uFAFF\u2F800-\u2FA1F\u3200-\u32FF\u1F200-\u1F2FF\u2F00-\u2FDF]*?[<\\]?)",
        #     lambda m: f"<a href='{m[0]}'>{m[0]}</a>",
        #     content,
        # )
        # pprint(content)
        episode = self.episode
        podcast = episode.from_podcast
        logo_url = episode.logo.url or podcast.logo.url
        img_content = (
            f"<img src='{logo_url}'/>" if logo_url and ("img" not in content) else ""
        )
        content = img_content + content
        content = content.replace(
            "’", "'"
        )  # TODO: format like 1'03" should be recognized as chapter start time
        try:
            res = await telegraph.create_page(
                title=f"{episode.title}",
                author_name=podcast.name,
                author_url=episode.link or podcast.website,
                html_content=content,
            )
            self.url = res["url"]
            return self.url
        except:
            return None


class ShownotesIndex(FTSModel):
    # Full-text search index.
    content = SearchField()

    class Meta:
        database = db
        options = {"content": Shownotes.content}


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
    # Now, we can manage content in the ShownotesIndex. To populate the
    # search index:
    ShownotesIndex.rebuild()

    # Optimize the index.
    ShownotesIndex.optimize()


def parse_feed(feed):
    result = feedparser.parse(feed)
    feed = result.feed
    podcast = {}
    if not result.entries:
        return
        # self.delete_instance()
        # raise Exception(f"Feed has no entries.")
    podcast["feed"] = feed
    podcast["name"] = (
        unescape(feed.title)
        if len(feed.title) <= 63
        else unescape(feed.title)[:63] + "…"
    )
    podcast["logo"] = Logo.create(url=feed["image"]["href"])
    podcast["host"] = unescape(feed.author_detail.get("name") or "")
    podcast["website"] = feed.get("link")
    podcast["email"] = unescape(feed.author_detail.get("email") or "")
    # pprint(podcast["updated_time"])
    podcast["items"] = result["items"]
    return podcast


def parse_episode(item, podcast):
    episode = {}
    episode["from_podcast"] = podcast.id
    episode["published_time"] = datetime.fromtimestamp(mktime(item.published_parsed))
    audio = item.enclosures[0]
    episode["url"] = audio.get("href")
    episode["size"] = audio.get("length") if isinstance(audio.get("length"), int) else 0
    # performer = self.name
    episode["title"] = unescape(item.get("title") or "")

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
    shownotes = Shownotes.create(content=shownotes_content)
    excerpt = re.sub(r"\<.*?\>", "", episode["summary"]).strip()
    if len(excerpt) >= 47:
        excerpt = excerpt[:47] + "…"
    episode["subtitle"] = unescape(item.get("subtitle") or excerpt or "")
    episode["published_time"] = datetime.fromtimestamp(mktime(item.published_parsed))
    episode["updated_time"] = datetime.fromtimestamp(mktime(item.updated_parsed))
    return episode, shownotes


def set_duration(duration: str) -> int:
    duration_timedelta = None
    if duration:
        if ":" in duration:
            time = duration.split(":")
            if len(time) == 3:
                duration_timedelta = timedelta(
                    hours=int(time[0]), minutes=int(time[1]), seconds=int(time[2])
                ).total_seconds()
            elif len(time) == 2:
                duration_timedelta = timedelta(
                    hours=0, minutes=int(time[0]), seconds=int(time[1])
                ).total_seconds()
        else:
            duration_timedelta = re.sub(r"\.[0-9]+", "", duration)
    else:
        duration_timedelta = 0
    return int(duration_timedelta)


def format_html(text):
    """Format html texts to Telegraph allowed forms."""
    soup = BeautifulSoup(text, "html.parser")

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
    ALLOWED_VOID_TAGS = {"br", "img", "figure", "aside", "iframe", "ol", "ul", "hr"}
    for tag in soup.find_all():
        if tag.name not in ALLOWED_TAGS or (
            tag.name not in ALLOWED_VOID_TAGS and len(tag.get_text()) == 0
        ):
            tag.unwrap()
    return str(soup)
