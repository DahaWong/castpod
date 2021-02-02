from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from config import manifest
from castpod.models import User, Podcast
from castpod.components import ManagePage, PodcastPage
from castpod.utils import validate_user


@validate_user
def start(update, context):
    run_async = context.dispatcher.run_async
    message = update.message
    user = User.objects(user_id=update.message.from_user.id)

    if context.args and context.args[0] != 'login':
        podcast_id = context.args[0]
        podcast = Podcast.objects(id=podcast_id)
        subscribing_note = run_async(
            update.message.reply_text, "正在订阅…").result()
        user.subscribe(podcast)
        page = PodcastPage(podcast)
        run_async(
            subscribing_note.edit_text,
            text=page.text(),
            reply_markup=InlineKeyboardMarkup(page.keyboard())
        )
    else:
        welcome_text = (
            f'欢迎使用 {manifest.name}！                                            '
            f'\n\n您可以发送 OPML 文件或 RSS 链接以*导入播客订阅*。\n'
            f'\n⚠️ 目前还*没有正式上线*，正在接入数据库的功能，测试完毕会在[内测群组](https://t.me/castpodchat)中告知。'
        )
        run_async(
            message.reply_text,
            text=welcome_text,
            reply_markup=InlineKeyboardMarkup.from_button(
                InlineKeyboardButton(
                    '搜索播客', switch_inline_query_current_chat=""
                )
            )
        )


def about(update, context):
    keyboard = [[InlineKeyboardButton("源代码", url=manifest.repo),
                 InlineKeyboardButton("工作室", url=manifest.author_url)]]
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


def favourites(update, context):
    run_async = context.dispatcher.run_async
    buttons = [
        [InlineKeyboardButton('播 客', switch_inline_query_current_chat='p'),
         InlineKeyboardButton('单 集', switch_inline_query_current_chat='e')],
        [InlineKeyboardButton(
            '订  阅  列  表', switch_inline_query_current_chat='')]
    ]

    run_async(
        update.message.reply_text,
        text='⭐️',
        reply_markup=InlineKeyboardMarkup(buttons)
    )

    # tips = (
    #     "⦿ 前往 Telegram `设置 → 外观 → 大表情 Emoji` 获得更好的显示效果\n"
    #     f"⦿ 在对话框中输入 `@{manifest.bot_id}` 以唤出管理面板，接着输入关键词即可搜索播客"
    # )


@validate_user
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


@validate_user
def setting(update, context):
    keyboard = [["╳"],
                ["播客更新频率", "快捷置顶单集", "单集信息显示"],
                ["播客搜索范围", "快捷置顶播客", "单集排序方式"], ]
    update.message.reply_text(
        f'已打开设置面板',
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    )


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


@validate_user
def export(update, context):
    user = User.objects(user_id=update.message.from_user.id)
    if not user.subscriptions:
        update.message.reply_text('你还没有订阅的播客，请先订阅再导出～')
    else:
        update.message.reply_document(
            document=user.opml(),
            # thumb = ""
        )


@validate_user
def logout(update, context):
    keyboard = [[InlineKeyboardButton("返回", callback_data=f"delete_command_context_{update.message.message_id}"),
                 InlineKeyboardButton("注销", callback_data="logout")]]

    update.message.reply_text(
        "确认注销账号吗？\n",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

    # Tips('logout', "⦿ 这将清除所有存储在后台的个人数据。").send(update, context)
