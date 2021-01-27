from config import update_info, webhook_info, webhook_setting
from telegram.ext import Updater
from handlers.register import register

updater = Updater(**update_info)
dispatcher = updater.dispatcher

# Use this method to logout your bot from telegram api cloud:
# updater.bot.log_out()

# Use these methods before you move your bot to another local server:
# updater.bot.delete_webhook() 
# updater.bot.close()

# Polling:
updater.start_polling()
updater.idle()

# Webhook:
# updater.start_webhook(**webhook_info)
# updater.bot.set_webhook(**webhook_setting)

if not dispatcher.bot_data:
    updater.dispatcher.bot_data.update({"podcasts":{}})

for podcast in dispatcher.bot_data['podcasts'].values():
    podcast.set_jobqueue(updater.job_queue)

register(updater.dispatcher)

