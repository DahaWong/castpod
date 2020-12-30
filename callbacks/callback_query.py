from telegram import InlineKeyboardButton, InlineKeyboardMarkup, error
import re
from models import Episode
from config import podcast_vault
from utils.downloader import local_download
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
        chat_id = podcast_vault,
        audio = episode.audio_url,
        # caption = episode.summary[:1024] or episode.subtitle[:1024],
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
            fetching_note.delete()
            print(episode.audio_url)
            # get file size?
            local_download_note = bot.send_message(query.from_user.id, "正在切换至本地线路…")
            file_path = local_download(episode.audio_url)
            local_download_note.delete()
            bot.send_audio(
                chat_id = podcast_vault,
                audio = file_path,
                # caption = episode.summary[:1024] or episode.subtitle[:1024],
                title = episode.title,
                performer = podcast.host,
                thumb = podcast.logo_url
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
