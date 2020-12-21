from config import update_info
from telegram.ext import Updater
from handlers.register import register
 
updater = Updater(**update_info)
register(updater.dispatcher)

updater.start_polling()
updater.idle()