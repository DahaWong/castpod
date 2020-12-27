from telegram import InlineKeyboardButton, InlineKeyboardMarkup
import re

# Message
def delete_message(update, context):
    update.callback_query.delete_message()

def delete_command_context(update, context):
    pattern = r'(delete_command_context_)([0-9]+)'
    query = update.callback_query
    command_message_id = re.match(pattern, query.data)[2]
    query.delete_message()
    context.bot.delete_message(query.message.chat_id, command_message_id)

def pin_message(update, context):
    update.callback_query.pin_message(disable_notification=True)

def unpin_message(update, context):
    update.callback_query.unpin_message()

# Podcast
# 其他按键如何处理？ callback_data
def toggle_like_podcast(update, context, to:str):
    if (to == 'liked'):
        pin_method = pin_message
        button_text = '  ❤️  '
        callback_data = "unlike_podcast"
    elif (to == 'unliked'):
        pin_method = unpin_message
        button_text = '喜    欢'
        callback_data = "like_podcast"

    message = update.callback_query.message
    keyboard = [[InlineKeyboardButton("退    订", callback_data = f"unsubscribe_podcast"),
                 InlineKeyboardButton(button_text, callback_data = callback_data)],
               [InlineKeyboardButton("单      集", callback_data = f"show_episodes")],
               [InlineKeyboardButton("关      于", callback_data = "podcast.website")]] # 删除记得加「撤销」
    update.callback_query.edit_message_reply_markup(InlineKeyboardMarkup(keyboard))
    pin_method(update, context)


def like_podcast(update, context):
    toggle_like_podcast(update, context, to="liked")

def unlike_podcast(update, context):
    toggle_like_podcast(update, context, to="unliked")

# Episode
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
