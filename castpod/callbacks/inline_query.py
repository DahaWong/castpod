from ..utils import search_itunes, send_error_message
from telegram import (
    InlineQueryResultArticle,
    InlineQueryResultCachedAudio,
    InputTextMessageContent,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Update,
)
from telegram.error import TimedOut
import re
from ..models import (
    Episode,
    User,
    Podcast,
    UserSubscribePodcast,
    filter_subscription,
    show_subscription,
)
import datetime
from ..constants import SHORT_DOMAIN
from peewee import DoesNotExist
from uuid import uuid4
from zhconv import convert
from config import manifest


def subscription_generator(podcasts):
    if podcasts.count() == 0:
        yield InlineQueryResultArticle(
            id=uuid4(),
            title="你还没有订阅过播客",
            description="输入「+」进入搜索模式，接着便可以寻找并添加想听的播客",
            input_message_content=InputTextMessageContent("🔍"),
            reply_markup=InlineKeyboardMarkup.from_button(
                InlineKeyboardButton("返回订阅列表", switch_inline_query_current_chat="")
            ),
        )
    else:
        print([p for p in podcasts])
        for podcast in podcasts:
            print(podcast)
            yield InlineQueryResultArticle(
                id=podcast.id,
                title=podcast.name,
                input_message_content=InputTextMessageContent(
                    podcast.name, parse_mode=None
                ),
                description=f"{podcast.host}",
                thumb_url=podcast.logo.url,
                thumb_height=60,
                thumb_width=60,
            )


async def search_subscription(update: Update, context):
    inline_query = update.inline_query
    keywords = inline_query.query
    podcasts = None
    user_id = update.effective_user.id
    if not keywords:
        podcasts = show_subscription(user_id)
    else:
        podcasts = filter_subscription(user_id, keywords)
    results = subscription_generator(podcasts)
    await inline_query.answer(list(results), auto_pagination=True, cache_time=10)


async def search_new_podcast(update: Update, context):
    inline_query = update.inline_query
    keywords = inline_query.query[1:]
    results = []
    if not keywords:
        results = [
            InlineQueryResultArticle(
                id=uuid4(),
                title="🔎 继续输入关键词，寻找并添加新播客",
                description="你也可以发送从其他平台导出的 OPML 订阅文件，批量地添加播客",
                input_message_content=InputTextMessageContent("🔍"),
                reply_markup=InlineKeyboardMarkup.from_button(
                    InlineKeyboardButton("返回搜索栏", switch_inline_query_current_chat="+")
                ),
            )
        ]
    else:
        searched_results = await search_itunes(keyword=keywords)
        if not searched_results:
            results = [
                InlineQueryResultArticle(
                    id=uuid4(),
                    title="没有找到相关的播客 :(",
                    description="换个关键词试试",
                    input_message_content=InputTextMessageContent("🔍"),
                    reply_markup=InlineKeyboardMarkup.from_button(
                        InlineKeyboardButton(
                            "返回搜索栏", switch_inline_query_current_chat=f"+{keywords}"
                        )
                    ),
                )
            ]
        else:
            for search_result in searched_results:
                name = re.sub(r"[_*`]", " ", search_result["collectionName"])
                host = re.sub(r"[_*`]", " ", search_result["artistName"])
                feed = search_result.get("feedUrl")
                if not feed:
                    continue
                feed_short = re.match(SHORT_DOMAIN, feed.lower())[1]
                thumbtail_large = search_result.get("artworkUrl600")
                thumbnail_small = search_result.get("artworkUrl60")
                episode_count = f'共 {search_result["trackCount"]} 期'

                # 如果不在 机器人主页，则：
                # [InlineKeyboardButton('前往 bot', url = f"https://t.me/{manifest.bot_id}")],
                new_result = InlineQueryResultArticle(
                    id=search_result["collectionId"],
                    title=name,
                    input_message_content=InputTextMessageContent(
                        f"{feed}\n{thumbtail_large}\n{thumbnail_small}", parse_mode=None
                    ),
                    description=(
                        f"{host if len(host)<=31 else host[:31]+'...'}\n{episode_count} · {feed_short}"
                    ),
                    thumb_url=thumbnail_small or None,
                    thumb_height=60,
                    thumb_width=60,
                )
                results.append(new_result)
    await inline_query.answer(results, auto_pagination=True, cache_time=10)


