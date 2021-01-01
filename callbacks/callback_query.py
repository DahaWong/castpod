from telegram import InlineKeyboardButton, InlineKeyboardMarkup, error
import re
from models import Episode
from config import podcast_vault
from utils.downloader import local_download
from manifest import manifest
# import pprint

# Message
def delete_message(update, context):
    update.callback_query.delete_message()

def delete_command_context(update, context):
    pattern = r'(delete_command_context_)([0-9]+)'
    query = update.callback_query
    command_message_id = re.match(pattern, query.data)[2]
    query.delete_message()
    context.bot.delete_message(query.message.chat_id, command_message_id)

# Episode
def download_episode(update, context):
    query = update.callback_query
    bot = context.bot
    fetching_note = bot.send_message(query.from_user.id, "获取节目中，请稍候…")
    bot.send_chat_action(query.from_user.id, "record_audio")
    pattern = r'download_episode_(.+)_([0-9]+)'
    match = re.match(pattern, query.data)
    podcast_name, index = match[1], int(match[2])
    podcast = context.bot_data['podcasts'][podcast_name]
    episode = Episode(podcast_name, podcast.episodes[index])

    # pprint.pp(podcast.episodes[index])
    promise = context.dispatcher.run_async(
        bot.send_audio,
        chat_id = f'@{podcast_vault}',
        audio = episode.audio_url,
        caption = podcast.name,
        title = episode.title,
        performer = episode.host or podcast.host,
        thumb = episode.logo_url or podcast.logo_url
    )
    if (promise.done):
        try:
            audio_message = promise.result()
            fetching_note.delete()
            audio_message.forward(query.from_user.id)
        except error.BadRequest:
            print(episode.audio_url)
            # get file size?
            print("音频大小："+str(episode.audio_size))
            local_download_note = fetching_note.edit_text("下载中…")
            file_path = local_download(episode.audio_url)
            uploading_note = local_download_note.edit_text("正在转发…")
            bot.send_chat_action(query.from_user.id, "upload_audio")
            # this is Upload? Need async and error handling:
            audio_message = bot.send_audio(
                chat_id = f'@{podcast_vault}',
                audio = file_path,
                caption = f"{podcast.name}\n\n[返回个人主页](https://t.me/{manifest.bot_id})",
                title = episode.title,
                performer = episode.host or podcast.host,
                thumb = episode.logo_url or podcast.logo_url
            )
            success_note = uploading_note.edit_text("下载成功！")
            success_note.delete()
            forwarded_message = audio_message.forward(query.from_user.id)
            forwarded_message.edit_caption(
                caption = f"{podcast.name}"
            )
            forwarded_message.edit_reply_markup(
                reply_markup=InlineKeyboardMarkup.from_button(
                    InlineKeyboardButton(
                        "评    论", 
                        url=f"https://t.me/{podcast_vault}/{audio_message.message_id}"
                    )
                )
            )

# Tips

def close_tips(update, context):
    query = update.callback_query
    pattern = r'close_tips_(\w+)'
    from_command = re.match(pattern, query.data)[1]
    context.user_data['tips'].remove(from_command)
    delete_message(update, context)
    show_tips_alert = 'alert' in context.user_data['tips']
    if show_tips_alert:
        query.answer("阅读完毕，它不会再出现在对话框中～", show_alert = True)
        context.user_data['tips'].remove('alert')

# Account:

def logout(update, context):
    user = context.user_data.get('user')
    message = update.callback_query.message
    message.edit_text(
        "注销账号之前，您可能希望导出订阅数据？",
        reply_markup = InlineKeyboardMarkup.from_row([
            InlineKeyboardButton("直 接 注 销", callback_data="delete_account"),
            InlineKeyboardButton("导 出 订 阅", callback_data="export")
        ])
    )

def delete_account(update, context):
    user = context.user_data['user']
    message = update.callback_query.message
    deleting_note = message.edit_text("注销中…")
    if user.subscription.values():
        for podcast in user.subscription.values().podcast:
            podcast.subscribers.remove(user.user_id)
    context.user_data.clear()
    deleting_note.edit_text(
        "👋️", 
        reply_markup=InlineKeyboardMarkup.from_button(
            InlineKeyboardButton('重 新 开 始', url=f"https://t.me/{manifest.bot_id}?start=login")
        ))