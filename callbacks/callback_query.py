from telegram import InlineKeyboardButton, InlineKeyboardMarkup

def delete_message(update, context):
    update.callback_query.delete_message()
