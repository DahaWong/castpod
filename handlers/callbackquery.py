from telegram.ext import CallbackQueryHandler
import callbacks.callbackquery as callback

login_confirm_handler = CallbackQueryHandler(callback.request_username, pattern='^login_confirm$')

delete_link_handler = CallbackQueryHandler(callback.delete_link, pattern='^delete_')
like_link_handler = CallbackQueryHandler(callback.like_link, pattern='^like_')
unlike_link_handler = CallbackQueryHandler(callback.unlike_link, pattern='^unlike_')

quit_cancel_handler = CallbackQueryHandler(callback.cancel_quit, pattern='^cancel_quit$')
quit_confirm_handler = CallbackQueryHandler(callback.confirm_quit, pattern='^confirm_quit$')
