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
        context.user_data.update({
            'user': user,
            'tips':['search', 'help', 'logout','alert'],
        })

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

def about(update, context):
    if not check_login(update, context): return
    keyboard = [[InlineKeyboardButton("源    代    码", url = manifest.repo)],
                [InlineKeyboardButton("工    作    室", url = manifest.author_url)]]
    markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text(f"*{manifest.name}*  `{manifest.version}`\n@dahawong 出品", reply_markup=markup)

def search(update, context):
    if not check_login(update, context): return
    keyboard = [[InlineKeyboardButton('开    始', switch_inline_query_current_chat = '')]]

    message = update.message.reply_text(
        '🔎️',
        reply_markup = InlineKeyboardMarkup(keyboard)
    )

    Tips(from_command = 'search',
        text = (f"⦿ 点击「开始」按钮启动搜索模式。"
            f"\n⦿ 前往 Telegram `设置 → 外观 → 大表情 Emoji` 获得更好的显示效果"
            f"\n⦿ 推荐通过在对话框中输入 `@` 来唤出行内搜索模式"
        )
    ).send(update, context)

def manage(update, context):
    if not check_login(update, context): return
    user = context.user_data['user']
    podcast_names = user.subscription.keys()
    podcasts_count = len(podcast_names)
    rows_count = podcasts_count // 3 + bool(podcasts_count % 3)
    def row(i):
        row = [name for index, name in enumerate(podcast_names) if index // 3 == i]
        return row
    reply_message = update.message.reply_text(
        text = '请选择播客',
        reply_markup = ReplyKeyboardMarkup(
            [row(i) for i in range(rows_count)]+[['退出播客管理']], 
            resize_keyboard = True)
    )
    reply_message.delete()
    update.message.delete()

def settings(update, context):
    if not check_login(update, context): return
    keyboard = [["播客更新频率", "快捷置顶单集", "单集信息显示"],
                ["播客搜索范围", "快捷置顶播客", "单集排序方式"],
                ["退出偏好设置"]]
    message = update.message.reply_text(
        f'请选择需调整的偏好设置',
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    )

def help(update, context):
    if not check_login(update, context): return
    command_message_id = update.message.message_id

    keyboard = [[
        InlineKeyboardButton("阅  读  完  毕", 
        callback_data = f'delete_command_context_{command_message_id}')
    ]]

    update.message.reply_text(
        f"*{manifest.name} 使用说明*",# import constants
        reply_markup = InlineKeyboardMarkup(keyboard)
    )

def export(update, context):
    if not check_login(update, context): return
    user = context.user_data['user']
    update.message.reply_document(
        document = user.subscription_path, 
        filename = f"{user.name} 的 {manifest.name} 订阅.xml",
        thumb = "" # pathLib.Path/file-like, jpeg, w,h<320px, thumbnail
    )

def logout(update, context):
    if not check_login(update, context): return
    command_message_id = update.message.message_id
    keyboard = [[InlineKeyboardButton("返   回", callback_data = f"delete_command_context{command_message_id}"),
                 InlineKeyboardButton("注   销", callback_data = "logout")]]

    update.message.reply_text(
        "确认注销账号吗？\n",
        reply_markup = InlineKeyboardMarkup(keyboard)
    )

    Tips('logout', "⦿ 这将清除所有存储在后台的个人数据。").send(update, context)

class Tips(object):
    def __init__(self, from_command, text):
        self.command = from_command
        self.text = text
    def keyboard(self):
        return InlineKeyboardMarkup.from_button(
            InlineKeyboardButton("✓", callback_data=f'close_tips_{self.command}')
        )
    def send(self, update, context):
        if self.command not in context.user_data.get('tips'): 
            return
        update.message.reply_text(
            text = self.text,
            reply_markup = self.keyboard()
        )

def check_login(update, context):
    user = context.user_data.get('user')
    if not user:
        update.message.reply_text("请先登录：/start")
        return False
    else:
        return True