async def search_episode(update: Update, context):
    inline_query = update.inline_query
    match = re.search(r"(.*?)#(.*)", inline_query.query)
    name, index = match[1], match[2]
    podcast = Podcast.get(Podcast.name == name)
    results = show_episodes(podcast, index)
    await inline_query.answer(
        list(results),
        auto_pagination=True,
        cache_time=10,
        # cache_time=3600
    )


async def via_sender(update: Update, context):
    user = update.effective_user
    inline_query = update.inline_query
    keywords = inline_query.query
    subscribed_podcasts = (
        Podcast.select().join(UserSubscribePodcast).join(User).where(User.id == user.id)
    )
    if not keywords:
        if not subscribed_podcasts:
            results = [
                InlineQueryResultArticle(
                    id=uuid4(),
                    title="🔎 继续输入关键词，搜索并订阅新播客",
                    description="订阅后，这里将显示你的订阅列表。",
                    input_message_content=InputTextMessageContent("🔍"),
                    reply_markup=InlineKeyboardMarkup.from_button(
                        InlineKeyboardButton(
                            "返回搜索栏", switch_inline_query_current_chat=""
                        )
                    ),
                )
            ]
            await inline_query.answer(results, auto_pagination=True, cache_time=5)
            return
        results = []
        for podcast in subscribed_podcasts:
            new_result = InlineQueryResultArticle(
                id=uuid4(),
                title=podcast.name,
                input_message_content=InputTextMessageContent(
                    podcast.name, parse_mode=None
                ),
                description=f"{podcast.host}",
                thumb_url=podcast.logo.url,
                thumb_height=60,
                thumb_width=60,
            )
            # new_result = InlineQueryResultPhoto(
            #     id=uuid4(),
            #     photo_url=podcast.logo.url,
            #     thumb_url=podcast.logo.thumb_url or podcast.logo.url,
            #     photo_width=80,
            #     photo_height=80,
            #     title=podcast.name,
            #     description=podcast.website or podcast.email or None,
            #     input_message_content=InputTextMessageContent(
            #         podcast.name, parse_mode=None
            #     ),
            # )
            results.append(new_result)
        await inline_query.answer(
            results,
            auto_pagination=True,
            cache_time=1200,
        )
    else:
        match = re.search(r"(.*?)#(.*)$", keywords)
        try:
            if match:
                name, index = match[1], match[2]
                podcast = Podcast.get(Podcast.name == name)
                results = show_episodes(podcast, index)
                await inline_query.answer(
                    list(results),
                    auto_pagination=True,
                    cache_time=3600,
                )
            else:
                results = await search_podcast(keywords)
                await inline_query.answer(
                    results,
                    auto_pagination=True,
                    cache_time=500,
                )
        except DoesNotExist:
            await send_error_message(user, "🫧 该播客不在订阅列表中")
        except TimedOut:
            # TODO
            await send_error_message(user, "该播客节目较多，暂时无法收听")


async def via_private(update, context):
    inline_query = update.inline_query
    keywords = inline_query.query
    results = None
    if not keywords:
        results = get_invitation()
    else:
        results = share_podcast(keywords)
    await inline_query.answer(list(results), auto_pagination=True, cache_time=150)


