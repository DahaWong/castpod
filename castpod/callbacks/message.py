from datetime import timedelta
import os
from time import time
from zhconv import convert
from bs4 import BeautifulSoup
from user_agent import generate_user_agent
import httpx
from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InputMediaPhoto,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
    Update,
    MessageEntity,
)
from telegram.constants import MessageLimit
from telegram.constants import ChatAction
from telegram.ext import CallbackContext
from telegram.error import TimedOut
from mutagen import File
from PIL import Image
from telegram.constants import MessageLimit
from castpod.spotify import lookup_episode, lookup_podcast

from castpod.utils import (
    modify_logo,
    search_itunes,
    send_error_message,
    streaming_download,
    validate_path,
)
from ..models import (
    Chapter,
    Episode,
    User,
    Podcast,
    UserSubscribePodcast,
    parse_feed,
)
from ..components import PodcastPage
from ..utils import parse_doc
from config import manifest
from ..constants import OTHER_URL, SHORT_DOMAIN
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
    try:
        if is_new_podcast:
            podcast = await podcast.initialize()
            if not podcast:
                raise e
            podcast.save()
            logo = podcast.logo
            logo.thumb_url = thumbnail_small
            logo.save()
        UserSubscribePodcast.get_or_create(user=user, podcast=podcast)
        in_group = (chat_type == "group") or (chat_type == "supergroup")
        kwargs = {"mode": "group"} if in_group else {}
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
    # TODO: use asyncio, and use multiple subscribe feed in sql.
    message = update.message
    user = update.effective_user
    # TODO: add progress
    reply_msg = await message.reply_text("正在解析订阅文件…")
    podcasts_count = 0
    try:
        feeds = await parse_doc(context, user, message.document)
        failed_feeds = []
        for feed in feeds:
            podcast = None
            try:
                podcast, is_new_podcast = Podcast.get_or_create(
                    feed=re.sub(r"https?:\/\/", "", feed["url"]).lower()
                )[0]
                is_new_subscription = UserSubscribePodcast.get_or_create(
                    user=user.id, podcast=podcast
                )[1]
                if is_new_podcast:
                    podcast = await podcast.initialize()
                    podcast.save()
                if is_new_subscription:
                    podcasts_count += 1
            except:
                if podcast:
                    podcast.delete_instance()
                failed_feeds.append(feed["url"])
                continue
        if podcasts_count:
            newline = "\n"
            await message.reply_text(
                f"成功订阅 {podcasts_count} 部播客！"
                if not len(failed_feeds)
                else (
                    f"成功订阅 {podcasts_count} 部播客，部分订阅源解析失败。"
                    f"\n\n订阅失败的源："
                    # use Reduce ?
                    f"\n{newline.join([f'<code>{feed}</code>' for feed in failed_feeds])}"
                )
            )
        else:
            await message.reply_text("订阅失败 :( \n\n请检查订阅文件，以及其中的订阅源是否受损")
        await reply_msg.delete()
    except Exception as e:
        await reply_msg.delete()
        await send_error_message(user, "订阅失败 :( \n\n请检查订阅文件，以及其中的订阅源是否受损")
        raise e


