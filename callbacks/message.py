from utils.parser import parse_opml
from models import Podcast
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, ChatAction, ParseMode, ReplyKeyboardRemove
from components import PodcastPage, ManagePage
from config import podcast_vault, dev_user_id
from callbacks.command import check_login
from base64 import urlsafe_b64encode as encode
from utils.downloader import local_download as download
from manifest import manifest
import re


def save_subscription(update, context):
    if not check_login(update, context):
        return
    parsing_note = update.message.reply_text("正在解析订阅文件…")
    user = context.user_data['user']
    cached_podcasts = context.bot_data['podcasts']

    doc = update.message['document']
    doc_file = context.bot.getFile(doc['file_id'])
    doc_name = re.sub(r'.+(?=\.xml|\.opml?)',
                      str(user.user_id), doc['file_name'])
    # print(doc_file)
    path = doc_file.download(doc_name)
    # print(path)
    try:
        with open(path, 'r') as f:
            feeds = parse_opml(f)
    except Exception as e:
        print(e)
        parsing_note.delete()
        update.message.reply_text("订阅失败 :(\n请检查订阅文件是否格式正确/完好无损")
        return

    subscribing_note = parsing_note.edit_text(f"订阅中 (0/{len(feeds)})")
    podcasts = []
    failed_feeds = []
    for feed in feeds:  
        if feed['name'] not in cached_podcasts.keys():
            try:
                podcast = Podcast(feed['url'])
                podcasts.append(podcast)
                podcast.subscribers.add(user.user_id)
                cached_podcasts.update({podcast.name: podcast})
            except Exception as e:
                print(e)
                failed_feeds.append(feed['url'])
                return
        else:
            podcast = cached_podcasts[feed['name']]
            podcasts.append(podcast)
            podcast.subscribers.add(user.user_id)
        subscribing_note.edit_text(f"订阅中 ({len(podcasts)}/{len(feeds)})")

    if len(podcasts):
        user.import_feeds(podcasts)
        newline = '\n'
        reply = f"成功订阅 {len(feeds)} 部播客！" if not len(failed_feeds) else (
            f"成功订阅 {len(podcasts)} 部播客，部分订阅源解析失败。"
            f"\n\n可能损坏的订阅源："
            f"\n{newline.join(['`'+feed+'`' for feed in failed_feeds])}"
        )
    else:
        reply = "订阅失败:( \n\n请检查订阅文件以及其中的订阅源是否受损"

    subscribing_note.edit_text(
        text=reply,
        reply_markup=InlineKeyboardMarkup.from_button(
            InlineKeyboardButton(
                "订阅列表",
                switch_inline_query_current_chat=""
            )
        )
    )


