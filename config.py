import configparser
from utils.persistence import persistence
from telegram.ext import Defaults

config = configparser.ConfigParser()
config.read('config.ini')


# Bot
bot_token_test = config['BOT']['TOKEN_TEST']
bot_token = config['BOT']['TOKEN']
proxy = config['BOT']['PROXY']
bot_api = config['BOT']['API']
podcast_vault = config['BOT']['PODCAST_VAULT']
defaults = Defaults(
    parse_mode="MARKDOWN", 
    disable_notification=True, 
    run_async=True
)

# Dev
dev_user_id = config['DEV']['USER_ID']

# Server
webhook_port = int(config['WEBHOOK']['PORT'])


# Build
update_info = {
   'token': bot_token,
   'use_context': True,
   'persistence': persistence,
   'base_url': bot_api,
   'defaults': defaults,
   'workers': 1024
 }

webhook_info = {
    "listen": '127.0.0.1', 
    "port": webhook_port, 
    "url_path": bot_token
}

webhook_setting = {
    "url": f'http://webhook.daha.me/{bot_token}',
    "max_connections": 1000,
    "drop_pending_updates": True
    # "allowed_updates": []
}

# Test
# update_info = {
#    'token': bot_token,
#    'use_context': True,
#    'request_kwargs': {
#       'proxy_url':proxy
#     },
#    'persistence': persistence,
#    'base_url': bot_api,
#    'defaults': defaults
#  }