async def download_episode(update: Update, context: CallbackContext):
    message = update.message
    user = update.effective_user
    reply_msg = await message.reply_text("正在获取节目…")
    match = re.search(r"#(.{36})", message.text)
    episode = Episode.get(Episode.id == match[1])
    podcast = episode.from_podcast
    logo = episode.logo
    get_shownotes = episode.shownotes
    shownotes = episode.shownotes[0] if get_shownotes else None
    # todo:not only mp3??
    audio_local_path = validate_path(f"public/audio/{podcast.id}/{episode.id}.mp3")
    logo_path = validate_path(f"public/logo/{podcast.id}/{logo.id}.jpeg")
    timeline = ""
    if shownotes and not shownotes.url:
        shownotes = await shownotes.generate_telegraph()
        shownotes.save()
    markup = InlineKeyboardMarkup.from_row(
        [
            InlineKeyboardButton("我的订阅", switch_inline_query_current_chat=""),
            InlineKeyboardButton(
                "更多单集",
                switch_inline_query_current_chat=f"{podcast.name}#",
            ),
            InlineKeyboardButton(
                "分享", switch_inline_query=f"{podcast.name}>{episode.title}&"
            ),
        ],
    )
    if not episode.url:
        shownotes_text = (
            f"\n\n<a href='{shownotes.url}'>📖 本期附录</a>" if shownotes else ""
        )
        await message.reply_text(
            text=f"<b>{podcast.name}</b>\n{episode.title}{shownotes_text}\n\n{timeline}",
            reply_markup=markup,
        )
        await reply_msg.delete()
        return
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
        if logo.url:
            ua = generate_user_agent(os="linux", device_type="desktop")
            res = httpx.get(
                logo.url,
                follow_redirects=True,
                headers={"User-Agent": ua},
            )
            with open(logo_path, "wb") as f:
                f.write(res.content)
    with Image.open(logo_path) as im:
        # then process image to fit restriction:
        # 1. jpeg format
        im = im.convert("RGB")
        # 2. < 320*320
        size = (320, 320)
        im.thumbnail(size)
        # 3. less than 200 kB !!
        im.save(logo_path, "JPEG", optimize=True, quality=85)
    if shownotes and not episode.chapters:
        has_chapters = shownotes.extract_chapters()
        if not has_chapters:
            audio_metadata = File(audio_local_path)
            audio_tags = audio_metadata.tags
            if audio_tags and hasattr(audio_tags, "getall"):
                chaps = audio_tags.getall("CHAP")
                for chap in chaps:
                    start_time = str(
                        timedelta(milliseconds=int(chap.start_time))
                    ).split(".")[0]
                    title = chap.sub_frames.getall("TIT2")[0].text[0]
                    Chapter.create(
                        from_episode=episode, start_time=start_time, title=title
                    )
    try:
        if episode.chapters:
            timeline = "\n".join(
                [
                    f"<code>{chapter.start_time} </code>{chapter.title}"
                    for chapter in episode.chapters
                ]
            )
        shownotes_text = (
            f"\n\n<a href='{shownotes.url}'>📖 本期附录</a>" if shownotes else ""
        )
        caption = (
            f"<b>{podcast.name}</b>\n{episode.title}{shownotes_text}\n\n{timeline}"
        )
        caption = (
            caption[: MessageLimit.CAPTION_LENGTH - 1] + "…"
            if len(caption) >= MessageLimit.CAPTION_LENGTH
            else caption
        )
        audio_msg = await message.reply_audio(
            # audio=audio_local_path,
            # audio=open(audio_local_path, "rb"),  # TODO:why doesn't work??
            audio=episode.file_id or audio_local_path,
            caption=caption,
            reply_markup=markup,
            title=episode.title,
            performer=podcast.name,
            duration=episode.duration,
            thumb=logo.file_id or open(logo_path, "rb") or episode.logo.url,
            write_timeout=180,
        )
        if not episode.file_id:
            audio = audio_msg.audio
            episode.file_id = audio.file_id
            episode.save()
            if os.path.exists(audio_local_path):
                print("deleting")
                os.remove(audio_local_path)  # delete local file
            if audio.thumb:
                logo.file_id = audio.thumb.file_id
                logo.save()
    except TimedOut:
        await message.reply_text("这期节目的文件体积较大，请稍等…")
    except Exception as e:
        await send_error_message(user, "下载失败，稍后再试试 😞")
        raise e
    finally:
        await reply_msg.delete()
        await message.delete()


