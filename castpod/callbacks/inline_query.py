from ..utils import search_itunes
from telegram import (
    InlineQueryResultArticle,
    InlineQueryResultCachedAudio,
    InputTextMessageContent,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Update,
)
import re
from ..models import (
    Episode,
    User,
    Podcast,
    UserSubscribePodcast,
    filter_subscription,
    select_episodes_by_keywords,
    get_subscription,
)
import datetime
from ..constants import SHORT_DOMAIN
from peewee import DoesNotExist
from uuid import uuid4
from zhconv import convert
from config import manifest


def subscription_generator(podcasts, subscription_empty=False):
    if podcasts.count() == 0:
        title = "你还没有订阅过播客" if subscription_empty else "你还没有订阅相关的播客"
        yield InlineQueryResultArticle(
            id=uuid4(),
            title=title,
            description="输入「+」进入搜索模式，然后便可开始寻找新播客",
            input_message_content=InputTextMessageContent("🔍"),
            reply_markup=InlineKeyboardMarkup.from_button(
                InlineKeyboardButton("返回订阅列表", switch_inline_query_current_chat="")
            ),
        )
    else:
        for podcast in podcasts:
            thumb_url = podcast.logo.url if podcast.logo else None
            yield InlineQueryResultArticle(
                id=podcast.id,
                title=podcast.name,
                input_message_content=InputTextMessageContent(
                    podcast.name, parse_mode=None
                ),
                description=f"{podcast.host}",
                thumb_url=thumb_url,
                thumb_height=60,
                thumb_width=60,
            )


async def search_subscription(update: Update, context):
    inline_query = update.inline_query
    keywords = inline_query.query
    podcasts = None
    user_id = update.effective_user.id
    subscription_empty = False
    if not keywords:
        podcasts = get_subscription(user_id)
        subscription_empty = True
    else:
        podcasts = filter_subscription(user_id, keywords)
    results = subscription_generator(podcasts, subscription_empty=subscription_empty)
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
                description="也可以发送从其他平台导出的 OPML 订阅文件，批量地添加播客",
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


async def search_all_episode(update: Update, context):
    inline_query = update.inline_query
    keywords = inline_query.query[1:].replace("[", "").replace("]", "")
    if not keywords:
        await inline_query.answer(
            [
                InlineQueryResultArticle(
                    id=uuid4(),
                    title="请输入关键词来搜索单集…",
                    description=f"{manifest.name} 会在已订阅的所有播客里寻找相关单集",
                    input_message_content=InputTextMessageContent("/episodes"),
                )
            ],
            auto_pagination=True,
        )
        return
    subscribed_podcasts = (
        Podcast.select()
        .join(UserSubscribePodcast)
        .where(UserSubscribePodcast.user == update.effective_user.id)
    )
    episodes = select_episodes_by_keywords(Episode.select(), keywords).where(
        Episode.from_podcast.in_(subscribed_podcasts)
    )

    if episodes.count():
        try:
            await inline_query.answer(
                [
                    InlineQueryResultArticle(
                        id=episode.id,
                        title=episode.title,
                        description=f"{episode.published_time.date()}·《{episode.from_podcast.name}》\n{episode.subtitle}",
                        input_message_content=InputTextMessageContent(
                            f"<b>{episode.from_podcast.name}</b>\n{episode.title}\n\n<code>#{episode.id}</code>"
                        ),
                        reply_markup=InlineKeyboardMarkup.from_row(
                            [
                                InlineKeyboardButton(
                                    "订阅列表", switch_inline_query_current_chat=""
                                ),
                                InlineKeyboardButton(
                                    "更多单集",
                                    switch_inline_query_current_chat=f"{episode.from_podcast.name}#",
                                ),
                            ]
                        ),
                        thumb_url=episode.logo.thumb_url or episode.logo.url,
                        thumb_width=60,
                        thumb_height=60,
                    )
                    for episode in episodes
                ],
                auto_pagination=True,
                cache_time=1800,
            )
        except:
            pass
    else:
        await inline_query.answer(
            [
                InlineQueryResultArticle(
                    id=uuid4(),
                    title="没有找到相关的节目",
                    input_message_content=InputTextMessageContent("/search"),
                    description=f"换个关键词试试！",
                )
            ],
            auto_pagination=True,
        )


async def search_episode(update: Update, context):
    inline_query = update.inline_query
    match = re.search(r"(.*?)#(.*)", inline_query.query)
    name, index = match[1], match[2]
    results = []
    try:
        podcast = Podcast.get(Podcast.name == name)
    except:
        results = [
            InlineQueryResultArticle(
                id=uuid4(),
                title="该播客不存在~",
                description="换个播客名字试试",
                input_message_content=InputTextMessageContent("🔍"),
                reply_markup=InlineKeyboardMarkup.from_button(
                    InlineKeyboardButton("返回搜索栏", switch_inline_query_current_chat="")
                ),
            )
        ]
        return
    results = show_episodes(podcast, index)
    await inline_query.answer(
        list(results),
        auto_pagination=True,
        # cache_time=10,
        cache_time=1800,
    )


