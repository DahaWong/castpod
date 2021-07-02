import re
import io
import os
import random
import datetime
import requests
from time import mktime
import feedparser
from mongoengine import PULL, NULLIFY
from mongoengine.document import Document, EmbeddedDocument
from mongoengine.fields import BooleanField, DateTimeField, EmbeddedDocumentField, FileField, ImageField, IntField, ListField, ReferenceField, StringField, URLField
from mongoengine.queryset.manager import queryset_manager
from telegram.error import TimedOut
from castpod.utils import local_download
from config import podcast_vault, dev, manifest
from telegraph import Telegraph
from html import unescape
from .constants import SPEAKER_MARK
from PIL import Image

telegraph = Telegraph()
telegraph.create_account(
    short_name=manifest.name,
    author_name=manifest.name,
    author_url=f'https://t.me/{manifest.bot_id}'
)


class Setting(EmbeddedDocument):
    timeline_displayed = BooleanField(default=True)
    episodes_order_reversed = BooleanField(default=True)
    feed_freq = IntField(default=60)  # minutes


class Logo(EmbeddedDocument):
    _path = StringField(required=True)
    is_local = BooleanField(default=False)
    url = URLField()
    file_id = StringField()

    @property
    def path(self):
        if not self.is_local:
            print('not local')
            data = io.BytesIO(requests.get(self.url).content)
            with Image.open(data) as im:
                # then process image to fit restriction:
                # 1. jpeg format
                im = im.convert('RGB')
                # 2. < 320*320
                size = (80, 80)
                im = im.resize(size, Image.ANTIALIAS)
                # 3. less than 200 kB !!
                im.save(self._path, "JPEG")
                # print(os.stat(path).st_size)
            # with open(path, 'rb') as fr:
                # self._logo.put(fr, content_type='image/jpeg')
                # self.save()
        # return self._logo
        self.is_local = True
        return self._path

    @path.setter
    def path(self, value):
        self._path = value
        self.save()


class User(Document):
    # meta = {'queryset_class': UserQuerySet}
    user_id = IntField(primary_key=True)
    username = StringField()
    name = StringField()
    bonus = IntField(default=0)
    settings = EmbeddedDocumentField(Setting)

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
        if not podcast.name:  # if podcast has never been initialized, ..
            result = podcast.parse_feed()
            if not result:
                return
            podcast.update_feed(result, init=True)
        podcast.update(push__subscribers=self)

    def unsubscribe(self, podcast):
        podcast.update(pull__subscribers=self)
        podcast.update(pull__starrers=self)

    def toggle_fav(self, podcast):
        if self in podcast.starrers:
            podcast.update(pull__starrers=self)
        else:
            podcast.update(push__starrers=self)

    def fav_ep(self, episode):
        episode.update(push__starrers=self)

    def unfav_ep(self, episode):
        episode.update(pull__starrers=self)


