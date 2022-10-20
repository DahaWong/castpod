from email import message
from webbrowser import get
from bs4 import BeautifulSoup
import httpx
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

from castpod.utils import search_itunes, send_error_message, streaming_download
from ..models_new import User, Podcast, UserSubscribePodcast, parse_feed
from ..components import PodcastPage, ManagePage

# from ..utils import download, parse_doc
from config import podcast_vault, manifest, dev
from ..constants import RIGHT_SEARCH_MARK, SHORT_DOMAIN, SPEAKER_MARK, STAR_MARK
import re


async def delete_message(update: Update, context: CallbackContext):
    await update.message.delete()


async def subscribe_feed(update: Update, context: CallbackContext):
    message = update.message
    chat_type = update.effective_chat.type
    await context.bot.send_chat_action(chat_id=message.chat_id, action="typing")
    reply_msg = await message.reply_text(f"订阅中…")

    user = User.get(id=update.effective_user.id)
    podcast, is_new_podcast = Podcast.get_or_create(feed=message.text)
    if is_new_podcast:
        podcast.initialize()
        podcast.save()
    UserSubscribePodcast.create(user=user, podcast=podcast)
    in_group = (chat_type == "group") or (chat_type == "supergroup")
    kwargs = {"mode": "group"} if in_group else {}
    try:
        await reply_msg.edit_text(
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
        await reply_msg.edit_text("订阅失败 :(")
        podcast.delete_instance()
        raise e


async def save_subscription(update: Update, context: CallbackContext):
    message = update.message
    reply_msg = await message.reply_text("正在解析订阅文件…")
    user = User.validate_user(update.effective_user)
    try:
        feeds = await parse_doc(context, user, message.document)
        feeds_count = len(feeds)
        await reply_msg.edit_text(f"订阅中 (0/{feeds_count})")
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
            await reply_msg.edit_text(f"订阅中 ({podcasts_count}/{feeds_count})")

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

        await reply_msg.delete()
        await message.reply_text(
            text=manage_page.text,
            reply_markup=ReplyKeyboardMarkup(
                manage_page.keyboard(), resize_keyboard=True, one_time_keyboard=True
            ),
        )
    except Exception as e:
        await reply_msg.delete()
        await send_error_message("订阅失败 😢\ 请检查订阅文件是否受损。")


async def download_episode(update: Update, context: CallbackContext):
    message = update.message
    bot: Bot = context.bot
    chat = update.effective_chat
    reply_msg = await message.reply_text("正在获取节目…")
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
    if episode.message_id:
        await reply_msg.delete()
        forwarded_message = await bot.forward_message(
            chat_id=chat.id,
            from_chat_id=f"@{podcast_vault}",
            message_id=episode.message_id,
        )
    else:
        await reply_msg.edit_text("下载中…")
        await chat.send_chat_action(ChatAction.RECORD_VOICE)
        audio_file = await streaming_download(
            from_podcast=podcast.name,
            title=episode.title,
            url=episode.url,
            progress_msg=reply_msg,
        )
        await reply_msg.edit_text("正在发送，请稍候…")
        await chat.send_chat_action(ChatAction.UPLOAD_VOICE)
        logo = episode.logo
        await logo.download()
        logo.save()
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
                thumb=logo.local_path or logo.file_id,
            )
        except Exception as e:
            raise e
        finally:
            await reply_msg.delete()
        forwarded_message = await audio_msg.forward(chat.id)
        episode.message_id = audio_msg.id
        episode.file_id = audio_msg.audio.file_id
        episode.save()
    shownotes = episode.shownotes
    await forwarded_message.edit_caption(
        caption=f"{episode.summary[:64]}…\n\n<a href='{shownotes.url or episode.link}'>本期附录</a>",
        reply_markup=InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton("时间轴", callback_data="show_timeline_XXX"),
                    InlineKeyboardButton("收藏", callback_data=f"fav_ep_{episode.id}"),
                    InlineKeyboardButton(
                        "分享", switch_inline_query=f"{podcast.name}#{episode.id}"
                    ),
                ],
                [
                    InlineKeyboardButton("我的订阅", switch_inline_query_current_chat=""),
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


async def from_url(update: Update, context: CallbackContext):
    message = update.message
    url = message.text
    domain = re.match(SHORT_DOMAIN, url)[1]
    if not url.startswith("http"):
        url = "https://" + url
    reply = await message.reply_text("解析链接中…")
    async with httpx.AsyncClient() as client:
        r = await client.get(url, follow_redirects=True)
    soup = BeautifulSoup(r.text, "html.parser")
    podcast_name = ""
    podcast_logo = soup.img["src"]
    title_text = soup.title.text
    await reply.delete()
    if domain == "xiaoyuzhoufm.com":
        match = re.search(r"([^(:?\- )]+?) \| 小宇宙", title_text)
        podcast_name = match[1]
    elif domain == "google.com" or domain == "pca.st":
        podcast_name = title_text
    elif domain == "apple.com" or domain == "overcast.fm":  # use itunes id
        podcast_itunes_id = re.search(r"(?:id|itunes)([0-9]+)", url)[1]
        results = await search_itunes(itunes_id=podcast_itunes_id)
        podcast_name = results[0].get("collectionName")
        podcast_logo = results[0].get("artworkUrl600")
    elif domain == "castro.fm":
        feed_url = soup.find_all("a")[-1]["href"]
        podcast = parse_feed(feed_url)
        podcast_name = podcast["name"]
        podcast_logo = podcast["logo"].url
    else:
        await send_error_message("请检查链接拼写是否有误 🖐🏻")
        return

    if podcast_logo:
        await message.reply_photo(
            photo=podcast_logo,
            caption=f"<b>{podcast_name}</b>",
            reply_markup=InlineKeyboardMarkup.from_button(
                InlineKeyboardButton(
                    "订阅此播客", switch_inline_query_current_chat=podcast_name
                )
            ),
        )
    else:
        await send_error_message("解析失败，链接可能已经损坏 😵‍💫")
