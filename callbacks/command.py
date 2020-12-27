from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
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
            '开始搜索播客', 
            switch_inline_query_current_chat = ""
            )
        ]]

        welcome_message = message.reply_text(
            welcome_text,
            reply_markup = InlineKeyboardMarkup(keyboard)
        )
        
        welcome_message.pin(disable_notification=True)

    else: # deeplinking subscription
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
    update.message.reply_text(f"*{manifest.name}*  `{manifest.version}`\n@dahawong 出品", reply_markup=markup)


def search(update, context):
    keyboard = [[InlineKeyboardButton('🔍️', switch_inline_query_current_chat = '')]]

    message = update.message.reply_text(
        f'点击下方按钮进入搜索模式',
        reply_markup = InlineKeyboardMarkup(keyboard)
    )


def manage(update, context):
    # 回复一个列表，用 `` 包裹每一个条目，每一页呈现的个数有限制，用按键翻页。复制并发送播客名字，即可获得该节目的所有信息/操作选项
    user = context.user_data['user']
    message_text = '请选择播客'

    keyboard = [[KeyboardButton(podcast_name)] for podcast_name in user.subscription.keys()]
    message = update.message.reply_text(
        text = message_text,
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard = True, one_time_keyboard = True)
    )

def settings(update, context):
    # 1. 更新频率
    # 2. 是否喜欢节目的同时置顶节目
    message = update.message.reply_text(
        f'欢迎使用 {manifest.name}！\n您可以发送 OPML 文件以批量导入播客订阅。'
    )
    return USERNAME


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
    message = update.message
    user_id = message['from_user']['id']
    user = context.bot_data["users"][user_id]
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