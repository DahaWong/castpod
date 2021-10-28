from castpod.callbacks import *
from .constants import QUIT_MARK, SPEAKER_MARK, STAR_MARK, DOC_MARK
from telegram.ext import MessageHandler, Filters, InlineQueryHandler, CommandHandler, CallbackQueryHandler, ConversationHandler
from telegram import Chat
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
        CommandHandler('star', command.star),
        CommandHandler('search', command.search, run_async=True),
        CommandHandler('favorite', command.favorite, run_async=True),
        CommandHandler('share', command.share, run_async=True),
        CommandHandler('invite', command.invite),
        CommandHandler('bonus', command.bonus),
        CommandHandler('settings', command.settings),
        CommandHandler('help', command.help_, run_async=True),
        CommandHandler('about', command.about, run_async=True),
        MessageHandler(
            (Filters.via_bot(dispatcher.bot.get_me().id) | Filters.chat_type.private) & Filters.entity("url") & Filters.regex(r'^https?://'), message.subscribe_feed),
        MessageHandler(
            Filters.regex(f'{SPEAKER_MARK} (.+) #([0-9]+)'), message.download_episode, run_async=True),
        MessageHandler(
            Filters.regex(f'^{QUIT_MARK}$'),
            message.exit_reply_keyboard,
            run_async=True
        ),
        MessageHandler(
            Filters.regex(f'^{STAR_MARK}$'),
            command.star,
            run_async=True
        ),
        MessageHandler(
            Filters.regex(f'^{DOC_MARK}$'),
            command.manage,
            run_async=True
        ),
        MessageHandler(
            Filters.regex(r'^探索播客世界$'),
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
        MessageHandler(
            Filters.status_update.pinned_message,
            message.delete_message
        ),
        InlineQueryHandler(inline_query.via_sender, chat_types=[Chat.SENDER]),
        InlineQueryHandler(inline_query.via_private, chat_types=[Chat.PRIVATE]),
        InlineQueryHandler(inline_query.via_group, chat_types=[Chat.GROUP, Chat.SUPERGROUP]),
        InlineQueryHandler(inline_query.via_channel, chat_types=[Chat.CHANNEL]),
        ConversationHandler(
            entry_points=[conversation.request_host_handler],
            states={
                RSS: [conversation.rss_handler, conversation.explain_rss_handler],
                CONFIRM: [conversation.confirm_podcast_handler, conversation.deny_confirm_handler],
                PHOTO: [conversation.photo_handler]
            },
            fallbacks=[conversation.fallback_handler],
            allow_reentry=True,
            conversation_timeout=900
        )
    ])

    for handler in handlers:
        dispatcher.add_handler(handler)
        # dispatcher.add_error_handler(error.handle_error)
