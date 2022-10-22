from telegram import (
    BotCommandScopeAllChatAdministrators,
    BotCommandScopeAllPrivateChats,
    BotCommandScopeChat,
)
from telegram.ext import Application, ApplicationBuilder

import config
from castpod.handlers import register_handlers
from castpod.models_new import User, db_init


async def post_init(application: Application) -> None:
    bot = application.bot
    # Use this method to logout your bot from official telegram api:
    # await bot.log_out()
    # await bot.delete_webhook()
    # await bot.close()
    # Init commands
    await bot.set_my_commands(
        commands=config.private_commands, scope=BotCommandScopeAllPrivateChats()
    )
    await bot.set_my_commands(
        commands=config.group_commands, scope=BotCommandScopeAllChatAdministrators()
    )
    await bot.set_my_commands(
        commands=config.dev_commands, scope=BotCommandScopeChat(config.dev)
    )


application = (
    ApplicationBuilder()
    .token(config.bot_token)
    .defaults(config.defaults)
    .base_url(config.bot_api)
    .post_init(post_init)
    .build()
)

register_handlers(application)
db_init()

# Webhook:
application.run_webhook(**config.webhook_info)

# Polling:
# application.run_polling()
