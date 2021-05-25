import re
import random
import socket
import datetime
import uuid
from time import mktime, sleep
import feedparser
from mongoengine import PULL, NULLIFY, CASCADE
from mongoengine.document import Document, EmbeddedDocument
from mongoengine.fields import BooleanField, DateTimeField, EmbeddedDocumentField, EmbeddedDocumentListField, IntField, LazyReferenceField, ListField, ReferenceField, StringField, URLField, ObjectIdField
from mongoengine.queryset.manager import queryset_manager
from mongoengine.errors import DoesNotExist

from telegram.parsemode import ParseMode
from telegram.error import TimedOut
from castpod.utils import local_download
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

class User(Document):
    # meta = {'queryset_class': UserQuerySet}
    user_id = IntField(primary_key=True)
    username = StringField()
    name = StringField()

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
        if not podcast.name: # if podcast never been initialized, ..
            result = podcast.parse_feed()
            if not result: return
            podcast.update_feed(result, init=True)
        podcast.update(push__subscribers=self)

    def unsubscribe(self, podcast):
        podcast.update(pull__subscribers=self)

    def toggle_fav(self, podcast):
        if self in podcast.fav_subscribers:
            podcast.update(pull__fav_subscribers=self)
        else:
            podcast.update(push__fav_subscribers=self)



class Episode(Document):
    index = IntField(required=True) # 需要废除!!
    episode_id = StringField(primary_key=True, default=uuid.uuid4().hex)
    link = StringField()
    title = StringField(unique=True)
    subtitle = StringField()
    summary = StringField()
    host = StringField()
    timeline = StringField()
    published_time = DateTimeField()
    updated_time = DateTimeField()
    message_id = IntField()  # message_id in podcast_vault
    file_id = StringField()
    shownotes = StringField()
    shownotes_url = URLField()
    timeline = StringField()
    is_downloaded = BooleanField(required=True, default=True)
    is_new = BooleanField(default=False)
    url = StringField()
    performer = StringField()
    logo = StringField()
    size = IntField()
    duration = IntField()
    fav_subscribers = ListField(ReferenceField(User, reverse_delete_rule=PULL))

    def set_shownotes_url(self, title, author):
        res = telegraph.create_page(
            title=f"{title}",
            html_content=self.shownotes,
            author_name=author
        )
        self.shownotes_url = f"https://telegra.ph/{res['path']}"
        return self.shownotes_url

    def set_content(self, logo):
        img_content = f"<img src='{logo}'>" if logo and ('img' not in self.shownotes) else ''
        self.shownotes = img_content + self.replace_invalid_tags(self.shownotes)
        return self.shownotes

    def set_timeline(self):
        shownotes = re.sub(r'</?(?:br|p|li).*?>', '\n', self.shownotes)
        # pattern = r'.+(?:[0-9]{1,2}:)?[0-9]{1,3}:[0-5][0-9].+'
        pattern = r'.+(?:[0-9]{1,2}[:：\'])?[0-9]{1,3}[:：\'][0-5][0-9].+'
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

