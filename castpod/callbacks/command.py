import re

from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InputMediaAudio,
    ReplyKeyboardMarkup,
    Update,
)

from telegram.ext import CallbackContext

from castpod.components import ManagePage, PodcastPage
from castpod.models_new import Episode, Podcast, User
from config import manifest
from manifest import manifest

from ..constants import DOC_MARK, RIGHT_SEARCH_MARK, STAR_MARK


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
        podcast = Podcast.objects(id=podcast_id).first()
        if not podcast:
            await update.reply_message(
                f"抱歉，该播客不存在。如需订阅，请尝试在对话框输入 `@{manifest.bot_id} 播客关键词` 检索。"
            )
            return
        if not user in podcast.subscribers:
            subscribing_note = await message.reply_text("正在订阅…")
            user.subscribe(podcast)
            await subscribing_note.delete()
        page = PodcastPage(podcast)
        manage_page = ManagePage(Podcast.subscribe_by(user), f"`{podcast.name}` 订阅成功！")
        photo = podcast.logo.file_id or podcast.logo.url
        msg = await message.reply_photo(
            photo=photo,
            caption=page.text(),
            reply_markup=InlineKeyboardMarkup(page.keyboard()),
        )
        podcast.logo.file_id = msg.photo[0].file_id
        podcast.save()

        await message.reply_text(
            text=manage_page.text,
            reply_markup=ReplyKeyboardMarkup(manage_page.keyboard()),
        )


# async def star(update: Update, context: CallbackContext):
#     user = User.validate_user(update.effective_user)
#     page = ManagePage(Podcast.star_by(user, "name"), text="已启动收藏面板")
#     if context.chat_data.get("reply_keyboard"):
#         await context.chat_data["reply_keyboard"].delete()
#     msg = await update.message.reply_text(
#         text=page.text,
#         reply_markup=ReplyKeyboardMarkup(
#             page.keyboard(null_text="还没有收藏播客～", jump_to=DOC_MARK),
#             resize_keyboard=True,
#             one_time_keyboard=True,
#             selective=True,
#         ),
#     )
#     await update.message.delete()
#     context.chat_data.update(reply_keyboard=msg)


async def search(update: Update, context: CallbackContext):
    await update.message.reply_text(
        text=RIGHT_SEARCH_MARK,
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


# async def favorite(update: Update, context: CallbackContext):
#     user = User.validate_user(update.effective_user)
#     fav_episodes = Episode.objects(starrers=user)
#     if len(fav_episodes) == 1:
#         await update.message.reply_audio(audio=fav_episodes.first().file_id)
#     elif len(fav_episodes) >= 2 and len(fav_episodes) <= 5:
#         await update.message.reply_media_group(
#             media=list(
#                 map(
#                     lambda episode: InputMediaAudio(media=episode.file_id), fav_episodes
#                 )
#             )
#         )
#     elif len(fav_episodes) > 5:
#         #!!!
#         await update.message.reply_media_group(
#             media=list(map(lambda x: InputMediaAudio(x.file_id), fav_episodes))
#         )
#     else:
#         await update.message.reply_text(
#             text="还没有收藏的单集～",
#             reply_markup=InlineKeyboardMarkup.from_button(
#                 InlineKeyboardButton("我的订阅", switch_inline_query_current_chat="")
#             ),
#         )


# async def random(update: Update, context: CallbackContext):
#     await update.message.reply_text(
#         "功能开发中，敬请等待！", reply_to_message_id=update.effective_message.message_id
#     )


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