async def find_podcast(
    update: Update, context: CallbackContext, keywords: str | None = None
):
    user = update.effective_user
    message = update.message
    if not keywords:
        keywords = message.text
    if (
        message.reply_to_message
        and message.reply_to_message.from_user.username != manifest.bot_id
    ):
        return
    keywords_hans = convert(keywords, "zh-hans")
    keywords_hant = convert(keywords, "zh-hant")
    podcasts = (
        Podcast.select()
        .where(
            Podcast.name.contains(keywords_hans)
            | Podcast.pinyin_abbr.startswith(keywords)
            | Podcast.pinyin_full.startswith(keywords)
            | Podcast.name.contains(keywords_hant)
            | Podcast.host.startswith(keywords_hans)
            | Podcast.host.startswith(keywords_hant)
        )
        .join(UserSubscribePodcast)
        .join(User)
        .where(User.id == user.id)
    )
    count = podcasts.count()
    if count == 0:
        await user.send_message(
            "你还没有订阅相关的播客~",
            reply_markup=InlineKeyboardMarkup.from_button(
                InlineKeyboardButton(
                    f"+ 搜索「{keywords}」",
                    switch_inline_query_current_chat=f"+{keywords}",
                )
            ),
        )
    elif count == 1:
        podcast = podcasts[0]
        is_using_reply_keyboard = context.chat_data.get("is_using_reply_keyboard")
        if is_using_reply_keyboard:
            await message.reply_text(
                f"成功找到播客<b>{podcast.name}</b>", reply_markup=ReplyKeyboardRemove()
            )
            context.chat_data["is_using_reply_keyboard"] = False
        page = PodcastPage(podcast)
        logo = podcast.logo
        # print(logo.file_id or logo.url)
        try:
            msg = await message.reply_photo(
                photo=logo.file_id or logo.url,
                caption=page.text(),
                reply_markup=InlineKeyboardMarkup(page.keyboard()),
            )
            if not logo.file_id:
                logo.file_id = msg.photo[0].file_id
                logo.save()
        except:
            msg = await message.reply_text(
                text=page.text(),
                reply_markup=InlineKeyboardMarkup(page.keyboard()),
            )
    elif count > 1:
        podcasts = podcasts[: MessageLimit.MESSAGE_ENTITIES - 1]
        keyboard = []
        for index, podcast in enumerate(podcasts):
            name = podcast.name
            if index % 2 == 0:
                keyboard.append([name])
            else:
                keyboard[index // 2].append(name)
        await message.reply_text(
            f"在订阅列表中找到 {count} 档相关的播客…",
            reply_markup=ReplyKeyboardMarkup(
                [["[ 关闭 ]"]] + keyboard,
                one_time_keyboard=True,
                input_field_placeholder=f"{message.text} 的检索结果",
                resize_keyboard=True,
            ),
        )
        context.chat_data["is_using_reply_keyboard"] = True


async def show_podcast(update: Update, context: CallbackContext):
    message = update.message
    podcast = Podcast.get(Podcast.name == message.text)
    page = PodcastPage(podcast)
    logo = podcast.logo
    msg = await message.reply_photo(
        photo=logo.file_id or logo.url,
        caption=page.text(),
        reply_markup=InlineKeyboardMarkup(page.keyboard()),
    )
    if not logo.file_id:
        logo.file_id = msg.photo[0].file_id
        logo.save()


async def subscribe_from_url(update: Update, context: CallbackContext):
    user = update.effective_user
    message = update.message
    urls = message.parse_entities("url").values()
    for url in urls:
        reply = await message.reply_text("正在解析链接…")
        await message.reply_chat_action(ChatAction.TYPING)
        if not re.search(OTHER_URL, url):
            continue
        match = re.match(SHORT_DOMAIN, url)
        if match:
            domain = match[1]
        if not url.startswith("http"):
            url = "https://" + url
        ua = generate_user_agent(os="linux", device_type="desktop")
        async with httpx.AsyncClient() as client:
            res = await client.get(
                url, follow_redirects=True, headers={"User-Agent": ua}, timeout=10
            )
        soup = BeautifulSoup(res.text, "html.parser")
        podcast_name = ""
        img = soup.img
        podcast_logo = img.get("src") if img else None
        title_text = soup.title.text
        await reply.delete()
        if domain == "xiaoyuzhoufm.com":
            match = re.search(r"([^\-]+?) \| 小宇宙", title_text)
            if match:
                podcast_name = match[1].lstrip()
        elif domain == "spotify.com":
            match = re.search(r".*?\/(show|episode)\/([0-9a-zA-Z]+)\??", url)
            if match:
                item_type = match[1]
                item_id = match[2]
                if item_type == "podcast":
                    # TODO: 利用返回的数据，直接让用户订阅播客
                    podcast_name, podcast_logo = await lookup_podcast(id=item_id)
                elif item_type == "episode":
                    podcast_name, podcast_logo = await lookup_episode(id=item_id)
                else:
                    podcast_logo = None
            else:
                podcast_logo = None
        elif domain == "google.com" or domain == "pca.st":
            podcast_name = title_text
        elif domain == "apple.com" or domain == "overcast.fm":  # use itunes id
            podcast_itunes_id = re.search(r"(?:id|itunes)([0-9]+)", url)[1]
            results = await search_itunes(itunes_id=podcast_itunes_id)
            podcast_name = results[0].get("collectionName")
            podcast_logo = results[0].get("artworkUrl600")
        elif domain == "castro.fm":
            feed_url = soup.find_all("a")[-1]["href"]
            podcast = await parse_feed(feed_url)
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
                        "+ 订阅此播客", switch_inline_query_current_chat=f"+{podcast_name}"
                    )
                ),
            )
        elif podcast_name:
            await message.reply_text(
                text=f"<b>{podcast_name}</b>",
                reply_markup=InlineKeyboardMarkup.from_button(
                    InlineKeyboardButton(
                        "+ 订阅此播客", switch_inline_query_current_chat=f"+{podcast_name}"
                    )
                ),
            )
        else:
            await send_error_message(user, "解析失败，链接可能已经损坏 😵‍💫")


async def close_reply_keyboard(update: Update, context: CallbackContext):
    await update.message.reply_text("键盘已关闭", reply_markup=ReplyKeyboardRemove())


async def handle_mention_bot(update: Update, context: CallbackContext):
    keywords = re.sub(f"@{manifest.bot_id} +", "", update.message.text)
    await show_podcast(update, context, keywords=keywords)


async def pin_audio(update: Update, context: CallbackContext):
    await update.effective_message.pin()
