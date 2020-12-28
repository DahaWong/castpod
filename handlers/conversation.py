from telegram.ext import ConversationHandler, CallbackQueryHandler, MessageHandler, Filters
import callbacks.conversation as callbacks

show_feed = MessageHandler(Filters.text, callbacks.show_feed)
like_podcast = CallbackQueryHandler(callbacks.like_podcast, pattern = "^like_podcast")
unlike_podcast = CallbackQueryHandler(callbacks.unlike_podcast, pattern = "^unlike_podcast")
back_to_actions = CallbackQueryHandler(callbacks.back_to_actions, pattern = "^back_to_actions")
unsubscribe_podcast = CallbackQueryHandler(callbacks.unsubscribe_podcast, pattern = "^unsubscribe_podcast")
confirm_unsubscribe = CallbackQueryHandler(callbacks.confirm_unsubscribe, pattern = "^confirm_unsubscribe")
show_episodes = CallbackQueryHandler(callbacks.show_episodes, pattern = "^show_podcast_")

conversation_handler = ConversationHandler(
    entry_points = [show_feed],
    states = {
        callbacks.ACTIONS:[
            like_podcast, 
            unlike_podcast,
            show_episodes, 
            unsubscribe_podcast
        ],
        callbacks.SHOW_EPISODES:[back_to_actions],
        callbacks.UNSUBSCRIBE:[confirm_unsubscribe, back_to_actions],
    },
    fallbacks = [back_to_actions],
    allow_reentry = True
)

handlers=[conversation_handler]