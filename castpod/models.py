import datetime
from enum import unique
import feedparser
import socket
import random
import re
from mongoengine import connect
from mongoengine.document import Document, EmbeddedDocument
from mongoengine.fields import BooleanField, DateTimeField, EmailField, EmbeddedDocumentField, IntField, ListField, ReferenceField, StringField, URLField
from mongoengine.queryset.manager import queryset_manager
from telegram.parsemode import ParseMode
from castpod.utils import local_download
from config import podcast_vault, dev_user_id, manifest, Mongo
from base64 import urlsafe_b64encode as encode
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegraph import Telegraph
from html import unescape

connect(
    db=Mongo.db,
    username=Mongo.user,
    password=Mongo.pwd
)


class Subscription(EmbeddedDocument):
    podcast = ReferenceField(
        'Podcast', required=True)
    is_saved = BooleanField(default=False)
    is_latest = BooleanField(default=True)


class User(Document):
    user_id = IntField(primary_key=True)
    name = StringField(required=True)
    username = StringField(unique=True)
    subscriptions = ListField(EmbeddedDocumentField(Subscription))

    def subscribe(self, subscription):
        self.update(push__subscriptions__0=subscription)
        self.reload()

    def opml(self):
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
        path = f"./public/subscriptions/{self.name} - {manifest.name} 订阅源.xml"
        with open(path, 'w+') as f:
            f.write(opml)
        return path


class Shownotes(EmbeddedDocument):
    content = StringField(required=True)
    url = URLField(unique=True)

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
        self.reload()


class Audio(EmbeddedDocument):
    url = URLField(required=True)
    performer = StringField()
    logo = URLField()
    size = IntField()
    duration = IntField()


class Episode(EmbeddedDocument):
    podcast = ReferenceField('Podcast', required=True)
    audio = EmbeddedDocumentField(Audio)
    title = StringField(max_length=64, required=True)
    subtitle = StringField()
    content = StringField()
    summary = StringField()
    shownotes = EmbeddedDocumentField(Shownotes)
    timeline = StringField()
    published_time = DateTimeField()
    message_id = IntField()
    file_id = StringField()

    def replace_invalid_tags(self, html_content):
        html_content = html_content.replace('h1', 'h3').replace('h2', 'h4')
        html_content = html_content.replace('cite>', "i>")
        html_content = re.sub(r'</?(?:div|span|audio).*?>', '', html_content)
        html_content = html_content.replace('’', "'")
        return html_content

    # def parse_feed(self, url):
    #     socket.setdefaulttimeout(5)
    #     result = feedparser.parse(url)
    #     if str(result.status)[0] != '2' and str(result.status)[0] != '3':
    #         raise Exception(f'Feed URL Open Error, status: {result.status}')
    #     feed = result.feed
    #     self.name = feed.get('title')
    #     if not self.name:
    #         raise Exception("Cannot parse feed name.")
    #     self.name = unescape(self.name)[:32]
    #     if len(self.name) == 32:
    #         self.name += '…'
    #     self.logo_url = feed.get('image').get('href')
    #     # self.download_logo()
    #     self.episodes = self.set_episodes(result['items'])
    #     self.latest_episode = self.episodes[0]
    #     self.host = unescape(feed.author_detail.name)
    #     if self.host == self.name:
    #         self.host = ''
    #     self.website = feed.link
    #     self.email = feed.author_detail.get('email') or ""

    # def set_episodes(self, results):
    #     episodes = []
    #     for episode in results:
    #         episodes.append(Episode(self.name, episode, self.logo_url))
    #     return episodes

    # def download_logo(self):
    #     infile = f'public/logos/{self.name}.jpg'
    #     with open(infile, 'wb') as f:
    #         response = requests.get(
    #             self.logo_url, allow_redirects=True, stream=True)
    #         if not response.ok:
    #             raise Exception("URL Open Error: can't get this logo.")
    #         for block in response.iter_content(1024):
    #             if not block:
    #                 break
    #             f.write(block)
    #     self.logo = infile
        # outfile = os.path.splitext(infile)[0] + ".thumbnail.jpg"
        # try:
        #     with Image.open(infile) as im:
        #         im.thumbnail(size=(320, 320))
        #         im.convert('RGB')
        #         im.save(outfile, "JPEG")
        #     self.thumbnail = outfile
        # except Exception as e:
        #     print(e)
        #     self.thumbnail = ''


