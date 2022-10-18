# import datetime

# import io
# import re

# import feedparser
# import httpx
# from PIL import Image
# from telegram import InlineKeyboardButton, InlineKeyboardMarkup
# from telegram.error import TimedOut
# from telegraph import Telegraph

# from castpod.utils import download
# from config import dev, manifest, podcast_vault

# from .constants import SPEAKER_MARK

# telegraph = Telegraph()
# telegraph.create_account(
#     short_name=manifest.name,
#     author_name=manifest.name,
#     author_url=f'https://t.me/{manifest.bot_id}'
# )

# class Logo(EmbeddedDocument):
#     _path = StringField(required=True)
#     is_local = BooleanField(default=False)
#     url = URLField()
#     file_id = StringField()

#     @property
#     def path(self):
#         if not self.is_local:
#             data = io.BytesIO(httpx.get(self.url).content)
#             with Image.open(data) as im:
#                 # then process image to fit restriction:
#                 # 1. jpeg format
#                 im = im.convert('RGB')
#                 # 2. < 320*320
#                 size = (80, 80)
#                 im = im.resize(size, Image.ANTIALIAS)
#                 # 3. less than 200 kB !!
#                 im.save(self._path, "JPEG")
#                 # print(os.stat(path).st_size)
#             # with open(path, 'rb') as fr:
#                 # self._logo.put(fr, content_type='image/jpeg')
#                 # self.save()
#         # return self._logo
#         self.is_local = True
#         return self._path

#     @path.setter
#     def path(self, value):
#         self._path = value
#         self.save()


# class User(Document):
#     # meta = {'queryset_class': UserQuerySet}
#     user_id = IntField(primary_key=True)
#     username = StringField()
#     name = StringField()

#     @classmethod
#     def validate_user(cls, from_user, subsets=None):
#         if subsets:
#             user = cls.objects(user_id=from_user.id).only(subsets).first()
#         else:
#             user = cls.objects(user_id=from_user.id).first()
#         return user or cls(user_id=from_user.id, username=from_user.username, name=from_user.first_name).save()

#     def subscribe(self, podcast):
#         if self in podcast.subscribers:
#             return
#         if not podcast.name:  # if podcast has never been initialized, ..
#             result = podcast.parse_feed()
#             if not result:
#                 return
#             podcast.update_feed(result, init=True)
#         podcast.update(push__subscribers=self)

#     def unsubscribe(self, podcast):
#         podcast.update(pull__subscribers=self)
#         podcast.update(pull__starrers=self)

#     def toggle_fav(self, podcast):
#         if self in podcast.starrers:
#             podcast.update(pull__starrers=self)
#         else:
#             podcast.update(push__starrers=self)

#     def fav_ep(self, episode):
#         episode.update(push__starrers=self)

#     def unfav_ep(self, episode):
#         episode.update(pull__starrers=self)


# class Episode(Document):
#     from_podcast = ReferenceField('Podcast')  # reverse delete rule = ??? !!!
#     title = StringField(unique=True)
#     link = StringField()
#     subtitle = StringField()
#     summary = StringField()
#     host = StringField()
#     published_time = DateTimeField()
#     updated_time = DateTimeField()
#     message_id = IntField()  # message_id in podcast_vault
#     file_id = StringField()
#     shownotes = StringField()
#     _shownotes_url = URLField()
#     _timeline = StringField()
#     is_downloaded = BooleanField(required=True, default=True)
#     url = StringField()
#     performer = StringField()
#     _logo = EmbeddedDocumentField(Logo)
#     size = IntField()
#     duration = IntField()
#     starrers = ListField(ReferenceField(User, reverse_delete_rule=PULL))

#     @property
#     def logo(self):
#         if not self._logo:
#             self._logo = Logo(_path=f'public/logo/sub/{self.title}.jpeg')
#         return self._logo

#     @logo.setter
#     def logo(self, value):
#         self._logo = value

#     @property
#     def shownotes_url(self):
#         if not self._shownotes_url:
#             res = telegraph.create_page(
#                 title=f"{self.title}",
#                 html_content=self.shownotes,
#                 author_name=self.from_podcast.name
#             )
#             self._shownotes_url = f"https://telegra.ph/{res['path']}"
#         return self._shownotes_url

