
import re
from mongoengine import connect
from mongoengine.document import Document, EmbeddedDocument
from mongoengine.fields import BooleanField, DateTimeField, EmailField, EmbeddedDocumentField, IntField, ListField, ReferenceField, StringField, URLField
from mongoengine.queryset.base import PULL
from mongoengine.queryset.manager import queryset_manager
from telegram.parsemode import ParseMode
# from castpod.utils import local_download
from config import podcast_vault, dev_user_id, manifest, Mongo
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegraph import Telegraph
from html import unescape

connect(
    db=Mongo.db
    # username=Mongo.user,
    # password=Mongo.pwd
    # host=Mongo.remote_host
)


class Subscription(EmbeddedDocument):
    podcast = ReferenceField(
        'Podcast', required=True)
    is_saved = BooleanField(default=False)
    is_latest = BooleanField(default=True)


class User(Document):
    user_id = IntField(primary_key=True)
    name = StringField(required=True)
    username = StringField(unique=True, required=True)
    subscriptions = ListField(EmbeddedDocumentField(Subscription))


class Shownotes(EmbeddedDocument):
    content = StringField(required=True)
    url = URLField(unique=True)
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
        img_content = f"<img src='{self.logo_url or self.podcast_logo}'>" if 'img' not in shownotes else ''
        return img_content + self.replace_invalid_tags(shownotes)

    def set_timeline(self):
        shownotes = re.sub(r'</?(?:br|p|li).*?>', '\n', self.content)
        # self.shownotes = re.sub(r'(?<=:[0-5][0-9])[\)\]\}】」）》>]+', '', self.shownotes)
        # self.shownotes = re.sub(r'[\(\[\{【「（《<]+(?=:[0-5][0-9])', '', self.shownotes)
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
    podcast = ReferenceField('Podcast', required=True)
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

    # def parse(self, item):
    #     self.audio.performer = unescape(item.get('author') or '')
    #     if self.host == self.podcast.name:
    #         self.host = ''
    #     audio = item.enclosures[0]
    #     self.audio = Audio(
    #         url=audio.href,
    #         size=audio.get('length') or 0,
    #         performer=self.podcast.name,
    #         logo=item.get('image').href if item.get('image') else '',
    #         duration=self.set_duration(item.get('itunes_duration'))
    #     ).save()
    #     self.title = unescape(item.get('title') or '')
    #     self.subtitle = unescape(item.get('subtitle') or '')
    #     if self.title == self.subtitle:
    #         self.subtitle = ''
    #     self.content = item.get('content')
    #     self.summary = unescape(item.get('summary') or '')
    #     self.shownotes = Shownotes(self.content).save()
    #     self.published_time = item.published_parsed
    #     self.save()

    # def replace_invalid_tags(self, html_content):
    #     html_content = html_content.replace('h1', 'h3').replace('h2', 'h4')
    #     html_content = html_content.replace('cite>', "i>")
    #     html_content = re.sub(r'</?(?:div|span|audio).*?>', '', html_content)
    #     html_content = html_content.replace('’', "'")
    #     return html_content


class Podcast(Document):
    feed = URLField(required=True, unique=True)
    name = StringField(max_length=64)
    logo = URLField()
    host = StringField()
    website = URLField()
    email = EmailField(allow_ip_domain=True, allow_utf8_user=True)
    episodes = ListField(EmbeddedDocumentField(Episode))
    subscribers = ListField(ReferenceField(User, reverse_delete_rule=PULL))
    update_time = DateTimeField()
    job_group = ListField(IntField(min_value=0, max_value=47))


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
    #     outfile = os.path.splitext(infile)[0] + ".thumbnail.jpg"
    #     try:
    #         with Image.open(infile) as im:
    #             im.thumbnail(size=(320, 320))
    #             im.convert('RGB')
    #             im.save(outfile, "JPEG")
    #         self.thumbnail = outfile
    #     except Exception as e:
    #         print(e)
    #         self.thumbnail = ''




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


# class UserStats(EmbeddedDocument):
#     pass

# class CommandStats(UserStats):
#     name = StringField(required=True, unique=True)
#     count = IntField()

# class ListenStats(UserStats):
#     liked_

# class PodcastStats(Stats):
