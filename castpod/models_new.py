from distutils.text_file import TextFile
import re
from datetime import date, datetime, timedelta
from html import unescape
from time import mktime
from pprint import pprint
from bs4 import BeautifulSoup

import feedparser
import httpx
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

db = SqliteDatabase(
    database="dimbo.db",
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
    local_path = TextField(null=True)

    async def download(self):
        async with httpx.AsyncClient() as client:
            res = await client.get(self.url, follow_redirects=True)
        if res.status_code != httpx.codes.OK:
            return
        path = f"public/logo/{self.id}"
        extension = "." + res.headers["content-type"].replace("image/", "")
        path += extension
        with open(path, "wb") as f:
            f.write(res.content)
        self.local_path = path


class Podcast(BaseModel):
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
                kwargs = parse_episode(item, self)
                Episode.create(**kwargs)


class Shownotes(BaseModel):
    content = TextField()
    url = TextField(null=True)

    def extract_chapters(self):
        INLINE = r"<\/?(?:s|strong|b|em|i|del|u|cite|span|a).*?>"
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


class ShownotesIndex(FTSModel):
    # Full-text search index.
    content = SearchField()

    class Meta:
        database = db
        options = {"content": Shownotes.content}


class Episode(BaseModel):
    # guid = TextField(unique=True)
    from_podcast = ForeignKeyField(Podcast, null=True, backref="episodes")
    title = TextField()
    link = TextField()
    subtitle = TextField(null=True)
    summary = TextField(null=True)
    logo = ForeignKeyField(Logo, null=True)
    shownotes = ForeignKeyField(Shownotes, null=True, backref="episode")
    published_time = DateTimeField(default=datetime.now)
    updated_time = DateTimeField(default=datetime.now)
    message_id = IntegerField(null=True)
    file_id = TextField(null=True)
    is_downloaded = BooleanField(default=False)
    url = TextField(null=True)
    performer = TextField(null=True)
    size = IntegerField(null=True)
    duration = IntegerField(null=True)
    timeline = TextField(null=True)


class Chapter(BaseModel):
    """Represent a single chapter item which contains title, start time, and end time."""

    from_episode = ForeignKeyField(Episode, backref="chapters")
    start_time = IntegerField()
    title = TextField()


# Middle models
class UserSubscribePodcast(BaseModel):
    """Model for user's subscription."""

    user = ForeignKeyField(User)
    podcast = ForeignKeyField(Podcast)


class FavPodcast(BaseModel):
    user = ForeignKeyField(User)
    podcast = ForeignKeyField(Podcast)


class SaveEpisode(BaseModel):
    user = ForeignKeyField(User)
    episode = ForeignKeyField(Episode)


class ChannelPodcast(BaseModel):
    """Model for channel's subscription."""

    channel = ForeignKeyField(Channel)
    podcast = ForeignKeyField(Podcast)


class GroupPodcast(BaseModel):
    """Model for group's subscribtion."""

    group = ForeignKeyField(Group)
    podcast = ForeignKeyField(Podcast)


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
    content = (
        item.get("content")[0]["value"] if item.get("content") else episode["summary"]
    )
    episode["shownotes"] = Shownotes.create(content=content)
    excerpt = re.sub(r"\<.*?\>", "", episode["summary"]).strip()
    if len(excerpt) >= 47:
        excerpt = excerpt[:47] + "…"
    episode["subtitle"] = unescape(item.get("subtitle") or excerpt or "")
    episode["published_time"] = datetime.fromtimestamp(mktime(item.published_parsed))
    episode["updated_time"] = datetime.fromtimestamp(mktime(item.updated_parsed))
    return episode


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
