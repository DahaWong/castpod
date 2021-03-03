import re
import random
import socket
import datetime
from time import mktime, sleep
import feedparser
from mongoengine.document import Document, EmbeddedDocument
from mongoengine.fields import BooleanField, DateTimeField, EmbeddedDocumentField, EmbeddedDocumentListField, IntField, LazyReferenceField, ListField, ReferenceField, StringField, URLField
from mongoengine.queryset.base import PULL
from mongoengine.queryset.manager import queryset_manager
from mongoengine.errors import DoesNotExist

from telegram.parsemode import ParseMode
# from castpod.utils import local_download
from config import podcast_vault, dev_user_id, manifest
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegraph import Telegraph
from html import unescape

telegraph = Telegraph()

telegraph.create_account(
    short_name=manifest.name,
    author_name=manifest.name,
    author_url=f'https://t.me/{manifest.bot_id}'
)


class Subscription(EmbeddedDocument):
    podcast = ReferenceField(
        'Podcast', required=True)
    is_fav = BooleanField(default=False)
    is_latest = BooleanField(default=True)


class User(Document):
    # meta = {'queryset_class': UserQuerySet}
    user_id = IntField(primary_key=True)
    username = StringField()
    name = StringField()
    subscriptions = EmbeddedDocumentListField(Subscription)

    @classmethod
    def validate_user(cls, from_user, subsets=None):
        if subsets:
            user = cls.objects(user_id=from_user.id).only(subsets).first()
        else:
            user = cls.objects(user_id=from_user.id).first()
        return user or cls(user_id=from_user.id, username=from_user.username, name=from_user.first_name).save()

    def subscribe(self, podcast):
        if self in podcast.subscribers:
            return
        if not podcast.name:
            podcast.renew()
        self.update(push__subscriptions=Subscription(podcast=podcast))
        # self.reload()
        podcast.update(push__subscribers=self)
        # podcast.reload()

    def unsubscribe(self, podcast):
        self.update(pull__subscriptions=self.subscriptions.get(podcast=podcast))
        podcast.update(pull__subscribers=self)
    def toggle_fav(self, podcast):
        # use XOR to toggle boolean
        self.subscriptions.get(podcast=podcast).is_fav ^= True
        self.save()

    def generate_opml(self):
        body = ''
        for subscription in self.subscriptions:
            try:
                podcast = subscription.podcast
            except DoesNotExist:
                self.subscriptions.remove(subscription)
                self.update(set__subscriptions=self.subscriptions)
                # self.reload()
                continue
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

    def set_url(self, title, author):
        res = telegraph.create_page(
            title=f"{title}",
            html_content=self.content,
            author_name=author
        )
        self.url = f"https://telegra.ph/{res['path']}"
        return self.url

    def set_content(self, logo):
        content = self.content
        img_content = f"<img src='{logo}'>" if logo and ('img' not in content) else ''
        self.content = img_content + self.replace_invalid_tags(content)
        return self.content

    def set_timeline(self):
        shownotes = re.sub(r'</?(?:br|p|li).*?>', '\n', self.content)
        pattern = r'.+(?:[0-9]{1,2}:)?[0-9]{1,3}:[0-5][0-9].+'
        matches = re.finditer(pattern, shownotes)
        self.timeline = '\n\n'.join([re.sub(
            r'</?(?:cite|del|span|div|s).*?>', '', match[0].lstrip()) for match in matches])
        return self.timeline

    def replace_invalid_tags(self, html_content):
        html_content = html_content.replace('h1', 'h3').replace('h2', 'h4')
        html_content = html_content.replace('cite>', "i>")
        html_content = re.sub(r'</?(?:div|span|audio).*?>', '', html_content)
        html_content = html_content.replace('’', "'")
        return html_content


class Audio(EmbeddedDocument):
    url = URLField()
    performer = StringField()
    logo = URLField()
    size = IntField()
    duration = IntField()


class Episode(EmbeddedDocument):
    index = IntField(required=True)
    audio = EmbeddedDocumentField(Audio)
    title = StringField()
    subtitle = StringField()
    content = StringField()
    summary = StringField()
    host = StringField()
    shownotes = EmbeddedDocumentField(Shownotes)
    timeline = StringField()
    published_time = DateTimeField()
    message_id = IntField()  # message_id in podcast_vault
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
    # update_time = DateTimeField()
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
        self.logo = feed['image']['href']
        self.episodes = []
        for i, item in enumerate(result['items']):
            episode = self.parse_episode(item, i)
            if episode:
                self.update(push__episodes=episode)
            # self.reload()
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

    def parse_episode(self, item, i):
        if not item.enclosures:
            return
        audio = item.enclosures[0]
        episode = Episode(index=i)
        episode.audio = Audio(
                url=audio.get('href'),
                size=audio.get('length') or 0,
                performer=self.name,
                logo=item.get('image').href if item.get('image') else self.logo,
                duration=self.set_duration(item.get('itunes_duration'))
            )
        episode.title = unescape(item.get('title') or '')
        episode.subtitle = unescape(item.get('subtitle') or '')
        if episode.title == episode.subtitle:
            episode.subtitle = ''
        episode.summary = unescape(item.get('summary') or '')
        content = item.get('content')[0]['value'] if item.get(
            'content') else episode.summary
        episode.shownotes = Shownotes(content=content)
        episode.shownotes.set_content(episode.audio.logo)
        episode.published_time = datetime.datetime.fromtimestamp(
            mktime(item.published_parsed))
        return episode

    def set_duration(self, duration: str) -> int:
        duration_timedelta = None
        if duration:
            if ':' in duration:
                time = duration.split(':')
                if len(time) == 3:
                    duration_timedelta = datetime.timedelta(
                        hours=int(time[0]),
                        minutes=int(time[1]),
                        seconds=int(time[2])
                    ).total_seconds()
                elif len(time) == 2:
                    duration_timedelta = datetime.timedelta(
                        hours=0,
                        minutes=int(time[0]),
                        seconds=int(time[1])
                    ).total_seconds()
            else:
                duration_timedelta = re.sub(r'\.[0-9]+', '', duration)
        else:
            duration_timedelta = 0
        return int(duration_timedelta)
