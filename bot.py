from telegram.ext import Updater
from telegram import BotCommandScopeAllPrivateChats, BotCommandScopeAllGroupChats, BotCommandScopeAllChatAdministrators, BotCommandScopeChat
from castpod.handlers import register_handlers
from castpod.models import Podcast
import config
# from castpod.stats import register as register_stats
from mongoengine import connect
import datetime
updater = Updater(**config.update_info)
dispatcher = updater.dispatcher

# Use this method to logout your bot from telegram api:
# updater.bot.log_out()

# updater.bot.delete_webhook()
# updater.bot.close()

# Webhook:
updater.start_webhook(**config.webhook_info)  # Webhook

connection = dispatcher.run_async(
    connect,
    db=config.Mongo.db
    # username=Mongo.user, # for auth
    # password=Mongo.pwd # for auth
    # host=Mongo.remote_host # for remote test
)

register_handlers(dispatcher)
# register_stats(dispatcher) # stats


def make_job(i):
    def job(context):
        podcasts = Podcast.objects(job_group=i)
        # context.bot.send_message(dev, f'`{podcasts}`')
        for podcast in podcasts:
            podcast.check_update(context)
    return job


for i in range(48):
    interval = 15
    time = datetime.time(hour=i // (60 // interval), minute=i * interval % 60)
    dispatcher.job_queue.run_daily(
        make_job(i), time, name=f'update_podcast_group_{i}')

if connection.result():
    print('MongoDB Connected!')
else:
    raise Exception('MongoDB Connection Failed.')

# set commands
updater.bot.set_my_commands(
    commands=config.private_commands, scope=BotCommandScopeAllPrivateChats())
updater.bot.set_my_commands(
    commands=config.group_commands, scope=BotCommandScopeAllChatAdministrators())
updater.bot.set_my_commands(
    commands=config.dev_commands, scope=BotCommandScopeChat(config.dev))

# Polling:
# updater.start_polling()  # polling

updater.idle()
