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
