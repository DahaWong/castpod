import re

from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InputMediaAudio,
    ReplyKeyboardMarkup,
    Update,
)

from telegram.ext import CallbackContext

from castpod.components import PodcastPage
from castpod.models import Episode, Podcast, User, UserSubscribePodcast
from config import manifest
from manifest import manifest


async def start(update: Update, context):
    message = update.message
    effective_user = update.effective_user
    user, is_new_user = User.get_or_create(id=effective_user.id)

    if is_new_user:
        user.name = effective_user.full_name
        user.save()
        msg = await message.reply_text(
            text=(
                f"欢迎使用 {manifest.name}！\n\n疑问或建议请询<a href='https://t.me/castpodchat'>内测聊天室</a>。"
            ),
            reply_markup=InlineKeyboardMarkup.from_button(
                InlineKeyboardButton("搜索播客", switch_inline_query_current_chat="")
            ),
        )
        await msg.pin()
    elif not context.args:
        await message.reply_text("欢迎回来！")
        return

    # if subscribing podcast via deep link:
    if context.args and context.args[0] != "login":
        match = re.match(r"^([0-9]*)$", context.args[0])
        podcast_id = int(match[1])
        podcast = Podcast.get(Podcast.id == podcast_id)
        if not podcast:
            await update.reply_message(
                f"抱歉，该播客不存在。请尝试在对话框输入 <code>@{manifest.bot_id} {podcast.name}</code> 检索。",
                reply_markup=InlineKeyboardMarkup.from_button(
                    InlineKeyboardButton(
                        "开始搜索", switch_inline_query_current_chat=podcast.name
                    )
                ),
            )
            return
        if (
            not UserSubscribePodcast.select()
            .where(
                UserSubscribePodcast.user == user,
                UserSubscribePodcast.podcast == Podcast,
            )
            .execute()
        ):
            subscribing_note = await message.reply_text("正在订阅…")
            UserSubscribePodcast.create(user=user, podcast=podcast)
            await subscribing_note.delete()
        page = PodcastPage(podcast)
        photo = podcast.logo.file_id or podcast.logo.url
        msg = await message.reply_photo(
            photo=photo,
            caption=page.text(),
            reply_markup=InlineKeyboardMarkup(page.keyboard()),
        )
        podcast.logo.file_id = msg.photo[0].file_id
        podcast.save()


async def search(update: Update, context: CallbackContext):
    await update.message.reply_text(
        text="🔍",
        reply_markup=InlineKeyboardMarkup.from_button(
            InlineKeyboardButton("搜索播客", switch_inline_query_current_chat="")
        ),
    )


async def about(update: Update, context: CallbackContext):
    keyboard = [
        [
            InlineKeyboardButton("源代码", url=manifest.repo),
            InlineKeyboardButton("工作室", url=manifest.author_url),
        ]
    ]
    await update.message.reply_text(
        text=(
            f"<b>{manifest.name}</b>  "
            f"<pre>{manifest.version}</pre> "
            f"by <a href='https://t.me/{manifest.author_id}'>{manifest.author}</a>\n"
        ),
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


async def show_help_info(update: Update, context: CallbackContext):
    message = update.message
    text_handler = (
        message.reply_text if message else update.callback_query.edit_message_text
    )
    doc_link = (
        "https://github.com/DahaWong/castpod/wiki/%E5%85%A5%E9%97%A8%E6%8C%87%E5%8D%97"
    )
    await text_handler(
        text=f"<a href='{doc_link}'>{manifest.name} 入门指南</a>",
        reply_markup=InlineKeyboardMarkup.from_row(
            [
                InlineKeyboardButton("删除账号", callback_data="logout"),
                InlineKeyboardButton("导出订阅", callback_data="export"),
            ]
        ),
    )