class Episode(Document):
    from_podcast = ReferenceField('Podcast')  # reverse delete rule = ??? !!!
    title = StringField(unique=True)
    link = StringField()
    subtitle = StringField()
    summary = StringField()
    host = StringField()
    published_time = DateTimeField()
    updated_time = DateTimeField()
    message_id = IntField()  # message_id in podcast_vault
    file_id = StringField()
    shownotes = StringField()
    _shownotes_url = URLField()
    _timeline = StringField()
    is_downloaded = BooleanField(required=True, default=True)
    is_new = BooleanField(default=False)
    url = StringField()
    performer = StringField()
    _logo = EmbeddedDocumentField(Logo)
    size = IntField()
    duration = IntField()
    starrers = ListField(ReferenceField(User, reverse_delete_rule=PULL))

    @property
    def logo(self):
        if not self._logo:
            self._logo = Logo(_path=f'public/logo/sub/{self.title}.jpeg')
        return self._logo

    @logo.setter
    def logo(self, value):
        self._logo = value

    @property
    def shownotes_url(self):
        if not self._shownotes_url:
            res = telegraph.create_page(
                title=f"{self.title}",
                html_content=self.shownotes,
                author_name=self.from_podcast.name
            )
            self._shownotes_url = f"https://telegra.ph/{res['path']}"
        return self._shownotes_url

    def set_content(self, logo_url):
        img_content = f"<img src='{logo_url}'>" if logo_url and (
            'img' not in self.shownotes) else ''
        self.shownotes = img_content + \
            self.replace_invalid_tags(self.shownotes)
        return self.shownotes

    @property
    def timeline(self):
        if not self._timeline:
            shownotes = re.sub(r'</?(?:br|p|li).*?>', '\n', self.shownotes)
            # pattern = r'.+(?:[0-9]{1,2}:)?[0-9]{1,3}:[0-5][0-9].+'
            pattern = r'.+(?:[0-9]{1,2}[:：\'])?[0-9]{1,3}[:：\'][0-5][0-9].+'
            matches = re.finditer(pattern, shownotes)
            self._timeline = '\n\n'.join([re.sub(
                r'</?(?:cite|del|span|div|s).*?>', '', match[0].lstrip()) for match in matches])
        return self._timeline

    def replace_invalid_tags(self, html_content):
        #!!!
        html_content = html_content.replace('h1', 'h3').replace('h2', 'h4')
        html_content = html_content.replace('cite>', "i>")
        html_content = re.sub(r'</?(?:div|span|audio).*?>', '', html_content)
        html_content = html_content.replace('’', "'")
        return html_content


