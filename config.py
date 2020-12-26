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
  parse_mode="MARKDOWN"
)

# Test(with proxy)
update_info = {
  'token': bot_token,
  'use_context': True,
  'request_kwargs': {
    'proxy_url':proxy
  },
  'persistence': persistence,
  'defaults': defaults
  # 'base_url': bot_api
}


# Build
# update_info = {
#   'token': bot_token,
#   'use_context': True,
#   'persistence': persistence
# }
