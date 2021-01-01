from telegram.ext import MessageHandler, Filters
import callbacks.message as callback

subscription_handler = MessageHandler(
    Filters.document.mime_type('text/xml') | Filters.document.mime_type('application/octet-stream'), 
    callback.save_subscription
)

feed_handler = MessageHandler(Filters.entity("url") & Filters.regex(r'^https?://'), callback.subscribe_feed)
exit_handler = MessageHandler(Filters.regex(r'^退出'), callback.exit_reply_keyboard)

handlers=[feed_handler, subscription_handler, exit_handler]