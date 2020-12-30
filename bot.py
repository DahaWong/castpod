from config import update_info, webhook_info, webhook_setting
from telegram.ext import Updater
from handlers.register import register
from utils.persistence import persistence
from utils.schedule import set_jobs
 
updater = Updater(**update_info)
dispatcher = updater.dispatcher

# Use this method to logout your bot from telegram api cloud:
#updater.bot.log_out()

# Use these methods before you move your bot to another local server:
#updater.bot.delete_webhook() 
#updater.bot.close()


set_jobs(updater.job_queue)

if not dispatcher.bot_data:
    updater.dispatcher.bot_data.update({"podcasts":{}})

print(dispatcher.bot_data['podcasts'])
print(dispatcher.user_data)

register(updater.dispatcher)

# Webhook:
updater.start_webhook(**webhook_info)
updater.bot.set_webhook(**webhook_setting)

# Polling:
# updater.start_polling()
# updater.idle()
