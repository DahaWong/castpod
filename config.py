from telegram.ext import PicklePersistence
import configparser
from telegram.ext import Defaults


config = configparser.ConfigParser()
config.read('config.ini')  # Read the configuration file on your machine.


# Bot
bot_token_test = config['BOT']['TOKEN_TEST']
bot_token = config['BOT']['TOKEN']
proxy = config['BOT']['PROXY']
bot_api = config['BOT']['API']
podcast_vault = config['BOT']['PODCAST_VAULT']
defaults = Defaults(
    parse_mode="MARKDOWN",
    disable_notification=True
)

# Dev
dev_user_id = config['DEV']['USER_ID']

# Server
webhook_port = int(config['WEBHOOK']['PORT'])

# MongoDB


class Mongo(object):
    mongo = config['MONGODB']
    db = mongo['DB_NAME']
    user = mongo['USER']
    pwd = mongo['PWD']
    remote_host = mongo['REMOTE_HOST']  # test


webhook_info = {
    "listen": '127.0.0.1',
    "port": webhook_port,
    "url_path": bot_token
}

webhook_setting = {
    "url": f'https://webhook.daha.me/{bot_token}',
    "max_connections": 1000,
    "drop_pending_updates": True,
    "allowed_updates": []
}

# Test
persistence = PicklePersistence(filename='persistence')
update_info_test = {
   'token': bot_token_test,
   'use_context': True,
   'request_kwargs': {
      'proxy_url':proxy  # Use proxy especially when telegram is banned in your country
    },
   'defaults': defaults,
   'persistence': persistence
 }

# Build
persistence = PicklePersistence(filename='persistence')
update_info = {
    'token': bot_token,
    'use_context': True,
    'persistence': persistence,
    'base_url': bot_api,
    'defaults': defaults
}


# Manifest
class manifest:
    name = "Castpod"
    bot_id = "castpodbot"
    author = "Daha"
    author_id = 'dahawong'
    author_url = "https://office.daha.me/"
    version = "0.1.0"
    discription = ""
    repo = "https://github.com/dahawong/castpod"
