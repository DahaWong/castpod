from castpod.callbacks import *
from telegram.ext import MessageHandler, Filters, InlineQueryHandler, CommandHandler, CallbackQueryHandler, ConversationHandler
import inspect

RSS, CONFIRM, PHOTO = range(3)


def register_handlers(dispatcher):
    handlers = []

    for value in vars(callback_query).values():
        if inspect.isfunction(value):
            callback_query_handler = CallbackQueryHandler(
                value, pattern=f"^{value.__name__}")
            handlers.append(callback_query_handler)

    handlers.extend([
        CommandHandler('start', command.start,
                       filters=Filters.chat_type.private, pass_args=True),
        CommandHandler('manage', command.manage),
        CommandHandler('help', command.help_, run_async=True),
        MessageHandler(
            (Filters.via_bot(dispatcher.bot.get_me().id) | Filters.chat_type.private) & Filters.entity("url") & Filters.regex(r'^https?://'), message.subscribe_feed),
        MessageHandler(
            Filters.regex(r'🎙️ (.+) #([0-9]+)'), message.download_episode, run_async=True),
        MessageHandler(
            Filters.regex(r'^╳$'),
            message.exit_reply_keyboard,
            run_async=True
        ),
        MessageHandler(
            Filters.regex(r'^您尚未开始订阅，点击出发寻找播客$'),
            message.search_podcast,
            run_async=True
        ),
        MessageHandler(
            Filters.chat_type.private &
            (Filters.document.mime_type('text/xml') |
             Filters.document.file_extension("opml") |
             Filters.document.file_extension("opm")),
            message.save_subscription,
            run_async=True
        ),
        MessageHandler(
            (
                Filters.reply |
                Filters.via_bot(dispatcher.bot.get_me().id) |
                Filters.chat_type.private
            ) &
            Filters.text, message.show_podcast
        ),
        MessageHandler(Filters.chat(username="podcast_vault_chat")
                       & Filters.audio, message.handle_audio),
        InlineQueryHandler(inline_query.handle_inline_query),
        ConversationHandler(
            entry_points=[conversation.request_host_handler],
            states={
                RSS: conversation.parse_rss_handler,
                PHOTO: conversation.verify_info_handler
            },
            fallbacks=[conversation.fallback_handler],
            allow_reentry=True,
            conversation_timeout=900
        )
    ])

    for handler in handlers:
        dispatcher.add_handler(handler)
        # dispatcher.add_error_handler(error.handle_error)
