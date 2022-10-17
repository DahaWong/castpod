from peewee import *
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
    """A base model that will use our Sqlite database."""

    class Meta:
        database = db


class User(BaseModel):
    id = IntegerField(primary_key=True)
    name = TextField()


class Channel(BaseModel):
    """a telegram channel."""

    id = IntegerField(primary_key=True)
    name = TextField()


class Group(BaseModel):
    """a telegram group."""

    id = IntegerField(primary_key=True)
    name = TextField()


class Logo(BaseModel):
    path = TextField()
    downloaded = BooleanField(default=False)
    url = TextField()
    file_id = TextField()


class Podcast(BaseModel):
    feed = TextField(unique=True)
    name = TextField()
    # logo
    host = TextField()
    website = TextField()
    email = TextField()
    channel = TextField()
    group = IntegerField()
    updated_time = DateTimeField(default=datetime.now)
    owner = ForeignKeyField(User, 'owning_podcasts')

class Episode(BaseModel):
    id = TextField(unique=True)
    from_podcast = ForeignKeyField(Podcast, backref="episodes")
    title = TextField()
    link = TextField()
    subtitle = TextField()
    summary = TextField()
    published_time = DateTimeField(default=datetime.now)
    updated_time = DateTimeField(default=datetime.now)
    message_id = IntegerField()
    file_id = TextField()
    shownotes= TextField()
    shownotes_url = TextField()
    # timeline
    downloaded = BooleanField(default=False)
    url = TextField()
    performer = TextField()
    # logo
    size = IntegerField()
    duration = IntegerField()


# Intermediate models


class UserPodcast(BaseModel):
    user = ForeignKeyField(User)
    podcast = ForeignKeyField(Podcast)


class FavPodcast(BaseModel):
    user = ForeignKeyField(User)
    podcast = ForeignKeyField(Podcast)


class SaveEpisode(BaseModel):
    user = ForeignKeyField(User)
    episode = ForeignKeyField(Episode)


class ChannelPodcast(BaseModel):
    channel = ForeignKeyField(Channel)
    podcast = ForeignKeyField(Podcast)


class GroupPodcast(BaseModel):
    group = ForeignKeyField(Group)
    podcast = ForeignKeyField(Podcast)


def db_init():
    db.connect()
    db.create_tables([User])
