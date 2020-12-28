from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from utils.persistence import persistence
from base64 import urlsafe_b64decode as decode
from manifest import manifest
from models import User, Feed
import re

def start(update, context):
    message = update.message
    user_id = message['from_user']['id']
    first_name = message['from_user']['first_name']

    if 'user' not in context.user_data.keys():
        user = User(first_name, user_id)
        context.user_data.update({"user": user})

    user = context.user_data['user']
    if (not context.args) or (context.args[0] == "login"):
        welcome_text = (
            f'欢迎使用 {manifest.name}。                                              '
            f'\n\n您可以发送 OPML 文件或 RSS 链接以*导入播客订阅*。\n'
            f'\n\n以下是全部的操作指令，在对话框输入 `/` 即可随时唤出'
            f'\n\n/search：搜索播客'
            f'\n/manage：管理订阅'
            f'\n/about：幕后信息'
            f'\n/help：使用说明'
            f'\n\n/export：导出订阅'
            f'\n/logout：退出登录'
        )

        keyboard = [[InlineKeyboardButton(
            '搜 索 播 客', 
            switch_inline_query_current_chat = ""
            )
        ]]

        welcome_message = message.reply_text(
            welcome_text,
            reply_markup = InlineKeyboardMarkup(keyboard)
        )
        
        welcome_message.pin(disable_notification=True)
    else: 
        feed = decode(context.args[0]).decode('utf-8')
        print(feed)
        cached_podcasts = context.bot_data['podcasts']
        for cached_podcast in cached_podcasts.values():
            if podcast_name == cached_podcast.name:
                podcast = cached_podcast
                # 这里应该用 setter:
                user.subscription.update({podcast.name: Feed(podcast)})
                break
        else: # not found, add new podcast
            # ⚠️ 需要检查是否存在于 podcasts，然后再分别处理：
            podcast = user.add_feed(podcast_feed)
        podcast.subscribers.add(user_id)
        print(user.subscription)


def about(update, context):
    keyboard = [[InlineKeyboardButton("源    代    码", url = manifest.repo)],
                [InlineKeyboardButton("工    作    室", url = manifest.author_url)]]
    markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text(f"*{manifest.name}*  `{manifest.version}`\n@dahawong 出品", reply_markup=markup)


def search(update, context):
    keyboard = [[InlineKeyboardButton('🔍️', switch_inline_query_current_chat = '')]]

    message = update.message.reply_text(
        f'点击下方按钮进入搜索模式',
        reply_markup = InlineKeyboardMarkup(keyboard)
    )

def manage(update, context):
    user = context.user_data['user']
    message_text = '请选择播客'

    column_buttons = [podcast_name for podcast_name in user.subscription.keys()]
    column_buttons.append('退出播客管理')
    message = update.message.reply_text(
        text = message_text,
        reply_markup = ReplyKeyboardMarkup.from_column(
            column_buttons, 
            resize_keyboard = True, 
            one_time_keyboard = True)
    )


def settings(update, context):
    message = update.message.reply_text(
        f'请选择需调整的偏好设置',
        reply_markup = ReplyKeyboardMarkup.from_column(
            ["调节更新频率", 
             "收藏节目的同时置顶消息",
             "收藏播客的同时置顶消息", 
             "退出偏好设置"]
        )
    )


def help(update, context):
    command_message_id = update.message.message_id

    keyboard = [[
        InlineKeyboardButton("阅  读  完  毕", 
        callback_data = f'delete_command_context_{command_message_id}')
    ]]

    update.message.reply_text(
        """**Podcasted 使用说明**""",# import constants
        reply_markup = InlineKeyboardMarkup(keyboard)
    )


def export(update, context):
    user = context.user_data['user']
    update.message.reply_document(
        document = user.subscription_path, 
        filename = f"{user.name} 的 Podcasted 订阅.xml",
        thumb = "" # pathLib.Path/file-like, jpeg, w,h<320px, thumbnail
    )


def logout(update, context):
    keyboard = [[InlineKeyboardButton("返   回", callback_data = "delete_message"),
                 InlineKeyboardButton("注   销", callback_data = "delete_account")]]

    update.message.reply_text(
        "您确定要注销账号吗？\n这将清除所有存储在后台的个人数据。",
        reply_markup = InlineKeyboardMarkup(keyboard)
    )