class Podcast(Document):
    # meta = {'queryset_class': PodcastQuerySet}
    feed = StringField(required=True, unique=True)
    name = StringField(max_length=64)  # 合理？
    _logo = EmbeddedDocumentField(Logo)
    host = StringField()
    website = StringField()
    email = StringField()  # !!!
    channel = IntField()  # 播客绑定的单独分发频道，由认证主播控制
    group = IntField()  # 播客绑定的群组
    # 认证的主播，telegram 管理员
    admin = ReferenceField(User, reverse_delete_rule=NULLIFY)
    episodes = ListField(ReferenceField(Episode, reverse_delete_rule=PULL))
    subscribers = ListField(ReferenceField(User, reverse_delete_rule=PULL))
    starrers = ListField(ReferenceField(User, reverse_delete_rule=PULL))
    _updated_time = DateTimeField(default=datetime.datetime(1970, 1, 1))
    last_updated_time = DateTimeField()
    job_group = ListField(IntField(min_value=0, max_value=47))

    meta = {'indexes': [
        {'fields': ['$name', "$host"],
         'default_language': 'english',
         'weights': {'name': 10, 'host': 2}
         }
    ]}

    @property
    def updated_time(self):
        return self._updated_time

    @updated_time.setter
    def updated_time(self, value):
        self._updated_time = datetime.datetime.fromtimestamp(mktime(value))

    @property
    def logo(self):
        if not self._logo:
            self._logo = Logo(_path=f'public/logo/{self.name}.jpeg')
        return self._logo

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
    def star_by(doc_cls, queryset, user, subsets=None):
        if subsets:
            return queryset(starrers=user).only(subsets)
        else:
            return queryset(starrers=user)

    def parse_feed(self):
        # Do request using requests library and timeout
        try:
            res = requests.get(self.feed, timeout=5.0)
            res.raise_for_status()
        except requests.ReadTimeout:
            raise Exception(f'网络连接超时！')
        except requests.exceptions.HTTPError as e:
            self.delete()
            raise Exception(f'Feed open error, status: {res.status_code}')
        content = io.BytesIO(res.content)
        result = feedparser.parse(content)
        if not result.entries:
            self.delete()
            print('feed has no entries!')
            raise Exception(f'Feed has no entries.')
        self.updated_time = result.feed.get(
            'updated_parsed') or result.entries[0].updated_parsed
        # self.save()
        return result

    def check_update(self, context):
        result = self.parse_feed()
        if not result:
            return
        self.last_updated_time = self.episodes[-1].published_time
        if self.last_updated_time < self.updated_time:
            context.bot.send_message(
                dev, f'`{self.name}` 有更新：\n\n上次发布\n`{self.last_updated_time}`\n\n最近更新\n`{self.updated_time}`')
            self.update_feed(result, init=False)
        else:
            context.bot.send_message(dev, f'`{self.name}：未检测到更新`')
        for i, episode in enumerate(self.episodes):
            if episode.is_downloaded:
                continue
            else:
                print('开始下载！！')
            context.bot.send_message(
                dev, f'开始下载 `{self.name}`：`{episode.title}`…')
            try:
                audio = local_download(episode, context)
                context.bot.send_audio(
                    chat_id=f'@{podcast_vault}',
                    audio=audio,
                    caption=(
                        f"{SPEAKER_MARK} *{self.name}*\n"
                        f"总第 {len(self.episodes) - i} 期\n\n"
                        f"[订阅](https://t.me/{manifest.bot_id}?start={self.id})"
                        f" | [相关链接]({episode.shownotes_url})\n\n"
                        f"#{self.id}"
                    ),
                    title=episode.title,
                    performer=self.name,
                    duration=episode.duration,
                    thumb=episode.logo.path
                )
            except TimedOut as e:
                context.bot.send_message(dev, '下载超时！')
                pass
            except Exception as e:
                context.bot.send_message(dev, f'{e}')
                continue
            episode.is_downloaded = True
            episode.is_new = True
            episode.save()
        # self.save()

    def update_feed(self, result, init):
        feed = result.feed
        if not feed.get('title'):
            # self.save()
            self.delete()
            raise Exception("Cannot parse feed name.")
        if init:
            self.set_job_group()
        self.name = unescape(feed.title)[:63]
        if len(self.name) == 63:
            self.name += '…'
        self.logo.url = feed['image']['href']
        self.save()

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
        for item in result['items']:
            episode = self.parse_episode(init, item)
            if episode:
                self.update(push__episodes=episode)
                self.save()
            elif not init:  # 一旦发现没有更新，就停止检测
                break
        self.reload()
        sorted_episodes = sorted(
            self.episodes, key=lambda x: x.published_time, reverse=True)
        self.update(set__episodes=sorted_episodes)
        self.save()

    def set_job_group(self):
        i = random.randint(0, 47)
        self.job_group = [i % 48 for i in range(i, i + 41, 8)]
        self.save()

    def parse_episode(self, init, item):
        published_time = datetime.datetime.fromtimestamp(
            mktime(item.published_parsed))

        if not item.get('enclosures'):
            return

        if not init:
            if (published_time <= self.last_updated_time):
                print(published_time)
                return
            episode = Episode(is_downloaded=False, is_new=True)
        else:
            episode = Episode()

        audio = item.enclosures[0]

        # size = audio.get('length') or 0
        # if isinstance(size, str):
        #     match = re.match(r'([0-9]+)\..*',size)
        #     if match:
        #         size = match[1]

        episode.from_podcast = self
        episode.url = audio.get('href')
        episode.size = int((audio.get('length')) or 0)
        episode.performer = self.name
        episode.title = unescape(item.get('title') or '')
        episode.logo.url = item.image.href if item.get(
            'image') else self.logo.url
        episode.duration = self.set_duration(item.get('itunes_duration'))

        episode.link = item.get('link')
        episode.subtitle = unescape(item.get('subtitle') or '')
        if episode.title == episode.subtitle:
            episode.subtitle = ''
        episode.summary = unescape(item.get('summary') or '')
        episode.shownotes = item.get('content')[0]['value'] if item.get(
            'content') else episode.summary
        episode.set_content(episode.logo.url)
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
