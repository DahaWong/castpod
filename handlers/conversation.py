from telegram.ext import ConversationHandler, CallbackQueryHandler
from handlers.command import start_handler, quit_handler
from handlers.callbackquery import login_confirm_handler, quit_cancel_handler, quit_confirm_handler, like_link_handler, delete_link_handler, unlike_link_handler
from handlers.message import password_handler, username_handler, link_handler

USERNAME, PASSWORD, VERIFY = range(3)
CONFIRM_QUIT, = range(1)

login_handler = ConversationHandler(
    entry_points=[start_handler],
    states={
        USERNAME: [login_confirm_handler],
        PASSWORD: [username_handler],
        VERIFY: [password_handler]
    },
    fallbacks=[start_handler],
    allow_reentry=True
)

quit_handler = ConversationHandler(
    entry_points=[quit_handler],
    states = { 
        CONFIRM_QUIT: [quit_cancel_handler, quit_confirm_handler]
    },
    fallbacks= [quit_handler],
    allow_reentry=True
)