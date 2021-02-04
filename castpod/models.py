import re
import random
import socket
import feedparser
from mongoengine.document import Document, EmbeddedDocument
from mongoengine.fields import BooleanField, DateTimeField, EmbeddedDocumentField, EmbeddedDocumentListField, IntField, ListField, ReferenceField, StringField, URLField
from mongoengine.queryset.base import PULL
from mongoengine.queryset.manager import queryset_manager
from telegram.parsemode import ParseMode
# from castpod.utils import local_download
from config import podcast_vault, dev_user_id, manifest
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegraph import Telegraph
from html import unescape


class Subscription(EmbeddedDocument):
    podcast = ReferenceField(
        'Podcast', required=True)
    is_saved = BooleanField(default=False)
    is_latest = BooleanField(default=True)


class User(Document):
    # meta = {'queryset_class': UserQuerySet}
    user_id = IntField(primary_key=True)
    username = StringField(unique=True, required=True)
    name = StringField()
    subscriptions = EmbeddedDocumentListField(Subscription)

    @classmethod
    def validate_user(cls, from_user, subsets=None):
        if subsets:
            user = cls.objects(user_id=from_user.id).only(subsets).first()
        else:
            user = cls.objects(user_id=from_user.id).first()
        return user or cls(user_id=from_user.id, username=from_user.username).save()

    def subscribe(self, podcast):
        if self in podcast.subscribers:
            return
        podcast.renew()
        self.subscriptions.append(Subscription(podcast=podcast))
        podcast.subscribers.append(self)
        podcast.save()
        self.save()

    def unsubscribe(self, podcast):
        self.subscriptions.get(podcast=podcast).delete()
        podcast.subscribers.pop(self)
        podcast.save()
        self.save()

    def generate_opml(self):
        body = ''
        for subscription in self.subscriptions:
            podcast = subscription.podcast
            outline = f'\t\t\t\t<outline type="rss" text="{podcast.name}" xmlUrl="{podcast.feed}"/>\n'
            body += outline
        head = (
            "<?xml version='1.0' encoding='UTF-8' standalone='yes' ?>\n"
            "\t<opml version='1.0'>\n"
            "\t\t<head>\n"
            f"\t\t\t<title>{manifest.name} 订阅源</title>\n"
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
        path = f"./public/subscriptions/{self.user_id}.xml"
        with open(path, 'w+') as f:
            f.write(opml)
        return path


class Shownotes(EmbeddedDocument):
    content = StringField(required=True)
    url = URLField()
    timeline = StringField()

    def set_url(self):
        telegraph = Telegraph()
        telegraph.create_account(
            short_name=manifest.name,
            author_name=manifest.name,
            author_url=f'https://t.me/{manifest.bot_id}'
        )

        res = telegraph.create_page(
            title=f"{self.title}",
            html_content=self.shownotes,
            author_name=self.host or self.podcast_name
        )
        self.url = f"https://telegra.ph/{res['path']}"
        self.save()

    def set_shownotes(self):
        shownotes = unescape(
            self.content[0]['value']) if self.content else self.summary
        img_content = f"<img src='{self.logo or self.podcast_logo}'>" if 'img' not in shownotes else ''
        return img_content + self.replace_invalid_tags(shownotes)

    def set_timeline(self):
        shownotes = re.sub(r'</?(?:br|p|li).*?>', '\n', self.content)
        pattern = r'.+(?:[0-9]{1,2}:)?[0-9]{1,3}:[0-5][0-9].+'
        matches = re.finditer(pattern, shownotes)
        return '\n\n'.join([re.sub(r'</?(?:cite|del|span|div|s).*?>', '', match[0].lstrip()) for match in matches])


class Audio(EmbeddedDocument):
    url = URLField()
    performer = StringField()
    logo = URLField()
    size = IntField()
    duration = IntField()


class Episode(EmbeddedDocument):
    index = IntField(required=True)
    audio = EmbeddedDocumentField(Audio)
    title = StringField(max_length=64)
    subtitle = StringField()
    content = StringField()
    summary = StringField()
    host = StringField()
    shownotes = EmbeddedDocumentField(Shownotes)
    timeline = StringField()
    published_time = DateTimeField()
    message_id = IntField()
    file_id = StringField()


class Podcast(Document):
    # meta = {'queryset_class': PodcastQuerySet}
    feed = URLField(required=True, unique=True)
    name = StringField(max_length=64)
    logo = URLField()
    host = StringField()
    website = URLField()
    email = StringField()
    episodes = EmbeddedDocumentListField(Episode)
    subscribers = ListField(ReferenceField(User, reverse_delete_rule=PULL))
    update_time = DateTimeField()
    job_group = ListField(IntField(min_value=0, max_value=47))

    @classmethod
    def validate_feed(cls, feed, subsets=None):
        if subsets:
            podcast = cls.objects(feed=feed).only(subsets).first()
        else:
            podcast = cls.objects(feed=feed).first()
        return podcast or cls(feed=feed).save()

    @queryset_manager
    def of_subscriber(doc_cls, queryset, user, subsets=None):
        if subsets:
            return queryset(subscribers=user).only(subsets)
        else:
            return queryset(subscribers=user)

    def renew(self):
        self.set_job_group()
        socket.setdefaulttimeout(5)
        result = feedparser.parse(self.feed)
        if str(result.status)[0] != '2' and str(result.status)[0] != '3':
            raise Exception(f'Feed open error, status: {result.status}')
        feed = result.feed
        self.name = feed.get('title')
        if not self.name:
            self.delete()
            raise Exception("Cannot parse feed name.")
        self.name = unescape(self.name)[:63]
        if len(self.name) == 63:
            self.name += '…'
        self.logo = feed.get('image')['href']
        self.episodes = []
        for i, item in enumerate(result['items']):
            self.parse_episode(item)
            self.episodes.append(Episode(index=i))
        self.host = unescape(feed.author_detail.name or '')
        if self.host == self.name:
            self.host = ''
        self.website = feed.get('link')
        self.email = feed.author_detail.get('email') or ''
        self.save()
        return self

    def set_job_group(self):
        i = random.randint(0, 47)
        self.job_group = [i % 48 for i in range(i, i + 41, 8)]
        self.save()

    def parse_episode():

        pass
