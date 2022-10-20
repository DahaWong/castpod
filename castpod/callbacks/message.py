from webbrowser import get
from telegram import (
    Bot,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
    Update,
)
from telegram.constants import ChatAction, ParseMode
from telegram.ext import CallbackContext

from castpod.utils import streaming_download
from ..models_new import User, Podcast, UserSubscribePodcast
from ..components import PodcastPage, ManagePage

# from ..utils import download, parse_doc
from config import podcast_vault, manifest, dev
from ..constants import RIGHT_SEARCH_MARK, SPEAKER_MARK, STAR_MARK
import re


async def delete_message(update: Update, context: CallbackContext):
    await update.message.delete()


async def subscribe_feed(update: Update, context: CallbackContext):
    message = update.message
    chat_type = update.effective_chat.type
    await context.bot.send_chat_action(chat_id=message.chat_id, action="typing")
    subscribing_message = await message.reply_text(f"订阅中…")

    user = User.get(id=update.effective_user.id)
    podcast, is_new_podcast = Podcast.get_or_create(feed=message.text)
    if is_new_podcast:
        podcast.initialize()
        podcast.save()
    UserSubscribePodcast.create(user=user, podcast=podcast)
    in_group = (chat_type == "group") or (chat_type == "supergroup")
    kwargs = {"mode": "group"} if in_group else {}
    try:
        await subscribing_message.edit_text(
            f"成功订阅<b>{podcast.name}</b>",
        )

        podcast_page = PodcastPage(podcast, **kwargs)
        photo = podcast.logo.file_id or podcast.logo.url
        msg = await message.reply_photo(
            photo=photo,
            caption=podcast_page.text(),
            reply_markup=InlineKeyboardMarkup(podcast_page.keyboard()),
            parse_mode="HTML",
        )
        podcast.logo.file_id = msg.photo[0].file_id
        podcast.logo.save()
        await message.delete()
    except Exception as e:
        await subscribing_message.edit_text("订阅失败 :(")
        raise e


async def save_subscription(update: Update, context: CallbackContext):
    message = update.message
    parsing_note = await message.reply_text("正在解析订阅文件…")
    user = User.validate_user(update.effective_user)
    try:
        feeds = await parse_doc(context, user, message.document)
        feeds_count = len(feeds)
        subscribing_note = await parsing_note.edit_text(f"订阅中 (0/{feeds_count})")
        podcasts_count = 0
        failed_feeds = []
        for feed in feeds:
            podcast = None
            try:
                podcast = Podcast.validate_feed(feed["url"].lower())
                user.subscribe(podcast)
                podcasts_count += 1
            except Exception as e:
                podcast.delete()
                failed_feeds.append(feed["url"])
                continue
            await subscribing_note.edit_text(f"订阅中 ({podcasts_count}/{feeds_count})")

        if podcasts_count:
            newline = "\n"
            reply = (
                f"成功订阅 {feeds_count} 部播客！"
                if not len(failed_feeds)
                else (
                    f"成功订阅 {podcasts_count} 部播客，部分订阅源解析失败。"
                    f"\n\n可能损坏的订阅源："
                    # use Reduce ?
                    f"\n{newline.join(['`'+feed+'`' for feed in failed_feeds])}"
                )
            )
        else:
            reply = "订阅失败:( \n\n请检查订阅文件以及其中的订阅源是否受损"

        manage_page = ManagePage(
            podcasts=Podcast.subscribe_by(user, "name"), text=reply
        )

        await subscribing_note.delete()
        await message.reply_text(
            text=manage_page.text,
            reply_markup=ReplyKeyboardMarkup(
                manage_page.keyboard(), resize_keyboard=True, one_time_keyboard=True
            ),
        )

    except Exception as e:
        await parsing_note.delete()
        await message.reply_text(
            f"订阅失败 :(\n" f"请检查订阅文件是否完好无损；" f"若文件没有问题，请私信[开发者](tg://user?id={dev})。"
        )
        raise e


