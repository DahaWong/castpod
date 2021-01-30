from castpod.utils import search_podcast
from telegram import InlineQueryResultArticle, InputTextMessageContent, InlineKeyboardButton, InlineKeyboardMarkup
import re
import uuid
from manifest import manifest

def handle_inline_query(update, context):
    run_async = context.dispatcher.run_async
    query = update.inline_query
    query_text = query.query
    podcasts_match = re.match('^p$', query_text)
    episodes_match = re.match('^e$', query_text)
    results, kwargs = [], {"auto_pagination": True, "cache_time": 10}
    if not query_text:
        results, kwargs = run_async(welcome, context)
    elif podcasts_match:
        results = run_async(search_saved, 'podcasts', context)
    elif episodes_match:
        results = run_async(search_saved, 'episodes', context)
    else:
        podcasts = context.bot_data['podcasts']
        podcast = podcasts.get(query_text)
        if podcast:
            results = run_async(show_episodes, podcast)
            kwargs.update({"cache_time": 600})
        else:
            results = run_async(search_podcast, query_text)

    run_async(query.answer, results, **kwargs)


def welcome(context):
    if not context.user_data.get('user'):
        results = []
        kwargs = {
            "switch_pm_text": "登录",
            "switch_pm_parameter": "login",
            "cache_time": 0
        }
    else:
        results = show_subscription(context)
        kwargs = {}
    return results, kwargs


def show_episodes(podcast):
    episodes = podcast.episodes
    buttons = [
        InlineKeyboardButton("订阅列表", switch_inline_query_current_chat=""),
        InlineKeyboardButton(
            "单集列表", switch_inline_query_current_chat=f"{podcast.name}")
    ]
    results = [InlineQueryResultArticle(
        id=index,
        title=episode.title,
        input_message_content=InputTextMessageContent((
            f"[🎙️]({podcast.logo_url}) *{podcast.name}* #{len(episodes) - index}"
        )),
        reply_markup=InlineKeyboardMarkup.from_row(buttons),
        description=f"{episode.duration or podcast.name}\n{episode.subtitle}",
        thumb_url=podcast.logo_url,
        thumb_width=60,
        thumb_height=60
    ) for index, episode in enumerate(episodes)]
    return results


def search_podcast(keyword):
    searched_results = search(keyword)
    listed_results = []
    if not searched_results:
        listed_results = [
            InlineQueryResultArticle(
                id='0',
                title="没有找到相关的播客呢 :(",
                description="换个关键词试试",
                input_message_content=InputTextMessageContent("🔍️"),
                reply_markup=InlineKeyboardMarkup.from_button(
                    InlineKeyboardButton(
                        '返回搜索', switch_inline_query_current_chat=keyword)
                )
            )
        ]
    else:
        for result in searched_results:
            name = re.sub(r"[_*`]", ' ', result['collectionName'])
            host = re.sub(r"[_*`]", ' ', result['artistName'])
            feed = result.get('feedUrl') or '（此播客没有提供订阅源）'
            thumbnail_small = result.get('artworkUrl60')

            # 如果不在 机器人主页，则：
            # [InlineKeyboardButton('前  往  B O T', url = f"https://t.me/{manifest.bot_id}")],

            result_item = InlineQueryResultArticle(
                id=result['collectionId'],
                title=name,
                input_message_content=InputTextMessageContent(
                    feed, parse_mode=None),
                description=host,
                thumb_url=thumbnail_small or None,
                thumb_height=60,
                thumb_width=60
            )
            listed_results.append(result_item)
    return listed_results


def show_subscription(context):
    results = []
    subscription = context.user_data['user'].subscription
    if not subscription:
        results = [InlineQueryResultArticle(
            id=0,
            title='订阅列表还是空的 🥡',
            description=f'试着在 `@{manifest.bot_id} ` 后面输入关键词，寻找喜欢的播客吧',
            input_message_content=InputTextMessageContent('🔍️'),
            reply_markup=InlineKeyboardMarkup.from_button(
                InlineKeyboardButton(
                    '搜索播客', switch_inline_query_current_chat='')
            )
        )]
    else:
        results = [InlineQueryResultArticle(
            id=index,
            title=feed.podcast.name,
            input_message_content=InputTextMessageContent(
                feed.podcast.name, parse_mode=None),
            description=feed.podcast.host or feed.podcast.name,
            thumb_url=feed.podcast.logo_url,
            thumb_width=60,
            thumb_height=60
        ) for index, feed in enumerate(subscription.values())]
    return results


def search_saved(saved_type, context):
    items = context.user_data[f'saved_{saved_type}'].items()
    if not items:
        return [InlineQueryResultArticle(
            id=0,
            title="收藏夹还是空的",
            input_message_content=InputTextMessageContent('/manage 管理订阅的播客'),
            description='🥡',
        )]
    return [InlineQueryResultArticle(
        id=uuid.uuid4(),
        title=item_name,
        input_message_content=InputTextMessageContent(
            item.name, parse_mode=None),
        description=item.host or item_name,
        thumb_url=item.logo_url,
        thumb_height=60,
        thumb_width=60
    ) for item_name, item in items]
