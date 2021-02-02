import datetime
from config import update_info, webhook_info, webhook_setting
from telegram.ext import Updater
from castpod.handlers import register_handlers

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
    dispatcher.bot_data.update(
        {"podcasts":{}}
    )

def make_job(i):
    def job(context):
        podcasts = context.bot_data['podcasts'].values()
        if not podcasts: return 
        for podcast in podcasts:
            if i in podcast.job_group:
                podcast.update()
    return job

for i in range(48):
    time = datetime.time(hour=i//4, minute=i*30%60)
    dispatcher.job_queue.run_daily(make_job(i), time, name=f'update_podcast_group_{i}')

register_handlers(updater.dispatcher)