class Podcast(Document):
    # meta = {'queryset_class': PodcastQuerySet}
    feed = StringField(required=True, unique=True)
    name = StringField(max_length=64)
    logo = StringField()
    host = StringField()
    website = StringField()
    email = StringField() # !!!
    channel = IntField() # 播客绑定的单独分发频道，由认证主播控制
    group = IntField() # 播客绑定的群组
    admin = ReferenceField(User, reverse_delete_rule=NULLIFY) # 认证的主播，暨 telegram 管理员
    episodes = ListField(ReferenceField(Episode, reverse_delete_rule=PULL))
    subscribers = ListField(ReferenceField(User, reverse_delete_rule=PULL))
    fav_subscribers = ListField(ReferenceField(User, reverse_delete_rule=PULL))
    updated_time = DateTimeField(default=datetime.datetime(1970,1,1))
    last_updated_time = DateTimeField()
    job_group = ListField(IntField(min_value=0, max_value=47))

    meta = {'indexes': [
        {'fields': ['$name', "$host"],
         'default_language': 'english',
         'weights': {'name': 10, 'host': 2}
        }
    ]}

    @classmethod
    def validate_feed(cls, feed, subsets=None):
        if subsets:
            podcast = cls.objects(feed=feed).only(subsets).first()
        else:
            podcast = cls.objects(feed=feed).first()
        return podcast or cls(feed=feed).save()

    @queryset_manager
    def subscribe_by(doc_cls, queryset, user, subsets=None):
        if subsets:
            return queryset(subscribers=user).only(subsets)
        else:
            return queryset(subscribers=user)

    @queryset_manager
    def fav_by(doc_cls, queryset, user, subsets=None):
        if subsets:
            return queryset(fav_subscribers=user).only(subsets)
        else:
            return queryset(fav_subscribers=user)

    def parse_feed(self):
        result = feedparser.parse(self.feed)
        if str(result.status)[0] != '2' and str(result.status)[0] != '3':
            self.delete()
            raise Exception(f'Feed open error, status: {result.status}')
        if not result.entries: 
            self.delete()
            print('feed has no entries!')
            # raise Exception(f'Feed has no entries.')
            return
        updated_time = result.feed.get('updated_parsed') or result.entries[0].updated_parsed
        self.updated_time = datetime.datetime.fromtimestamp(mktime(updated_time))
        self.save()
        return result

    def check_update(self, context):
        result = self.parse_feed()
        if not result : return
        self.last_updated_time = self.episodes[0].published_time
        if self.last_updated_time < self.updated_time:
            context.bot.send_message(dev_user_id, f'`{self.name}` 有更新：\n\n上次发布\n`{self.last_updated_time}`\n\n最近发布\n`{self.updated_time}`')
            self.update_feed(result, init=False)
            context.bot.send_message(dev_user_id, '更新结束，进入下载阶段')
        else:
            context.bot.send_message(dev_user_id, f'`{self.name}：未检测到更新`')
        self.update(set__episodes=sorted(self.episodes, key=lambda x:x.published_time, reverse=True))
        for i, episode in enumerate(self.episodes):
            self.episodes[i].index = i
            if episode.is_downloaded:
                self.update(set__episodes=self.episodes)
                continue
            context.bot.send_message(dev_user_id, f'开始下载 `{self.name}`：`{episode.title}`…')
            try:
                audio_file = local_download(episode, context)
                context.bot.send_audio(
                    chat_id=f'@{podcast_vault}',
                    audio=audio_file,
                    caption=(
                        f"🎙️ *{self.name}*\n"
                        f"总第 {len(self.episodes) - i} 期\n\n"
                        f"[订阅](https://t.me/{manifest.bot_id}?start={self.id})"
                        f" | [相关链接]({episode.shownotes_url or episode.set_shownotes_url(episode.title, self.name)})\n\n"
                        f"#{self.id}"
                    ),
                    title=episode.title,
                    performer=self.name,
                    duration=episode.duration,
                    thumb=self.logo
                )
            except TimedOut:
                print('download timed out!')
                pass
            except Exception as e:
                print(e)
                continue
            self.episodes[i].is_downloaded = True
            self.episodes[i].is_new = True
            self.update(set__episodes=self.episodes)
        self.save()
    
    def update_feed(self, result, init):
        feed = result.feed
        if not feed.get('title'):
            self.save()
            self.delete()
            raise Exception("Cannot parse feed name.")
        if init:
            self.set_job_group()
        self.name = unescape(feed.title)[:63]
        if len(self.name) == 63:
            self.name += '…'
        self.logo = feed['image']['href']

        if feed.get('author_detail'):
            self.host = unescape(feed.author_detail.get('name') or '')
        else:
            self.host = ''

        if self.host == self.name:
            self.host = ''
        self.website = feed.get('link')
        if feed.get('author_detail'):
            self.email = feed.author_detail.get('email') or ''
        else:
            self.email = ''
        for i, item in enumerate(result['items']):
            episode = self.parse_episode(init, item, i)
            if episode:
                # try:
                #     self.episodes.remove(episode.title)
                # except ValueError:
                #     pass
                # self.update(set__episodes=self.episodes)
                self.update(push__episodes__0=episode)
                self.save()
            elif not init: # 一旦发现没有更新，就停止检测
                break
        self.save()
        self.reload()
    
    def set_job_group(self):
        i = random.randint(0, 47)
        self.job_group = [i % 48 for i in range(i, i + 41, 8)]
        self.save()

    def parse_episode(self, init, item, i):
        published_time = datetime.datetime.fromtimestamp(
            mktime(item.published_parsed))

        if not item.get('enclosures'): 
            return

        if not init:
            if (published_time <= self.last_updated_time):
                print(published_time)
                return
            episode = Episode(index=i, is_downloaded=False, is_new = True)
        else:
            episode = Episode(index=i)

        episode.episode_id=item.get('id') or episode.episode_id
        audio = item.enclosures[0]

        # size = audio.get('length') or 0
        # if isinstance(size, str):
        #     match = re.match(r'([0-9]+)\..*',size)
        #     if match:
        #         size = match[1]

        episode.url=audio.get('href')
        episode.size = audio.get('length') or 0
        episode.size = int(episode.size)
        episode.performer=self.name
        episode.logo=item.get('image').href if item.get('image') else self.logo
        episode.duration=self.set_duration(item.get('itunes_duration'))

        episode.link = item.get('link')
        episode.title = unescape(item.get('title') or '')
        episode.subtitle = unescape(item.get('subtitle') or '')
        if episode.title == episode.subtitle:
            episode.subtitle = ''
        episode.summary = unescape(item.get('summary') or '')
        episode.shownotes = item.get('content')[0]['value'] if item.get('content') else episode.summary
        episode.set_content(episode.logo)
        episode.published_time = datetime.datetime.fromtimestamp(
            mktime(item.published_parsed))
        episode.updated_time = datetime.datetime.fromtimestamp(
            mktime(item.updated_parsed))
        episode.save()
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