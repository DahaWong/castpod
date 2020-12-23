from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from utils.persistence import persistence
from manifest import manifest
from models import User


def start(update, context):
    message = update.message
    message.reply_text(
        f'欢迎使用 {manifest.name}！\n\n您可以发送 OPML 文件或 RSS 链接以导入播客订阅。'
    )
    user_id = message['from_user']['id']
    first_name = message['from_user']['first_name']
    users = context.bot_data["users"]

    if user_id not in users.keys():
        user = User(first_name, user_id)
        context.bot_data["users"].update({user_id: user})  
         
    user = users[user_id]
    context.user_data.update({"user": user})

    print(user.subscription)


def about(update, context):
    keyboard = [[InlineKeyboardButton("源    代    码", url = manifest.repo)],
                [InlineKeyboardButton("工    作    室", url = manifest.author_url)]]
    markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_markdown(f"*{manifest.name}*  `{manifest.version}`", reply_markup=markup)


def search(update, context):
    message = update.message.reply_text(
        f'欢迎使用 {manifest.name}！\n您可以发送 OPML 文件以批量导入播客订阅。'
    )
    return USERNAME

def manage(update, context):
    message = update.message.reply_text(
        f'欢迎使用 {manifest.name}！\n您可以发送 OPML 文件以批量导入播客订阅。'
    )
    return USERNAME

def settings(update, context):
    message = update.message.reply_text(
        f'欢迎使用 {manifest.name}！\n您可以发送 OPML 文件以批量导入播客订阅。'
    )
    return USERNAME

def tips(update, context):
    message = update.message.reply_text(
        f'欢迎使用 {manifest.name}！\n您可以发送 OPML 文件以批量导入播客订阅。'
    )

def log_out(update, context):
    keyboard = [[InlineKeyboardButton("源    代    码", url = manifest.repo)],
                [InlineKeyboardButton("工    作    室", url = manifest.author_url)]]
    update.message.reply_text(
        "您确定要退出吗？这将清除所有后台存储的个人数据。"
    )