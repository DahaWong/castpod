from telegram import InlineKeyboardButton, InlineKeyboardMarkup, error, ReplyKeyboardRemove, ChatAction, InputMediaAudio
from models import Episode
from manifest import manifest
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
        for feed in user.subscription.values():
            if user.user_id in feed.podcast.subscribers:
                feed.podcast.subscribers.remove(user.user_id)
    context.user_data.clear()
    deleting_note.delete()
    success_note = context.bot.send_message(
        chat_id = user.user_id, 
        text = '您的账号已注销～', 
        reply_markup = ReplyKeyboardRemove())
    context.bot.send_message(
        chat_id = user.user_id, text = "👋️",
        reply_markup=InlineKeyboardMarkup.from_button(
            InlineKeyboardButton('重 新 开 始', url=f"https://t.me/{manifest.bot_id}?start=login")
    ))