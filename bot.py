from telegram.ext import Updater
from config import update_info, webhook_info, webhook_setting, Mongo
from castpod.handlers import register_handlers
# from castpod.stats import register as register_stats
from mongoengine import connect
import datetime

updater = Updater(**update_info)
dispatcher = updater.dispatcher

# Use this method to logout your bot from telegram api cloud:
# updater.bot.log_out()

# Use these methods before you move your bot to another local server:
# updater.bot.delete_webhook()
# updater.bot.close()

## 部署建议：#webhook 和 #polling 两种方法择其一，建议从 polling 直接上手，无需更多配置。注释掉含 #webhook 的语句、取消注释含 polling 的语句即可。

# Webhook:
updater.start_webhook(**webhook_info)  # Webhook
updater.bot.set_webhook(**webhook_setting) # Webhook
updater.idle()     # polling

connection = dispatcher.run_async(
    connect,
    db=Mongo.db
    # username=Mongo.user, # for auth
    # password=Mongo.pwd # for auth
    # host=Mongo.remote_host # for remote test
)


def make_job(i):
    def job(context):
        podcasts = context.bot_data['podcasts'].values()
        if not podcasts:
            return
        for podcast in podcasts:
            if i in podcast.job_group:
                podcast.update()
    return job


for i in range(48):
    time = datetime.time(hour=i//4, minute=i*30 % 60)
    dispatcher.job_queue.run_daily(
        make_job(i), time, name=f'update_podcast_group_{i}')

register_handlers(dispatcher)
# register_stats(dispatcher)

if connection.result():
    print('MongoDB Connected!')
else:
    raise Exception('MongoDB Connection Failed.')

# Polling:
# updater.start_polling() # polling
# updater.idle()     # polling