async def share_episode(update: Update, context):
    inline_query = update.inline_query
    match = re.match(r"(.+?)\>(.+?)&(.+)*", inline_query.query)
    if match:
        podcast_name, keywords, text_to_send = match[1:4]
    try:
        episode: Episode = (
            Episode.select()
            .where(Episode.title == keywords)
            .join(Podcast)
            .where(Podcast.name == podcast_name)
            .join(UserSubscribePodcast)
            .join(User)
            .where(User.id == update.effective_user.id)
            .get()
        )
        caption = ""
        if text_to_send:  # user has typed some word
            caption = text_to_send
            hint = f"点选单集发送音频，并留言「{text_to_send}」"
        else:
            caption = f"<b>{episode.title}</b>\n{podcast_name} · <i>{episode.published_time.strftime('%Y/%m/%d')}</i>\n\n"
            hint = "点选下方单集发送音频，若继续输入文字可附上留言"
        await inline_query.answer(
            [
                InlineQueryResultCachedAudio(
                    id=episode.id,
                    audio_file_id=episode.file_id,
                    caption=caption,
                    reply_markup=InlineKeyboardMarkup.from_button(
                        InlineKeyboardButton(
                            f"在 {manifest.name} 中打开",
                            url=f"https://t.me/{manifest.bot_id}?start=episode-{episode.id}",
                        )
                    ),
                )
            ],
            cache_time=0,
            switch_pm_text=hint,
            switch_pm_parameter="sharing_{episode.id}",
        )
    except DoesNotExist:
        await inline_query.answer(
            [
                InlineQueryResultArticle(
                    id=uuid4(),
                    title="该单集不存在",
                    description="换个关键词试试",  # TODO：用关键词检索所有播客
                    input_message_content=InputTextMessageContent(
                        f"<b>{podcast_name}</b><a href='{episode.from_podcast.logo.url}'> · </a>\n{episode.from_podcast.host}",
                        disable_web_page_preview=False,
                    ),
                    reply_markup=InlineKeyboardMarkup.from_button(
                        InlineKeyboardButton(
                            f"订阅",
                            url=f"https://t.me/{manifest.bot_id}?start=podcast-{podcast.id}",
                        )
                    ),
                )
            ]
        )


async def via_group(update, context):
    await via_private(update, context)


async def via_channel(update, context):
    await via_private(update, context)


async def search_podcast(keywords):
    searched_results = await search_itunes(keyword=keywords)
    if not searched_results:
        return [
            InlineQueryResultArticle(
                id=uuid4(),
                title="没有找到相关的播客 :(",
                description="换个关键词试试",
                input_message_content=InputTextMessageContent("🔍"),
                reply_markup=InlineKeyboardMarkup.from_button(
                    InlineKeyboardButton(
                        "返回搜索栏", switch_inline_query_current_chat=f"+{keywords}"
                    )
                ),
            )
        ]
    else:
        results = []
        for result in searched_results:
            name = re.sub(r"[_*`]", " ", result["collectionName"])
            host = re.sub(r"[_*`]", " ", result["artistName"])
            feed = result.get("feedUrl")
            if not feed:
                continue
            feed_short = re.match(SHORT_DOMAIN, feed.lower())[1]
            thumbtail_large = result.get("artworkUrl600")
            thumbnail_small = result.get("artworkUrl60")
            episode_count = f'共 {result["trackCount"]} 期'

            # 如果不在 机器人主页，则：
            # [InlineKeyboardButton('前往 bot', url = f"https://t.me/{manifest.bot_id}")],
            results.append(
                InlineQueryResultArticle(
                    id=result["collectionId"],
                    title=name,
                    input_message_content=InputTextMessageContent(
                        f"{feed}\n{thumbtail_large}\n{thumbnail_small}", parse_mode=None
                    ),
                    description=(
                        f"{host if len(host)<=31 else host[:31]+'...'}\n{episode_count} · {feed_short}"
                    ),
                    thumb_url=thumbnail_small or None,
                    thumb_height=60,
                    thumb_width=60,
                )
            )
        return results


