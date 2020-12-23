from telegram.ext import MessageHandler, Filters
import callbacks.message as callback

subscription_handler = MessageHandler(
    Filters.document.mime_type('text/xml') | Filters.document.mime_type('application/octet-stream'), 
    callback.save_subscription
)

feed_handler = MessageHandler(
    Filters.entity("url") | Filters.entity("text_link"), 
    callback.save_feed
)

handlers=[feed_handler, subscription_handler]