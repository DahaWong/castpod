from peewee import (
    SqliteDatabase,
    TextField,
    Model,
    IntegerField,
    BooleanField,
    ForeignKeyField,
    DateTimeField,
)
from playhouse.sqlite_ext import FTSModel, SearchField
from datetime import datetime
from PIL import Image


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
    is_downloaded = BooleanField(default=False)
    path = TextField(null=True)
    file_id = TextField(null=True)
    url = TextField()


class Podcast(BaseModel):
    feed = TextField(unique=True)
    name = TextField()
    logo = ForeignKeyField(Logo)
    host = TextField()
    website = TextField(null=True)
    email = TextField(null=True)
    updated_time = DateTimeField(default=datetime.now)


class Shownotes(BaseModel):
    content = TextField()
    url = TextField()


class ShownotesIndex(FTSModel):
    # Full-text search index.
    content = SearchField()

    class Meta:
        database = db
        options = {"content": Shownotes.content}


class Episode(BaseModel):
    id = TextField(unique=True)
    from_podcast = ForeignKeyField(Podcast, backref="episodes")
    title = TextField()
    link = TextField()
    subtitle = TextField(null=True)
    summary = TextField(null=True)
    logo = ForeignKeyField(Logo)
    shownotes = ForeignKeyField(Shownotes, backref="episode")
    published_time = DateTimeField(default=datetime.now)
    updated_time = DateTimeField(default=datetime.now)
    message_id = IntegerField(null=True)
    file_id = TextField(null=True)
    # timeline
    is_downloaded = BooleanField(default=False)
    url = TextField()
    performer = TextField()
    size = IntegerField(null=True)
    duration = IntegerField(null=True)


# Middle models
class UserPodcast(BaseModel):
    """Model for user's subscribtion."""

    user = ForeignKeyField(User)
    podcast = ForeignKeyField(Podcast)


class FavPodcast(BaseModel):
    user = ForeignKeyField(User)
    podcast = ForeignKeyField(Podcast)


class SaveEpisode(BaseModel):
    user = ForeignKeyField(User)
    episode = ForeignKeyField(Episode)


class ChannelPodcast(BaseModel):
    """Model for channel's subscribtion."""

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
            Episode,
            UserPodcast,
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
