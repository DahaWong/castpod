from peewee import *

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
    username = TextField()


def db_init():
    db.connect()
    db.create_tables([User])
