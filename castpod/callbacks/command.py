from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from config import manifest
from castpod.models import User, Podcast
from castpod.components import ManagePage, PodcastPage
from castpod.utils import save_manage_starter, delete_update_message
from manifest import manifest


@delete_update_message
def start(update, context):
    run_async = context.dispatcher.run_async
    message = update.message
    user = User.validate_user(update.effective_user)

    if context.args and context.args[0] != 'login':
        podcast_id = context.args[0]
        podcast = Podcast.objects(id=podcast_id).first()
        if not podcast:
            update.reply_message(
                f'抱歉，该播客不存在。如需订阅，请尝试在对话框输入 `@{manifest.bot_id} 播客关键词` 检索。')
            return
        if not user in podcast.subscribers:
            subscribing_note = run_async(
                update.message.reply_text, "正在订阅…").result()
            user.subscribe(podcast)
            run_async(subscribing_note.delete)
        page = PodcastPage(podcast)
        manage_page = ManagePage(
            Podcast.subscribe_by(user), f'`{podcast.name}` 订阅成功！'
        )

        run_async(
            update.message.reply_text,
            text=page.text(),
            reply_markup=InlineKeyboardMarkup(page.keyboard()),
            parse_mode="HTML"
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
def favourites(update, context):
    run_async = context.dispatcher.run_async
    buttons = [
        InlineKeyboardButton(
            '播  客  收  藏', switch_inline_query_current_chat='p'),
        #  InlineKeyboardButton('单 集', switch_inline_query_current_chat='e')],
        InlineKeyboardButton(
            '订  阅  列  表', switch_inline_query_current_chat='')
    ]

    run_async(
        update.message.reply_text,
        text='⭐️',
        reply_markup=InlineKeyboardMarkup.from_column(buttons)
    )


@delete_update_message
def manage(update, context):
    run_async = context.dispatcher.run_async
    user = User.validate_user(update.effective_user)

    page = ManagePage(Podcast.subscribe_by(user, 'name'))
    msg = run_async(
        update.effective_message.reply_text,
        text=page.text,
        reply_markup=ReplyKeyboardMarkup(
            page.keyboard(), resize_keyboard=True, one_time_keyboard=True, selective=True)
    ).result()
    save_manage_starter(context.chat_data, msg)

@delete_update_message
def help(update, context):
    run_async = context.dispatcher.run_async
    message = update.message
    run_async(
        message.reply_text,
        text=f"*{manifest.name} 使用说明*\n\n",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("导出播客", callback_data="export"),
             InlineKeyboardButton('偏好设置', callback_data="settings")],
            [InlineKeyboardButton('注销账号', callback_data="logout"),
             InlineKeyboardButton('更多信息', callback_data="about")]
        ])
    )