def subscribe_feed(update, context):
    if not check_login(update, context):
        return
    context.bot.send_chat_action(
        chat_id=update.message.chat_id, action='typing')
    feed_url = update['message']['text']
    subscribing_message = update.message.reply_text(f"订阅中，请稍候…")

    user = context.user_data['user']
    podcasts = context.bot_data['podcasts']
    podcast = Podcast(feed_url)  # 判断是否存在于音乐库中！
    user.add_feed(podcast)
    try:
        manage_page = ManagePage(
            podcast_names=user.subscription.keys(),
            text=f"`{podcast.name}` 订阅成功！"
        )
        subscribing_message.delete()
        message = update.message
        message.reply_text(
            text=manage_page.text,
            reply_markup=ReplyKeyboardMarkup(
                manage_page.keyboard(),
                resize_keyboard=True,
                one_time_keyboard=True
            )
        )
        podcast_page = PodcastPage(podcast)
        message.reply_text(
            text=podcast_page.text(),
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
    if not check_login(update, context):
        return
    bot = context.bot
    fetching_note = bot.send_message(update.message.chat_id, "获取节目中…")
    bot.send_chat_action(update.message.chat_id, ChatAction.RECORD_AUDIO)
    pattern = r'🎙️ (.+) #([0-9]+)'
    match = re.match(pattern, update.message.text)
    podcast_name, index = match[1], int(match[2])
    podcast = context.bot_data['podcasts'].get(podcast_name)
    episode = podcast.episodes[-index]
    bot.send_chat_action(update.message.chat_id, ChatAction.UPLOAD_AUDIO)
    if episode.message_id:
        fetching_note.delete()
        forwarded_message = bot.forward_message(
            chat_id=context.user_data['user'].user_id,
            from_chat_id=f"@{podcast_vault}",
            message_id=episode.message_id
        )
        forward_from_message = episode.message_id
    else:
        forwarded_message, forward_from_message = direct_download(
            podcast, episode, fetching_note, context)
    update.message.delete()

    forwarded_message.edit_caption(
        caption=(
            f"🎙️ <b>{podcast.name}</b>\n\n<a href='{episode.get_shownotes_url() or podcast.website}'>相关链接</a>"
            f"\n\n{episode.timeline}"
        ),
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton(
                text="评论区",
                url=f"https://t.me/{podcast_vault}/{forward_from_message}")
        ], [
            InlineKeyboardButton(
                "订阅列表", switch_inline_query_current_chat=""),
            InlineKeyboardButton(
                "单集列表", switch_inline_query_current_chat=f"{podcast.name}")

        ]])
    )
    # except Exception as e:
    #     print(e)
    #     update.message.reply_text(f'*{podcast.name}* - 《{episode.title}》下载失败。\n\n请联系[开发者](https://t.me/dahawong)以获得更多帮助。')


def direct_download(podcast, episode, fetching_note, context):
    encoded_podcast_name = encode(bytes(podcast.name, 'utf-8')).decode("utf-8")
    downloading_note = fetching_note.edit_text("下载中…")
    audio_file = download(episode, context)
    uploading_note = downloading_note.edit_text("正在上传，请稍候…")
    audio_message = context.bot.send_audio(
        chat_id=f'@{podcast_vault}',
        audio=audio_file,
        caption=(
            f"*{podcast.name}*"
            f"\n\n[订阅](https://t.me/{manifest.bot_id}?start={encoded_podcast_name})"
            f" | [相关链接]({episode.get_shownotes_url()})"
        ),
        title=episode.title,
        performer=f"{podcast.name} | {episode.host or podcast.host}" if podcast.host else podcast.name,
        duration=episode.duration.seconds,
        thumb=podcast.logo or podcast.logo_url,
        # timeout = 1800
    )
    uploading_note.delete()
    forwarded_message = audio_message.forward(
        context.user_data['user'].user_id)
    episode.message_id = audio_message.message_id
    return forwarded_message, audio_message.message_id


def exit_reply_keyboard(update, context):
    if not check_login(update, context):
        return
    message = update.message
    message.reply_text(
        '已退出管理面板',
        reply_markup=ReplyKeyboardRemove()
    ).delete()
    message.delete()


def show_feed(update, context):
    text = update.message.text
    user = context.user_data['user']
    if text in user.subscription.keys():
        feed_name = text
        feed = context.user_data['user'].subscription[feed_name]
        podcast = feed.podcast
        if podcast.name in context.user_data['saved_podcasts']:
            page = PodcastPage(podcast, save_text="❤️", save_action='unsave_podcast')
        else:
            page = PodcastPage(podcast)
        update.message.reply_text(
            text=page.text(),
            reply_markup=InlineKeyboardMarkup(page.keyboard())
        )
        update.message.delete()


def handle_audio(update, context):
    post = update.channel_post
    if not post: return
    if post.chat.username != podcast_vault:
        return
    podcast_name = re.match(r'🎙️ (.+)', post.caption)[1]
    index = int(re.match(r'总第 ([0-9]+) 期', post.caption)[1]) - 1
    podcast = context.bot_data['podcasts'][podcast_name]
    episode = podcast.episodes[index]
    episode.message_id = post.message_id
    context.bot.send_message(dev_user_id, f'message_id: {episode.message_id}')
