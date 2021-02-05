from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from config import manifest
from castpod.models import User, Podcast
from castpod.components import ManagePage, PodcastPage
from castpod.utils import save_manage_starter, delete_update_message


@delete_update_message
def start(update, context):
    run_async = context.dispatcher.run_async
    message = update.message
    user = User.validate_user(update.effective_user)

    if context.args and context.args[0] != 'login':
        podcast_id = context.args[0]
        podcast = Podcast.objects(id=podcast_id).first()
        subscribing_note = run_async(
            update.message.reply_text, "正在订阅…").result()
        user.subscribe(podcast)
        run_async(subscribing_note.delete)
        page = PodcastPage(podcast)
        manage_page = ManagePage(
            Podcast.of_subscriber(user), f'`{podcast.name}` 订阅成功！'
        )

        run_async(
            update.message.reply_text,
            text=page.text(),
            reply_markup=InlineKeyboardMarkup(page.keyboard())
        )

        run_async(
            update.message.reply_text,
            text=manage_page.text,
            reply_markup=ReplyKeyboardMarkup(manage_page.keyboard())
        )

    else:
        welcome_text = (
            f'欢迎使用 {manifest.name}！                                            '
            f'\n\n您可以发送 OPML 文件或 RSS 链接以*导入播客订阅*。\n'
            f'\n⚠️ 目前还*没有正式上线*，主要的问题是订阅的播客还不能更新。遇到问题或提供建议请移步[内测聊天室](https://t.me/castpodchat)。'
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


@delete_update_message
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


@delete_update_message
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


@delete_update_message
def manage(update, context):
    run_async = context.dispatcher.run_async
    user = User.validate_user(update.effective_user)
    message = update.message
    page = ManagePage(Podcast.of_subscriber(user, 'name'))
    msg = run_async(
        message.reply_text,
        text=page.text,
        reply_markup=ReplyKeyboardMarkup(
            page.keyboard(), resize_keyboard=True, one_time_keyboard=True)
    ).result()
    save_manage_starter(context.chat_data, msg)


@delete_update_message
def setting(update, context):
    keyboard = [["╳"],
                ["播客更新频率", "快捷置顶单集", "单集信息显示"],
                ["播客搜索范围", "快捷置顶播客", "单集排序方式"], ]
    msg = context.dispatcher.run_async(
        update.message.reply_text,
        f'已启动设置面板',
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    ).result()
    save_manage_starter(context.chat_data, msg)


@delete_update_message
def help(update, context):
    run_async = context.dispatcher.run_async
    message = update.message
    run_async(
        message.reply_text,
        text=(
            f"*{manifest.name} 使用说明*\n\n"
            "/about - 幕后信息\n"
            "/setting - 偏好设置（开发中）\n"
            "/export - 导出订阅\n"
            "/logout - 注销账号\n"
        ),
        reply_markup=InlineKeyboardMarkup.from_button(
            InlineKeyboardButton(
                "✓",
                callback_data=f'delete_message'
            )
        )
    )


@delete_update_message
def export(update, context):
    user = User.validate_user(update.effective_user)
    if not user.subscriptions:
        update.message.reply_text('你还没有订阅的播客，请先订阅再导出～')
    else:
        update.message.reply_document(
            document=user.generate_opml(),
            # thumb = ""
        )


@delete_update_message
def logout(update, context):
    keyboard = [[InlineKeyboardButton("返回", callback_data=f"delete_message"),
                 InlineKeyboardButton("注销", callback_data="logout")]]

    update.message.reply_text(
        "确认注销账号吗？\n",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

    # Tips('logout', "⦿ 这将清除所有存储在后台的个人数据。").send(update, context)