async def download_episode(update: Update, context: CallbackContext):
    message = update.message
    bot: Bot = context.bot
    chat = update.effective_chat
    fetching_msg = await message.reply_text("正在获取节目…")
    await chat.send_chat_action(ChatAction.RECORD_VOICE)
    match = re.match(r"(.+) #([0-9]+)", message.text)
    podcast = (
        Podcast.select()
        .where(Podcast.name == match[1])
        .join(UserSubscribePodcast)
        .join(User)
        .where(User.id == update.effective_user.id)
        .get()
    )
    episode = podcast.episodes[-int(match[2])]
    await chat.send_chat_action(ChatAction.UPLOAD_VOICE)
    if episode.message_id:
        await fetching_msg.delete()
        forwarded_message = await bot.forward_message(
            chat_id=chat.id,
            from_chat_id=f"@{podcast_vault}",
            message_id=episode.message_id,
        )
    else:
        progress_msg = await fetching_msg.edit_text("下载中…")
        audio_file, final_msg = await streaming_download(
            from_podcast=podcast.name,
            title=episode.title,
            url=episode.url,
            progress_msg=progress_msg,
        )
        uploading_msg = await final_msg.edit_text("正在发送，请稍候…")
        audio_msg: Message = None
        try:
            audio_msg = await bot.send_audio(
                chat_id=f"@{podcast_vault}",
                audio=audio_file,
                caption=(f"{SPEAKER_MARK} <b>{podcast.name}</b>\n" f"#{podcast.id}"),
                reply_markup=InlineKeyboardMarkup.from_row(
                    [
                        InlineKeyboardButton(
                            "订阅",
                            url=f"https://t.me/{manifest.bot_id}?start=p{podcast.id}",
                        ),
                        # InlineKeyboardButton("相关链接", url=episode.shownotes.url),
                    ]
                ),
                title=episode.title,
                performer=podcast.name,
                duration=episode.duration,
                thumb=episode.logo.file_id or episode.logo.url,
            )
        except Exception as e:
            raise e
        finally:
            await uploading_msg.delete()
        forwarded_message = await audio_msg.forward(chat.id)
        episode.message_id = audio_msg.id
        episode.file_id = audio_msg.audio.file_id
        episode.save()
    shownotes = episode.shownotes
    timeline = (
        shownotes.timeline if shownotes.timeline else shownotes.generate_timeline()
    )
    shownotes.save()
    await forwarded_message.edit_caption(
        caption=(timeline or episode.summary[:127] + "…"),
        reply_markup=InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "简介", url=shownotes.url or episode.link or podcast.website
                    ),
                    InlineKeyboardButton("收藏", callback_data=f"fav_ep_{episode.id}"),
                    InlineKeyboardButton(
                        "分享", switch_inline_query=f"{podcast.name}#{episode.id}"
                    ),
                ],
                [
                    InlineKeyboardButton("订阅列表", switch_inline_query_current_chat=""),
                    InlineKeyboardButton(
                        "单集列表", switch_inline_query_current_chat=f"{podcast.name}#"
                    ),
                ],
            ]
        ),
    )


async def show_podcast(update: Update, context: CallbackContext):
    message = update.message
    if (
        message.reply_to_message
        and message.reply_to_message.from_user.username != manifest.bot_id
    ):
        return
    podcast = (
        Podcast.select()
        .where(Podcast.name == message.text)
        .join(UserSubscribePodcast)
        .join(User)
        .where(User.id == update.effective_user.id)
        .get()
    )
    if not podcast:
        await message.reply_text("抱歉，没能理解这条指令。")
        return
    page = PodcastPage(podcast)
    photo = podcast.logo.file_id or podcast.logo.url
    msg = await message.reply_photo(
        photo=photo,
        caption=page.text(),
        reply_markup=InlineKeyboardMarkup(page.keyboard()),
    )
    podcast.logo.file_id = msg.photo[0].file_id
    podcast.logo.save()
    await message.delete()


# async def handle_audio(update:Update, context:CallbackContext):
#     message = update.message
#     if not (message and (message.from_user.id == 777000)):
#         return
#     match = re.match(f'{SPEAKER_MARK} .+?\n总第 ([0-9]+) 期', message.caption)
#     index = int(match[1])
#     podcast_id = list(message.parse_caption_entities().values()
#                       )[-1].replace('#', '')
#     podcast = Podcast.objects(id=podcast_id).only('episodes').first()
#     episodes = podcast.episodes
#     episodes[-index].update(set__message_id=message.forward_from_message_id)
#     episodes[-index].update(set__file_id=message.audio.file_id)
#     podcast.update(set__episodes=episodes)
#     episodes[-index].reload()
#     podcast.reload()


# async def search_podcast(update:Update, context:CallbackContext):
#     await update.message.reply_text(
#         text=RIGHT_SEARCH_MARK,
#         reply_markup=InlineKeyboardMarkup.from_button(
#             InlineKeyboardButton(
#                 '搜索播客', switch_inline_query_current_chat='')
#         )
#     )