def show_episodes(podcast, index):
    buttons = [
        InlineKeyboardButton("订阅列表", switch_inline_query_current_chat=""),
        InlineKeyboardButton(
            "更多单集", switch_inline_query_current_chat=f"{podcast.name}#"
        ),
    ]
    episodes = podcast.episodes
    if index:
        if re.match(r"^-?[0-9]{1,4}$", index):
            index = int(index)
            if abs(index) <= len(episodes):
                if index >= 0:
                    index = -index
                    episodes = episodes[
                        max(index - 3, -len(episodes)) : min(index + 2, -1)
                    ]
                else:
                    index = abs(index + 1)
                    episodes = episodes[
                        max(index - 3, 0) : min(index + 2, len(episodes))
                    ]
            else:
                yield InlineQueryResultArticle(
                    id=uuid4(),
                    title="超出检索范围",
                    input_message_content=InputTextMessageContent(":("),
                    description="当前播客只有一期节目"
                    if podcast.episodes.count() == 1
                    else f"请输入 1 ～ {len(episodes)} 之间的数字",
                )
                return
        else:
            episodes = (
                Episode.select().where(
                    (Episode.from_podcast == podcast.id)
                    & (
                        Episode.title.contains(index)
                        | Episode.title.contains(convert(index, "zh-hant"))
                    )
                )
                # .join(Shownotes)
                # .where(Shownotes.content.contains(index))
            )
            if not episodes:
                yield InlineQueryResultArticle(
                    id=uuid4(),
                    title="🫧 没有找到相关的节目",
                    input_message_content=InputTextMessageContent(podcast.name),
                    description=f"换个关键词试试",
                )
    for i, episode in enumerate(episodes):
        yield InlineQueryResultArticle(
            id=uuid4(),
            title=episode.title,
            input_message_content=InputTextMessageContent(
                f"<b>{podcast.name}</b> <i>#{len(episodes)-i}</i>\n{episode.title}"
            ),
            reply_markup=InlineKeyboardMarkup.from_row(buttons),
            description=f"{datetime.timedelta(seconds=episode.duration) or podcast.name}\n{episode.subtitle}",
            thumb_url=episode.logo.url,
            thumb_width=60,
            thumb_height=60,
        )


def get_invitation():
    # TODO: send photo instead
    yield InlineQueryResultArticle(
        id=uuid4(),
        title="点击发送 Castpod 邀请函",
        description="或继续输入关键词，以分享播客",
        input_message_content=InputTextMessageContent(
            f"来 <a href='https://t.me/{manifest.bot_id}'>Castpod</a>，一起听播客！",
            disable_web_page_preview=False,
        ),
        reply_markup=InlineKeyboardMarkup.from_button(
            InlineKeyboardButton(
                "🏖️ 开启播客之旅", url=f"https://t.me/{manifest.bot_id}?start"
            )
        ),
    )


def share_podcast(keywords):
    try:
        podcast = Podcast.get(Podcast.name == keywords)
        logo = podcast.logo
        yield InlineQueryResultArticle(
            id=uuid4(),
            thumb_url=logo.thumb_url or logo.url,
            thumb_height=60,
            thumb_width=60,
            title=podcast.name,
            description="点击分享此播客",
            reply_markup=InlineKeyboardMarkup.from_button(
                InlineKeyboardButton(
                    "订阅",
                    url=f"https://t.me/{manifest.bot_id}?start=podcast_{podcast.id}",
                )
            ),
            input_message_content=InputTextMessageContent(
                f"<b>{podcast.name}</b><a href='{podcast.logo.url}'> · </a>\n{podcast.host}",
                disable_web_page_preview=False,
            ),
        )
    except DoesNotExist:
        yield InlineQueryResultArticle(
            id=uuid4(),
            title="没有找到相关的播客，换个关键词试试 :)",
            description=f"点击此处直接向朋友推荐 Castpod",
            input_message_content=InputTextMessageContent(
                f"来 <a href='https://t.me/{manifest.bot_id}'>Castpod</a>，一起听播客！",
                disable_web_page_preview=False,
            ),
            reply_markup=InlineKeyboardMarkup.from_button(
                InlineKeyboardButton(
                    "🏖️ 开启播客之旅", url=f"https://t.me/{manifest.bot_id}?start"
                )
            ),
        )
