from telegram import (
    BotCommandScopeAllChatAdministrators,
    BotCommandScopeAllPrivateChats,
    BotCommandScopeChat,
)
from telegram.ext import Application, ApplicationBuilder

import config
from castpod.handlers import register_handlers
from castpod.models import db_init


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
    .write_timeout(120)
    .build()
)

register_handlers(application)
db_init()

# Webhook:
application.run_webhook(
    listen="127.0.0.1",
    port=8443,
    url_path=config.bot_token,
    webhook_url=f"http://127.0.0.1:8443/{config.bot_token}",
    max_connections=80,
    drop_pending_updates=True,
)

# Polling:
# application.run_polling()
