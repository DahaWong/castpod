from telegram.ext import MessageHandler, Filters
import callbacks.message as callback

username_handler = MessageHandler(Filters.text, callback.request_password)
password_handler = MessageHandler(Filters.text, callback.verify_login)

link_handler = MessageHandler(Filters.text, callback.save_link)




