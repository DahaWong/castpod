from email import message
from pickletools import optimize
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
from telegram.error import TimedOut
from mutagen import File

from castpod.utils import search_itunes, send_error_message, streaming_download
from ..models_new import (
    User,
    Podcast,
    UserSubscribePodcast,
    parse_feed,
)
from PIL import Image
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
        await send_error_message(update, "订阅失败 😢\ 请检查订阅文件是否受损。")


async def download_episode(update: Update, context: CallbackContext):
    message = update.message
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
    # todo:not only mp3
    audio_local_path = f"public/audio/{podcast.name}/{episode.title}.mp3"
    logo_path = "public/logo/{podcast.name}/{episode.logo.id}.jpeg"
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
        shownotes = episode.shownotes
        shownotes.extract_chapters()
        audio_metadata = File(audio_local_path)
        apic = audio_metadata.tags.get("APIC:")
        if apic:
            logo_data = apic.data
            with open(logo_path, "wb") as f:
                f.write(logo_data)
            with Image.open(logo_path) as im:
                # then process image to fit restriction:
                # 1. jpeg format
                im = im.convert("RGB")
                # 2. < 320*320
                size = (80, 80)
                im.thumbnail(size)
                # 3. less than 200 kB !!
                im.save(logo_path, "JPEG", optimize=True)
    try:
        timeline = ""
        if episode.chapters:
            timeline = "\n\n".join(
                [
                    f"{chapter.start_time}  {chapter.title}"
                    for chapter in episode.chapters
                ]
            )
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
        audio_msg = await message.reply_audio(
            audio=episode.file_id or audio_local_path,
            caption=f"<b>{episode.title}</b>\n\n{timeline}",
            reply_markup=markup,
            title=episode.title,
            performer=podcast.name,
            duration=episode.duration,
            thumb=logo_path,
        )
        if not episode.file_id:
            episode.file_id = audio_msg.audio.file_id
            episode.save()
    except TimedOut:
        await message.reply_text(
            "这期节目的体积略大，请稍等 🕛",
            reply_markup=InlineKeyboardMarkup.from_button(
                InlineKeyboardButton("好", callback_data="delete_message")
            ),
        )
    except Exception as e:
        await send_error_message(update, "下载失败，稍后再试试吧 😞")
        raise e
    finally:
        await reply_msg.delete()


async def show_podcast(update: Update, context: CallbackContext):
    message = update.message
    if (
        message.reply_to_message
        and message.reply_to_message.from_user.username != manifest.bot_id
    ):
        return
    try:
        podcast = (
            Podcast.select()
            .where(Podcast.name == message.text)
            .join(UserSubscribePodcast)
            .join(User)
            .where(User.id == update.effective_user.id)
            .get()
        )
    except:
        await send_error_message(update, "没有找到相应的播客，请重新尝试 😔")
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


# async def search_podcast(update:Update, context:CallbackContext):
#     await update.message.reply_text(
#         text=RIGHT_SEARCH_MARK,
#         reply_markup=InlineKeyboardMarkup.from_button(
#             InlineKeyboardButton(
#                 '搜索播客', switch_inline_query_current_chat='')
#         )
#     )


async def subscribe_from_url(update: Update, context: CallbackContext):
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
        await send_error_message(update, "请检查链接拼写是否有误 🖐🏻")
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
        await send_error_message(update, "解析失败，链接可能已经损坏 😵‍💫")
