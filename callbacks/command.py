from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from utils.persistence import persistence
from manifest import manifest
from models import User


def start(update, context):
    message = update.message
    user_id = message['from_user']['id']
    first_name = message['from_user']['first_name']
    users = context.bot_data["users"]

    if user_id not in users.keys():
        user = User(first_name, user_id)
        context.bot_data["users"].update({user_id: user})
        context.user_data.update({"user": user})

    user = users[user_id]

    if not context.args:
        message.reply_text(
            f'嗨，{first_name}。欢迎使用 {manifest.name}！\n\n您可以发送 OPML 文件或 RSS 链接以导入播客订阅。'
        )

    else: # deeplinking
        podcast_id = context.args[0]

        # 搜索 id，订阅当前用户，反馈结果:
        podcasts = context.bot_data['podcasts']
        # 这可否编写一个可调用的函数？is_podcast_cached : 
        if podcast_id not in podcasts.keys():
            pass # 添加新播客
        podcast = podcasts[podcast_id]
        podcast.subscribers.update({user_id: user}) # 订阅当前用户

def about(update, context):
    keyboard = [[InlineKeyboardButton("源    代    码", url = manifest.repo)],
                [InlineKeyboardButton("工    作    室", url = manifest.author_url)]]
    markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_markdown(f"*{manifest.name}*  `{manifest.version}`", reply_markup=markup)


def search(update, context):
    # 支持行内搜索、命令搜索
    message = update.message.reply_text(
        f'欢迎使用 {manifest.name}！\n您可以发送 OPML 文件以批量导入播客订阅。'
    )
    return USERNAME


def manage(update, context):
    # 回复一个列表，用 `` 包裹每一个条目，每一页呈现的个数有限制，用按键翻页。复制并发送播客名字，即可获得该节目的所有信息/操作选项
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
    keyboard = [[InlineKeyboardButton("阅  读  完  毕", url = manifest.repo)]]
    message = update.message.reply_markdown_v2(
        """**本客户端使用说明**""",# import constants
        reply_markup = InlineKeyboardMarkup(keyboard)
    ) # 参考 instasaver 的 删除文章


def export(update, context):
    message = update.message
    user_id = message['from_user']['id']
    user = context.bot_data["users"][user_id]
    update.message.reply_document(
        document = user.subscription_path, 
        filename = f"{user.name} 的 Podcasted 订阅.xml",
        thumb = "" # pathLib.Path/file-like, jpeg, w,h<320px, thumbnail
    )


def log_out(update, context):
    keyboard = [[InlineKeyboardButton("源    代    码", url = manifest.repo)],
                [InlineKeyboardButton("工    作    室", url = manifest.author_url)]]

    update.message.reply_text(
        "您确定要退出吗？\n\n这将清除所有后台存储的个人数据。",
        reply_markup = InlineKeyboardMarkup(keyboard)
    )