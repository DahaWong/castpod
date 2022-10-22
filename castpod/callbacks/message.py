from datetime import timedelta
from email import message
from pickletools import optimize
from webbrowser import get
from bs4 import BeautifulSoup
import httpx
from httpx import Response
from requests import delete
from telegram import (
    Bot,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
    Update,
    MessageEntity,
)
from telegram.constants import ChatAction, ParseMode
from telegram.ext import CallbackContext
from telegram.error import TimedOut
from mutagen import File

from castpod.utils import (
    modify_logo,
    search_itunes,
    send_error_message,
    streaming_download,
    validate_path,
)
from ..models_new import (
    User,
    Podcast,
    UserSubscribePodcast,
    parse_feed,
)
from ..components import PodcastPage, ManagePage

# from ..utils import download, parse_doc
from config import manifest, dev
from ..constants import RIGHT_SEARCH_MARK, SHORT_DOMAIN, SPEAKER_MARK, STAR_MARK
import re


async def delete_message(update: Update, context: CallbackContext):
    await update.message.delete()


async def subscribe_feed(update: Update, context: CallbackContext):
    message = update.message
    chat_type = update.effective_chat.type
    await message.delete()
    urls = message.parse_entities([MessageEntity.URL]).values()
    thumbnail_large = thumbnail_small = None
    if len(urls) == 3:
        feed, thumbnail_large, thumbnail_small = urls
    else:
        feed = list(urls)[0]
    await message.reply_chat_action(action=ChatAction.TYPING)
    reply_msg = await message.reply_text(f"订阅中…")
    feed = re.sub(r"^https?:\/\/", "", feed).lower()  # normalize
    podcast, is_new_podcast = Podcast.get_or_create(feed=feed)
    user = User.get(User.id == update.effective_user.id)
    if is_new_podcast:
        podcast.initialize()
        # print(podcast.logo)
        podcast.logo.thumbnail_url = thumbnail_small
        podcast.logo.save()
        podcast.save()
    UserSubscribePodcast.get_or_create(user=user, podcast=podcast)
    in_group = (chat_type == "group") or (chat_type == "supergroup")
    kwargs = {"mode": "group"} if in_group else {}
    try:
        podcast_page = PodcastPage(podcast, **kwargs)
        logo = podcast.logo
        photo = logo.file_id or thumbnail_large or logo.url
        msg = await message.reply_photo(
            photo=photo,
            caption=podcast_page.text(),
            reply_markup=InlineKeyboardMarkup(podcast_page.keyboard()),
        )
        if not logo.file_id:
            podcast.logo.file_id = msg.photo[0].file_id
            podcast.logo.save()
            # TODO:then delete the local logo file.
        await reply_msg.delete()
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
        await send_error_message(user, "订阅失败 😢\ 请检查订阅文件是否受损。")


async def download_episode(update: Update, context: CallbackContext):
    message = update.message
    user = update.effective_user
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
    shownotes = episode.shownotes[0]
    shownotes.extract_chapters()
    timeline = ""
    if not shownotes.url:
        shownotes = await shownotes.generate_telegraph()
        shownotes.save()
    markup = InlineKeyboardMarkup(
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
                    "更多单集",
                    switch_inline_query_current_chat=f"{podcast.name}#",
                ),
            ],
        ]
    )
    if not episode.url:
        await message.reply_text(
            text=f"<b>{episode.title}</b>\n\n<a href='{shownotes.url}'>📖 本期附录</a>\n\n{timeline}",
            reply_markup=markup,
        )
        await reply_msg.delete()
        return
    # todo:not only mp3
    audio_local_path = f"public/audio/{podcast.id}/{episode.title}.mp3"
    logo_path = validate_path(f"public/logo/{podcast.id}/{episode.logo.id}.jpeg")
    if not episode.file_id:
        await reply_msg.edit_text("下载中…")
        await message.reply_chat_action(ChatAction.RECORD_VOICE)
        audio_local_path = await streaming_download(
            path=audio_local_path,
            url=episode.url,
            progress_msg=reply_msg,
        )
        await reply_msg.edit_text("正在发送，请稍候…")
        await message.reply_chat_action(ChatAction.UPLOAD_VOICE)
    try:
        if episode.chapters:
            timeline = "\n\n".join(
                [
                    f"{chapter.start_time}  {chapter.title}"
                    for chapter in episode.chapters
                ]
            )
        audio_msg = await message.reply_audio(
            audio=episode.file_id or audio_local_path,
            caption=f"<b>{episode.title}</b>\n\n<a href='{shownotes.url}'>📖 本期附录</a>\n\n{timeline}",
            reply_markup=markup,
            title=episode.title,
            performer=podcast.name,
            duration=episode.duration,
            thumb=logo_path or episode.logo.url or podcast.logo.url,
        )
        if not episode.file_id:
            episode.file_id = audio_msg.audio.file_id
            episode.save()
    except TimedOut:
        await message.reply_text("🕛 这期节目的体积略大，请稍等")
    except Exception as e:
        await send_error_message(user, "😞 下载失败，稍后再试试吧")
        raise e
    finally:
        await reply_msg.delete()


async def show_podcast(update: Update, context: CallbackContext):
    user = update.effective_user
    message = update.message
    if (
        message.reply_to_message
        and message.reply_to_message.from_user.username != manifest.bot_id
    ):
        return
    try:
        keywords = message.text
        podcast = (
            Podcast.select()
            .where(
                Podcast.name.contains(keywords)
                | Podcast.pinyin_abbr.startswith(keywords)
                | Podcast.pinyin_full.contains(keywords)
                | Podcast.host.contains(keywords)
            )
            .join(UserSubscribePodcast)
            .join(User)
            .where(User.id == user.id)
            .get()
        )
    except:
        await user.send_message(
            "😔 你的订阅里没有相关的播客",
            reply_markup=InlineKeyboardMarkup.from_button(
                InlineKeyboardButton(
                    f"搜索「{keywords}」",
                    switch_inline_query_current_chat=keywords,
                )
            ),
        )
        return
    page = PodcastPage(podcast)
    await message.reply_photo(
        photo=podcast.logo.file_id,
        caption=page.text(),
        reply_markup=InlineKeyboardMarkup(page.keyboard()),
    )
    await message.delete()


# async def search_podcast(update:Update, context:CallbackContext):
#     await update.message.reply_text(
#         text=RIGHT_SEARCH_MARK,
#         reply_markup=InlineKeyboardMarkup.from_button(
#             InlineKeyboardButton(
#                 '搜索播客', switch_inline_query_current_chat='')
#         )
#     )


async def subscribe_from_url(update: Update, context: CallbackContext):
    user = update.effective_user
    message = update.message
    url = message.text
    domain = re.match(SHORT_DOMAIN, url)[1]
    if not url.startswith("http"):
        url = "https://" + url
    reply = await message.reply_text("正在解析链接…")
    async with httpx.AsyncClient() as client:
        r = await client.get(url, follow_redirects=True)
    soup = BeautifulSoup(r.text, "html.parser")
    podcast_name = ""
    podcast_logo = soup.img["src"]
    title_text = soup.title.text
    await reply.delete()
    if domain == "xiaoyuzhoufm.com":
        match = re.search(r"([^\-]+?) \| 小宇宙", title_text)
        podcast_name = match[1].lstrip()
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
        await send_error_message(user, "请检查链接拼写是否有误 🖐🏻")
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
        await send_error_message(user, "解析失败，链接可能已经损坏 😵‍💫")
