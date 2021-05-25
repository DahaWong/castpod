from mongoengine.queryset.visitor import Q
from mongoengine.errors import DoesNotExist
from castpod.utils import search_itunes
from telegram import InlineQueryResultArticle, InputTextMessageContent, InlineKeyboardButton, InlineKeyboardMarkup,InlineQueryResultPhoto
import re
from config import manifest
from castpod.models import User, Podcast
import datetime

def handle_inline_query(update, context):
    run_async = context.dispatcher.run_async
    query = update.inline_query
    query_text = query.query
    results, kwargs = [], {"auto_pagination": True, "cache_time": 20}
    user = User.validate_user(update.effective_user)
    if not query_text:
        results = run_async(show_subscription, user).result()
    elif re.match('^p$', query_text):
        results = run_async(show_fav_podcasts, user).result()
    # elif re.match('^e$', query_text):
    #     results = run_async(show_fav_episodes, user).result()
    else:
        try:
            podcast = Podcast.objects.get(
                Q(name=query_text) & Q(subscribers=user))
            results = run_async(show_episodes, podcast).result()
            kwargs.update({"cache_time": 40})
        except:
            results = run_async(search_podcast, query_text).result()

    run_async(query.answer, list(results), **kwargs)

def show_subscription(user):
    podcasts = Podcast.objects(subscribers__in=[user])
    if not podcasts:
        yield InlineQueryResultArticle(
            id=0,
            title='订阅列表还是空的',
            description=f'试着在 @{manifest.bot_id} 后面输入关键词，寻找喜欢的播客吧',
            input_message_content=InputTextMessageContent('🔍️'),
            reply_markup=InlineKeyboardMarkup.from_button(
                InlineKeyboardButton(
                    '搜索播客', switch_inline_query_current_chat='')
            )
        )
    else:
        # podcasts = sorted(podcasts, key=lambda x: x.podcast.updated_time, reverse=True)
        for index, podcast in enumerate(podcasts):
            fav_flag = ''
            if user in podcast.fav_subscribers:
                fav_flag = '  ⭐️'
            yield InlineQueryResultPhoto(
                id=str(index),
                title=str(podcast.name) + fav_flag,
                description=podcast.host or podcast.name,
                photo_url=podcast.logo,
                input_message_content=InputTextMessageContent(podcast.name),
                thumb_url=podcast.logo,
                caption=podcast.name,
                thumb_width=80,
                thumb_height=80
            )

def show_fav_podcasts(user):
    favs = Podcast.objects(fav_subscribers__in = [user])
    if not favs:
        yield InlineQueryResultArticle(
            id=0,
            title="播客收藏夹是空的",
            input_message_content=InputTextMessageContent('/manage'),
            description='🥡',
        )
    else:
        for fav in favs:
            podcast = fav.podcast
            yield InlineQueryResultArticle(
                id=podcast.id,
                title=podcast.name + "  ⭐️",
                input_message_content=InputTextMessageContent(
                    podcast.name, parse_mode=None),
                description=podcast.host or podcast.name,
                thumb_url=podcast.logo,
                thumb_height=80,
                thumb_width=80
            )

def show_fav_episodes(user):
    pass

def show_episodes(podcast):
    # episodes = sorted(podcast.episodes, key=lambda x: x.published_time, reverse=True)
    buttons = [
        InlineKeyboardButton("订阅列表", switch_inline_query_current_chat=""),
        InlineKeyboardButton(
            "单集列表", switch_inline_query_current_chat=f"{podcast.name}")
    ]
    for index, episode in enumerate(podcast.episodes):
        yield InlineQueryResultArticle(
            id=index,
            title=episode.title,
            input_message_content=InputTextMessageContent((
                f"[🎙️]({podcast.logo}) *{podcast.name}* #{len(podcast.episodes) - index}"
            )),
            reply_markup=InlineKeyboardMarkup.from_row(buttons),
            description=f"{datetime.timedelta(seconds=episode.duration) or podcast.name}\n{episode.subtitle}",
            thumb_url=episode.logo,
            thumb_width=80,
            thumb_height=80
        )

def search_podcast(keyword):
    searched_results = search_itunes(keyword)
    if not searched_results:
        yield InlineQueryResultArticle(
            id='0',
            title="没有找到相关的播客呢 :(",
            description="换个关键词试试",
            input_message_content=InputTextMessageContent("🔍️"),
            reply_markup=InlineKeyboardMarkup.from_button(
                        InlineKeyboardButton(
                            '返回搜索', switch_inline_query_current_chat=keyword)
            )
        )
    else:
        for result in searched_results:
            name = re.sub(r"[_*`]", ' ', result['collectionName'])
            host = re.sub(r"[_*`]", ' ', result['artistName'])
            feed = result.get('feedUrl') or '（此播客没有提供订阅源）'
            thumbnail_small = result.get('artworkUrl60')

            # 如果不在 机器人主页，则：
            # [InlineKeyboardButton('前  往  B O T', url = f"https://t.me/{manifest.bot_id}")],

            yield InlineQueryResultArticle(
                id=result['collectionId'],
                title=name,
                input_message_content=InputTextMessageContent(
                    feed, parse_mode=None),
                description=host,
                thumb_url=thumbnail_small or None,
                thumb_height=60,
                thumb_width=60
            )
