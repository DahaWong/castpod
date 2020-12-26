from config import update_info
from telegram.ext import Updater
from handlers.register import register
from utils.persistence import persistence
from utils.schedule import set_jobs
 
updater = Updater(**update_info)
dispatcher = updater.dispatcher

# Use this method to logout your bot from telegram api cloud:
# updater.bot.log_out()

# Use these methods before you move your bot to another local server:
# updater.bot.delete_webhook() 
# updater.bot.close()

set_jobs(updater.job_queue)

if not dispatcher.bot_data:
    print('init')
    updater.dispatcher.bot_data.update({"users": {}, "podcasts":{}})

register(updater.dispatcher)

updater.start_polling()
updater.idle()