#     def set_content(self, logo_url):
#         img_content = f"<img src='{logo_url}'>" if logo_url and (
#             'img' not in self.shownotes) else ''
#         self.shownotes = img_content + \
#             self.replace_invalid_tags(self.shownotes)
#         return self.shownotes

#     @property
#     def timeline(self):
#         if not self._timeline:
#             shownotes = re.sub(r'</?(?:br|p|li).*?>', '\n', self.shownotes)
#             pattern = r'.+(?:[0-9]{1,2}[:：\'])?[0-9]{1,3}[:：\'][0-5][0-9].+'
#             matches = re.finditer(pattern, shownotes)
#             self._timeline = '\n\n'.join([re.sub(
#                 r'</?(?:cite|del|span|div|s).*?>', '', match[0].lstrip()) for match in matches])
#         return self._timeline

#     def replace_invalid_tags(self, html_content):
#         #!!!
#         html_content = html_content.replace('h1', 'h3').replace('h2', 'h4')
#         html_content = html_content.replace('cite>', "i>")
#         html_content = re.sub(r'</?(?:div|span|audio).*?>', '', html_content)
#         html_content = html_content.replace('’', "'")
#         return html_content


# class Podcast(Document):
#     # meta = {'queryset_class': PodcastQuerySet}
#     feed = StringField(required=True, unique=True)
#     name = StringField(max_length=64)  # 合理吗？
#     _logo = EmbeddedDocumentField(Logo)
#     host = StringField()
#     website = StringField()
#     email = StringField()  # !!!
#     channel = IntField()  # 播客绑定的单独分发频道，由认证主播控制
#     group = IntField()  # 播客绑定的群组
#     # 认证的主播，telegram 管理员
#     admin = ReferenceField(User, reverse_delete_rule=NULLIFY)
#     episodes = ListField(ReferenceField(Episode, reverse_delete_rule=PULL))
#     subscribers = ListField(ReferenceField(User, reverse_delete_rule=PULL))
#     starrers = ListField(ReferenceField(User, reverse_delete_rule=PULL))
#     _updated_time = DateTimeField(default=datetime.datetime(1970, 1, 1))

#     meta = {'indexes': [
#         {'fields': ['$name', "$host"],
#          'default_language': 'english',
#          'weights': {'name': 10, 'host': 2}
#          }
#     ]}

#     @property
#     def updated_time(self):
#         return self._updated_time

#     @updated_time.setter
#     def updated_time(self, value):
#         self._updated_time = datetime.datetime.fromtimestamp(mktime(value))

#     @property
#     def logo(self):
#         if not self._logo:
#             self._logo = Logo(_path=f'public/logo/{self.name}.jpeg')
#         return self._logo

#     @classmethod
#     def validate_feed(cls, feed, subsets=None):
#         if subsets:
#             podcast = cls.objects(feed=feed).only(subsets).first()
#         else:
#             podcast = cls.objects(feed=feed).first()
#         return podcast or cls(feed=feed).save()

#     @queryset_manager
#     def subscribe_by(doc_cls, queryset, user, subsets=None):
#         if subsets:
#             return queryset(subscribers=user).only(subsets)
#         else:
#             return queryset(subscribers=user)

#     @queryset_manager
#     def star_by(doc_cls, queryset, user, subsets=None):
#         if subsets:
#             return queryset(starrers=user).only(subsets)
#         else:
#             return queryset(starrers=user)

#     def parse_feed(self):
#         result = feedparser.parse(self.feed)
#         if not result.entries:
#             self.delete()
#             raise Exception(f'Feed has no entries.')
#         self.updated_time = result.feed.get(
#             'updated_parsed') or result.entries[0].get('updated_parsed')
#         self.save()
#         return result

