from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from base64 import urlsafe_b64decode as decode
from config import manifest
from castpod.models import User, Feed
from castpod.components import ManagePage, PodcastPage, Tips
from castpod.utils import check_login


def start(update, context):
    run_async = context.dispatcher.run_async
    message = update.message
    user_id = message['from_user']['id']
    first_name = message['from_user']['first_name']

    if 'user' not in context.user_data.keys():
        user = User(first_name, user_id)
        context.user_data.update({
            'user': user,
            'tips': ['search', 'help', 'logout', 'alert'],
            'is_home_pinned': False,
            'saved_podcasts': {},
            'saved_episodes': {}
        })

    user = context.user_data['user']
    if (not context.args) or (context.args[0] == "login"):
        welcome_text = (
            f'欢迎使用 {manifest.name}！                                            '
            f'\n\n您可以发送 OPML 文件或 RSS 链接以*导入播客订阅*。\n'
            f'\n⚠️ 目前还*没有正式上线*，数据有可能丢失，请妥善保管自己的订阅源～'
        )

        run_async(
            message.reply_text,
            text=welcome_text,
            reply_markup=InlineKeyboardMarkup.from_button(
                InlineKeyboardButton(
                    '搜索播客',
                    switch_inline_query_current_chat=""
                )
            )
        )
    else:
        podcast_name = decode(context.args[0]).decode('utf-8')
        podcast = context.bot_data['podcasts'][podcast_name]
        subscribing_note = run_async(
            update.message.reply_text, "订阅中…").result()
        # 完全一样的订阅逻辑，简化之：
        user.subscription.update({podcast_name: Feed(podcast)})
        podcast.subscribers.add(user_id)
        page = PodcastPage(podcast)
        run_async(
            subscribing_note.edit_text,
            text=page.text(),
            reply_markup=InlineKeyboardMarkup(page.keyboard())
        )


@check_login
def about(update, context):
    keyboard = [[InlineKeyboardButton("源     代     码", url=manifest.repo),
                 InlineKeyboardButton("工     作     室", url=manifest.author_url)]]
    context.dispatcher.run_async(
        update.message.reply_text(
            text=(
                f"*{manifest.name}*  "
                f"`{manifest.version}`"
                f"\nby [{manifest.author}](https://t.me/{manifest.author_id})\n"
            ),
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    )


@check_login
def favorites(update, context):
    run_async = context.dispatcher.run_async
    buttons = [
        [InlineKeyboardButton('播  客', switch_inline_query_current_chat='p'),
         InlineKeyboardButton('单  集', switch_inline_query_current_chat='e')],
        [InlineKeyboardButton('订 阅 列 表', switch_inline_query_current_chat='')]
    ]

    message = run_async(
        update.message.reply_text,
        text='⭐️',
        reply_markup=InlineKeyboardMarkup.from_column(buttons)
    ).result()

    if not context.user_data['is_home_pinned']:
        run_async(message.pin)
        context.user_data['is_home_pinned'] = True

    tips = (
        "⦿ 前往 Telegram `设置 → 外观 → 大表情 Emoji` 获得更好的显示效果\n"
        f"⦿ 在对话框中输入 `@{manifest.bot_id}` 以唤出管理面板，接着输入关键词即可搜索播客"
    )

    Tips(from_command='search', text=tips).send(update, context)


@check_login
def manage(update, context):
    run_async = context.dispatcher.run_async
    user = context.user_data['user']
    message = update.message
    podcast_names = user.subscription.keys()
    page = ManagePage(podcast_names)
    run_async(message.delete)
    run_async(
        message.reply_text,
        text=page.text,
        reply_markup=ReplyKeyboardMarkup(
            page.keyboard(), resize_keyboard=True, one_time_keyboard=True)
    )


@check_login
def setting(update, context):
    keyboard = [["╳"],
                ["播客更新频率", "快捷置顶单集", "单集信息显示"],
                ["播客搜索范围", "快捷置顶播客", "单集排序方式"], ]
    update.message.reply_text(
        f'已打开设置面板',
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    )


@check_login
def help(update, context):
    message = update.message
    message.reply_text(
        text=(
            f"*{manifest.name} 使用说明*\n\n"
            "/setting - 偏好设置（开发中）\n"
            "/export - 导出订阅\n"
            "/logout - 注销账号\n"
            "/about - 幕后信息\n"
        ),
        reply_markup=InlineKeyboardMarkup.from_button(
            InlineKeyboardButton(
                "✓",
                callback_data=f'delete_command_context_{message.message_id}'
            )
        )
    )


@check_login
def export(update, context):
    user = context.user_data['user']
    if not user.subscription:
        update.message.reply_text('你还没有订阅的播客，请先订阅再导出～')
        return
    update.message.reply_document(
        filename=f"{user.name} 的 {manifest.name} 订阅.xml",
        document=user.update_opml(),
        # thumb = ""
    )


@check_login
def logout(update, context):
    keyboard = [[InlineKeyboardButton("返回", callback_data=f"delete_command_context_{update.message.message_id}"),
                 InlineKeyboardButton("注销", callback_data="logout")]]

    update.message.reply_text(
        "确认注销账号吗？\n",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

    Tips('logout', "⦿ 这将清除所有存储在后台的个人数据。").send(update, context)