class Podcast(Document):
    feed = URLField(required=True, unique=True)
    name = StringField(max_length=64)
    logo = URLField()
    host = StringField()
    website = URLField()
    email = EmailField(allow_ip_domain=True, allow_utf8_user=True)
    episodes = ListField(EmbeddedDocumentField(Episode))
    subscribers = ListField(ReferenceField(User))
    update_time = DateTimeField()
    job_group = IntField(min_value=0, max_value=47)

    # def parse(self):
    #     pass

    # def set_job_group(self):
    #     i = random.randint(0, 47)
    #     self.update(job_group=[i % 48 for i in range(i, i + 41, 8)])
    #     self.reload()

    # def update(self, context):
    #     last_published_time = self.episodes[0].published_time
    #     self.parse()
    #     if self.episodes[0].published_time != last_published_time:
    #         try:
    #             audio_file = local_download(self.episodes[0], context)
    #             encoded_podcast_name = encode(
    #                 bytes(self.name, 'utf-8')).decode("utf-8")
    #             audio_message = context.bot.send_audio(
    #                 chat_id=f'@{podcast_vault}',
    #                 audio=audio_file,
    #                 caption=(
    #                     f"<b>{self.name}</b>\n"
    #                     f"总第 {len(self.episodes)} 期\n\n"
    #                     f"<a href='https://t.me/{manifest.bot_id}?start={encoded_podcast_name}'>订阅</a> | "
    #                     f"<a href='{self.episodes[0].get_shownotes_url()}'>相关链接</a>"
    #                 ),
    #                 title=self.episodes[0].title,
    #                 performer=self.name,
    #                 duration=self.episodes[0].duration.seconds,
    #                 thumb=self.logo_url,
    #                 parse_mode=ParseMode.HTML
    #                 # timeout = 1800
    #             )
    #             self.episodes[0].message_id = audio_message.message_id
    #             for user_id in self.subscribers:
    #                 forwarded_message = context.bot.forward_message(
    #                     chat_id=user_id,
    #                     from_chat_id=f"@{podcast_vault}",
    #                     message_id=self.episodes[0].message_id
    #                 )
    #                 forwarded_message.edit_caption(
    #                     caption=(
    #                         f"🎙️ *{self.name}*\n\n[相关链接]({self.episodes[0].get_shownotes_url() or self.website})"
    #                         f"\n\n{self.episodes[0].timeline}"
    #                     ),
    #                     reply_markup=InlineKeyboardMarkup([[
    #                         InlineKeyboardButton(
    #                             text="评     论     区",
    #                             url=f"https://t.me/{podcast_vault}/{audio_message.message_id}")
    #                     ], [
    #                         InlineKeyboardButton(
    #                             "订  阅  列  表", switch_inline_query_current_chat=""),
    #                         InlineKeyboardButton(
    #                             "单  集  列  表", switch_inline_query_current_chat=f"{self.name}")
    #                     ]]
    #                     )
    #                 )
    #         except Exception as e:
    #             context.bot.send_message(
    #                 dev_user_id, f'{context.job.name} 更新出错：`{e}`')


# class Episode(object):
#     """
#     Episode of a specific podcast.
#     """

#     def __init__(self, from_podcast: str, episode, podcast_logo):
#         self.podcast_name = from_podcast
#         self.podcast_logo = podcast_logo
#         self.host = unescape(episode.get('author')) or ''
#         if self.host == from_podcast:
#             self.host = ''
#         self.audio = self.set_audio(episode.enclosures)
#         if self.audio:
#             self.audio_url = self.audio.href
#             self.audio_size = self.audio.get('length') or 0
#         else:
#             self.audio_url = ""
#             self.audio_size = 0
#         self.title = self.set_title(episode.get('title'))
#         self.subtitle = unescape(episode.get('subtitle') or '')
#         if self.title == self.subtitle:
#             self.subtitle = ''
#         self.logo_url = episode.get(
#             'image').href if episode.get('image') else ''
#         self.duration = self.set_duration(episode.get('itunes_duration'))
#         self.content = episode.get('content')
#         self.summary = unescape(episode.get('summary') or '')
#         self.shownotes = self.set_shownotes()
#         self.timeline = self.set_timeline()
#         self.shownotes_url = ''
#         self.published_time = episode.published_parsed
#         self.message_id = None

#     def set_duration(self, duration: str) -> int:
#         duration_timedelta = None
#         if duration:
#             if ':' in duration:
#                 time = duration.split(':')
#                 if len(time) == 3:
#                     duration_timedelta = datetime.timedelta(
#                         hours=int(time[0]),
#                         minutes=int(time[1]),
#                         seconds=int(time[2])
#                     )
#                 elif len(time) == 2:
#                     duration_timedelta = datetime.timedelta(
#                         hours=0,
#                         minutes=int(time[0]),
#                         seconds=int(time[1])
#                     )
#             else:
#                 duration_timedelta = datetime.timedelta(seconds=int(duration))
#         else:
#             duration_timedelta = datetime.timedelta(seconds=0)
#         return duration_timedelta

#     def set_audio(self, enclosure):
#         if enclosure:
#             return enclosure[0]
#         else:
#             return None

#     def set_title(self, title):
#         if not title:
#             return ''
#         return unescape(title).lstrip(self.podcast_name)

#     def set_shownotes(self):
#         shownotes = unescape(
#             self.content[0]['value']) if self.content else self.summary
#         img_content = f"<img src='{self.logo_url or self.podcast_logo}'>" if 'img' not in shownotes else ''
#         return img_content + self.replace_invalid_tags(shownotes)

#     def set_timeline(self):
#         shownotes = re.sub(r'</?(?:br|p|li).*?>', '\n', self.shownotes)
#         # self.shownotes = re.sub(r'(?<=:[0-5][0-9])[\)\]\}】」）》>]+', '', self.shownotes)
#         # self.shownotes = re.sub(r'[\(\[\{【「（《<]+(?=:[0-5][0-9])', '', self.shownotes)
#         pattern = r'.+(?:[0-9]{1,2}:)?[0-9]{1,3}:[0-5][0-9].+'
#         matches = re.finditer(pattern, shownotes)
#         return '\n\n'.join([re.sub(r'</?(?:cite|del|span|div|s).*?>', '', match[0].lstrip()) for match in matches])
