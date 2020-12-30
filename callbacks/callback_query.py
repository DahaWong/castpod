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
            local_download_note = fetching_note.edit_text("正在切换至本地线路…")
            file_path = local_download(episode.audio_url)
            uploading_note = local_download_note.edit_text("正在获取节目…")
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
                        "评  论  区", 
                        url=f"https://t.me/{podcast_vault}/{audio_message.message_id}"
                    )
                )
            )

def toggle_like_episode(update, context, to:str):
    if (to == 'liked'):
        pin_method = pin_message
        button_text = '  ❤️  '
        callback_data = "unlike_episode"
    elif (to == 'unliked'):
        pin_method = unpin_message
        button_text = '喜    欢'
        callback_data = "like_episode"

    message = update.callback_query.message
    keyboard = [[InlineKeyboardButton("删    除", callback_data = "delete_message"), 
                 InlineKeyboardButton(button_text, callback_data = callback_data)
    ]]

    update.callback_query.edit_message_reply_markup(
        InlineKeyboardMarkup(keyboard)
    )

    pin_method(update, context)

def like_episode(update, context):
    toggle_like_episode(update, context, to="liked")

def unlike_episode(update, context):
    toggle_like_episode(update, context, to="unliked")