#     async def check_update(self, context):
#         last_updated_time = self.updated_time
#         result = self.parse_feed()
#         if not result:
#             return
#         # await context.bot.send_message(
#         #     dev, f"{self.name}\n上次更新 {str(last_updated_time)}\n最近更新 {str(self.updated_time)}")
#         if last_updated_time < self.updated_time:
#             await context.bot.send_message(dev, f'{self.name} 检测到更新,更新中…')
#             self.update_feed(result, init=False)
#         # else:
#             # await context.bot.send_message(dev, f'{self.name} 未检测到更新')
#         for episode in self.episodes:
#             if episode.is_downloaded:
#                 continue
#             await context.bot.send_message(
#                 dev, f'开始下载：{self.name} - {episode.title}')
#             try:
#                 audio = download(episode, context)
#                 message = await context.bot.send_audio(
#                     chat_id=f'@{podcast_vault}',
#                     audio=audio,
#                     caption=(
#                         f"{SPEAKER_MARK} *{self.name}*\n\n"
#                         f"#{self.id}"
#                     ),
#                     reply_markup=InlineKeyboardMarkup.from_row(
#                         [InlineKeyboardButton('订阅', url=f'https://t.me/{manifest.bot_id}?start=p{self.id}'),
#                          InlineKeyboardButton('相关链接', url=episode.shownotes_url)]
#                     ),
#                     title=episode.title,
#                     performer=self.name,
#                     duration=episode.duration,
#                     thumb=episode.logo.path
#                 )
#                 episode.is_downloaded = True
#                 episode.message_id = message.message_id
#                 episode.file_id = message.audio.file_id
#                 episode.save()
#                 return message
#             except TimedOut as e:
#                 await context.bot.send_message(dev, '下载超时！')
#                 pass
#             except Exception as e:
#                 await context.bot.send_message(dev, f'{e}')
#                 continue

#     def update_feed(self, result, init):
#         feed = result.feed
#         if not feed.get('title'):
#             self.delete()
#             raise Exception("Cannot parse feed name.")
#         self.name = unescape(feed.title)[:63]
#         if len(self.name) == 63:
#             self.name += '…'
#         self.logo.url = feed['image']['href']
#         self.save()

#         if feed.get('author_detail'):
#             self.host = unescape(feed.author_detail.get('name') or '')
#         else:
#             self.host = ''
#         self.website = feed.get('link')
#         if feed.get('author_detail'):
#             self.email = feed.author_detail.get('email') or ''
#         else:
#             self.email = ''
#         for item in result['items']:
#             episode = self.parse_episode(init, item)
#             if episode:
#                 self.update(push__episodes=episode)
#                 self.save()
#             elif not init:  # 一旦发现没有更新，就停止检测
#                 break
#         sorted_episodes = sorted(
#             self.episodes, key=lambda x: x.published_time, reverse=True)
#         self.update(set__episodes=sorted_episodes)
#         self.save()

#     def parse_episode(self, init, item):
#         published_time = datetime.datetime.fromtimestamp(
#             mktime(item.published_parsed))

#         if not item.get('enclosures'):
#             return

#         if not init:
#             if (published_time <= self.episodes[0].published_time):
#                 return
#             episode = Episode(is_downloaded=False)
#         else:
#             episode = Episode()

#         audio = item.enclosures[0]

#         episode.from_podcast = self
#         episode.url = audio.get('href')
#         size = audio.get('length') or 0
#         episode.size = size if isinstance(size, int) else 0
#         episode.performer = self.name
#         episode.title = unescape(item.get('title') or '')
#         episode.logo.url = item.image.href if item.get(
#             'image') else self.logo.url
#         episode.duration = self.set_duration(item.get('itunes_duration'))
#         episode.link = item.get('link')
#         episode.subtitle = unescape(item.get('subtitle') or '')
#         if episode.title == episode.subtitle:
#             episode.subtitle = ''
#         episode.summary = unescape(item.get('summary') or '')
#         episode.shownotes = item.get('content')[0]['value'] if item.get(
#             'content') else episode.summary
#         episode.set_content(episode.logo.url)
#         episode.published_time = datetime.datetime.fromtimestamp(
#             mktime(item.published_parsed))
#         episode.updated_time = datetime.datetime.fromtimestamp(
#             mktime(item.updated_parsed))
#         episode.save()
#         self.save()
#         return episode


# def set_duration(self, duration: str) -> int:
#     duration_timedelta = None
#     if duration:
#         if ":" in duration:
#             time = duration.split(":")
#             if len(time) == 3:
#                 duration_timedelta = datetime.timedelta(
#                     hours=int(time[0]), minutes=int(time[1]), seconds=int(time[2])
#                 ).total_seconds()
#             elif len(time) == 2:
#                 duration_timedelta = datetime.timedelta(
#                     hours=0, minutes=int(time[0]), seconds=int(time[1])
#                 ).total_seconds()
#         else:
#             duration_timedelta = re.sub(r"\.[0-9]+", "", duration)
#     else:
#         duration_timedelta = 0
#     return int(duration_timedelta)