async def search_episodes_by_date(update, context):
    inline_query = update.inline_query
    keywords = inline_query.query[1:]
    if not keywords:
        await inline_query.answer(
            [
                InlineQueryResultArticle(
                    id=uuid4(),
                    title="请输入日期（如：年月日）或者相对时间（如：昨天）",
                    description=f"{manifest.name} 会根据日期列出当天发布的所有单集",
                    input_message_content=InputTextMessageContent("/episodes"),
                )
            ],
            auto_pagination=True,
        )
    else:
        episodes = None
        if keywords in ["今天", "today", "t"]:
            episodes = Episode.select().where(
                Episode.published_time == datetime.datetime.today()
            )
        elif keywords in ["昨天", "yesterday", "y"]:
            episodes = Episode.select().where(
                Episode.published_time
                == datetime.datetime.today() - datetime.timedelta(days=1)
            )
        elif keywords in ["前天", "b"]:
            episodes = Episode.select().where(
                Episode.published_time
                == datetime.datetime.today() - datetime.timedelta(days=2)
            )
        # elif keywords in ["本月", "m"]:
        #     episodes = Episode.select().where(
        #         Episode.published_time
        #         == datetime.datetime.today()
        #     )
        if episodes.count():
            try:
                await inline_query.answer(
                    [
                        InlineQueryResultArticle(
                            id=episode.id,
                            title=episode.title,
                            description=f"{episode.published_time.date()}·《{episode.from_podcast.name}》\n{episode.subtitle}",
                            input_message_content=InputTextMessageContent(
                                f"<b>{episode.from_podcast.name}</b>\n{episode.title}\n\n<code>#{episode.id}</code>"
                            ),
                            reply_markup=InlineKeyboardMarkup.from_row(
                                [
                                    InlineKeyboardButton(
                                        "订阅列表", switch_inline_query_current_chat=""
                                    ),
                                    InlineKeyboardButton(
                                        "更多单集",
                                        switch_inline_query_current_chat=f"{episode.from_podcast.name}#",
                                    ),
                                ]
                            ),
                            thumb_url=episode.logo.thumb_url or episode.logo.url,
                            thumb_width=60,
                            thumb_height=60,
                        )
                        for episode in episodes
                    ],
                    auto_pagination=True,
                    cache_time=1800,
                )
            except:
                pass
        else:
            await inline_query.answer(
                [
                    InlineQueryResultArticle(
                        id=uuid4(),
                        title="没有找到相关的节目",
                        input_message_content=InputTextMessageContent("/search"),
                        description=f"换个关键词试试！",
                    )
                ],
                auto_pagination=True,
            )


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
            episodes = episodes.order_by(-Episode.published_time)
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
                    if episodes.count() == 1
                    else f"请输入 1 ～ {len(episodes)} 之间的数字",
                )
                return
        else:
            episodes = select_episodes_by_keywords(episodes, index)
            if not episodes.count():
                yield InlineQueryResultArticle(
                    id=uuid4(),
                    title="没有找到相关的节目",
                    input_message_content=InputTextMessageContent(podcast.name),
                    description=f"换个关键词试试",
                )
    else:
        episodes = episodes.order_by(-Episode.published_time)
    for episode in episodes:
        yield InlineQueryResultArticle(
            id=uuid4(),
            title=episode.title,
            input_message_content=InputTextMessageContent(
                f"<b>{podcast.name}</b>\n{episode.title}\n\n<code>#{episode.id}</code>"
            ),
            reply_markup=InlineKeyboardMarkup.from_row(buttons),
            description=f"{episode.published_time.date()} · {datetime.timedelta(seconds=episode.duration) or episode.from_podcast.name}\n{episode.subtitle}",
            thumb_url=episode.logo.url,
            thumb_width=60,
            thumb_height=60,
        )


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
    match = re.match(r"(.+?)\>(.+?)&(.*)", inline_query.query)
    if match:
        podcast_name, keywords, text_to_send = match[1], match[2], match[3]
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
            hint = f"点选下方单集发送音频，并留言「{text_to_send}」"
        else:
            caption = f"<b>{episode.title}</b>\n{podcast_name} · <i>{episode.published_time.strftime('%Y/%m/%d')}</i>\n\n"
            hint = "点选下方单集发送音频；继续输入文字可附上留言"
        await inline_query.answer(
            [
                InlineQueryResultCachedAudio(
                    id=episode.id,
                    audio_file_id=episode.file_id,
                    caption=caption,
                    reply_markup=InlineKeyboardMarkup.from_button(
                        InlineKeyboardButton(
                            f"在 {manifest.name} 中打开",
                            url=f"https://t.me/{manifest.bot_id}?start=episode_{episode.id}",
                        )
                    ),
                )
            ],
            cache_time=0,
            switch_pm_text=hint,
            switch_pm_parameter="back",
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
                            url=f"https://t.me/{manifest.bot_id}?start=podcast_{podcast.id}",
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
            description=f"点击此处向朋友推荐 Castpod",
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
