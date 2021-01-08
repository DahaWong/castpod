from utils.parser import parse_opml
from models import Podcast
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardRemove, ReplyKeyboardMarkup, ChatAction
from components import PodcastPage, ManagePage
from base64 import urlsafe_b64encode as encode
from utils.downloader import local_download as download
from config import podcast_vault
from manifest import manifest
import re

def save_subscription(update, context):
    parsing_note = update.message.reply_text("正在解析订阅文件…")
    user = context.user_data['user']
    cached_podcasts = context.bot_data['podcasts']

    doc = update.message['document']
    doc_name, doc_file = doc['file_name'], context.bot.getFile(doc['file_id'])
    path = doc_file.download(f"public/subscriptions/{user.user_id}.xml")

    try:
        with open(path, 'r') as f:
            feeds = parse_opml(f)
    except Exception as e:
        print(e)
        parsing_note.delete()
        update.message.reply_text("订阅失败 :(\n请检查订阅文件是否格式正确/完好无损")
        return
    feeds_count = len(feeds)
    subscribing_note = parsing_note.edit_text(f"订阅中 (0/{feeds_count})")
    podcasts = []
    failed_feeds = []
    for i, feed in enumerate(feeds):
        if feed['name'] not in cached_podcasts.keys():
            try:
                promise = context.dispatcher.run_async(Podcast, feed_url=feed['url'])
                podcast = promise.result()
                if podcast:
                    cached_podcasts.update({podcast.name: podcast})
                    podcasts.append(podcast)
                    subscribing_note = subscribing_note.edit_text(f"订阅中 ({len(podcasts)}/{feeds_count})")
                else:
                    failed_feeds.append(feed['url'])
                    raise Exception(f"Error when adding feed {feed['url']}")
            except Exception as e: 
                print(e)
                failed_feeds.append(feed['url'])
                continue
        else:
            podcast = cached_podcasts[feed['name']]
            podcasts.append(podcast)
            subscribing_note = subscribing_note.edit_text(f"订阅中 ({len(podcasts)}/{feeds_count})")

    while len(podcasts) != len(failed_feeds) + len(podcasts):
        pass
    else:
        if len(podcasts):
            user.import_feeds(podcasts)
            newline = '\n'
            reply = f"成功订阅 {feeds_count} 部播客！" if not len(failed_feeds) else (
                f"成功订阅 {len(podcasts)} 部播客，部分订阅源解析失败。"
                f"\n\n可能损坏的订阅源："
                f"\n{newline.join(['`'+feed+'`' for feed in failed_feeds])}"
            )
        else:
                reply = "订阅失败:( \n\n请检查订阅文件以及其中的订阅源是否受损"

        subscribing_note.edit_text(
            reply, 
            reply_markup = InlineKeyboardMarkup.from_button(
                InlineKeyboardButton(
                    "查 看 订 阅 列 表", 
                    switch_inline_query_current_chat=""
                )
            )
        )

def subscribe_feed(update, context):
    context.bot.send_chat_action(chat_id = update.message.chat_id, action = 'typing')
    feed_url = update['message']['text']
    subscribing_message = update.message.reply_text(f"订阅中，请稍候…")
        
    user = context.user_data['user']
    podcasts = context.bot_data['podcasts']
    podcast = Podcast(feed_url) # 判断是否存在于音乐库中！
    user.add_feed(podcast)
    try:
        manage_page = ManagePage(
            podcast_names = user.subscription.keys(), 
            text = f"`{podcast.name}` 订阅成功！"
        )
        subscribing_message.delete()
        message = update.message
        message.reply_text(
            text = manage_page.text, 
            reply_markup = ReplyKeyboardMarkup(
                manage_page.keyboard(), 
                resize_keyboard=True,
                one_time_keyboard=True
            )
        )
        podcast_page = PodcastPage(podcast)
        message.reply_text(
            text = podcast_page.text(), 
            reply_markup=InlineKeyboardMarkup(podcast_page.keyboard())
        )
        message.delete()
        podcast.subscribers.add(user.user_id)
        if podcast.name not in podcasts.keys():
            podcasts.update({podcast.name: podcast})
    except Exception as e:
        print(e)
        subscribing_message.edit_text("订阅失败。可能是因为订阅源损坏 :(")

