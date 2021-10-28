from telegram.ext import Updater
from telegram import BotCommandScopeAllPrivateChats, BotCommandScopeAllGroupChats, BotCommandScopeAllChatAdministrators, BotCommandScopeChat
from castpod.handlers import register_handlers
from castpod.models import Podcast
import config
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


def update_podcasts(context):
    for podcast in Podcast.objects:
        message = podcast.check_update(context)
        if message:
            for subscriber in podcast.subscribers:
                message.copy(subscriber.user_id)


dispatcher.job_queue.run_repeating(
    update_podcasts, 1200)  # run every 1200 s (20 min)

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