def download_episode(update, context):
    bot = context.bot
    fetching_note = bot.send_message(update.message.chat_id, "获取节目中…")
    bot.send_chat_action(update.message.chat_id, ChatAction.RECORD_AUDIO)
    pattern = r'🎙️ (.+) #([0-9]+)'
    match = re.match(pattern, update.message.text)
    podcast_name, index = match[1], int(match[2])
    print(podcast_name, index)
    podcast = context.bot_data['podcasts'].get(podcast_name)
    episode = podcast.episodes[-index]
    bot.send_chat_action(update.message.chat_id, ChatAction.UPLOAD_AUDIO)
    try:
        if episode.message_id:
            fetching_note.delete()
            forwarded_message = bot.forward_message(
                chat_id = context.user_data['user'].user_id,
                from_chat_id = f"@{podcast_vault}",
                message_id = episode.message_id
            )
        else:
            forwarded_message = direct_download(podcast, episode, fetching_note, context)
        update.message.delete()
        forwarded_message.edit_caption(
            caption = (
                f"[🎙️]({episode.get_shownotes_url()}) *{podcast.name.replace(' ', '')}*"
                f"\n\n{generate_tag(podcast.name)} "
                f"{' '.join([generate_tag(tag['term']) for tag in podcast.tags if podcast.tags])}"
            ),
            reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("订  阅  列  表", switch_inline_query_current_chat=""),
                    InlineKeyboardButton("单  集  列  表", switch_inline_query_current_chat = f"{podcast.name}")
                ], [
                    InlineKeyboardButton(
                    text = "评   论   区", 
                    url = f"https://t.me/{podcast_vault}/{forwarded_message.forward_from_message_id}")
                ]]
            )
        )
    except Exception as e:
        print(e)
        update.message.reply_text(f'*{podcast.name}* - {episode.title} 下载失败。请[联系开发者](https://t.me/dahawong)以获得更多帮助。')

def direct_download(podcast, episode, fetching_note, context):
    encoded_podcast_name = encode(bytes(podcast.name, 'utf-8')).decode("utf-8")
    downloading_note = fetching_note.edit_text("下载中…")
    if int(episode.audio_size) >= 20000000 or not episode.audio_size:
        audio_file = download(episode.audio_url, context)
    else:   
        audio_file = episode.audio_url
    tagged_podcast_name = '#'+ re.sub(r'[\W]+', '', podcast.name)
    uploading_note = downloading_note.edit_text("正在上传，请稍候…")
    audio_message = context.bot.send_audio(
        chat_id = f'@{podcast_vault}',
        audio = audio_file,
        caption = (
            f"<b>{podcast.name}</b>   "
            f"<a href='https://t.me/{manifest.bot_id}?start={encoded_podcast_name}'>订阅</a>"
            f"\n\n {tagged_podcast_name}"
        ),
        title = episode.title,
        performer = f"{podcast.name} | {episode.host or podcast.host}",
        duration = episode.duration.seconds,
        thumb = podcast.thumbnail or podcast.logo or podcast.logo_url,
        timeout = 1800,
        parse_mode = 'html'
    )
    uploading_note.delete()
    forwarded_message = audio_message.forward(context.user_data['user'].user_id)
    episode.message_id = audio_message.message_id
    return forwarded_message

def generate_tag(text):
    return '#' + re.sub(r'\W', '', text)

def exit_reply_keyboard(update, context):
    message = update.message
    message.reply_text(
        '好', 
        reply_markup = ReplyKeyboardRemove()
    ).delete()
    message.delete()