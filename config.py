import configparser
from utils.persistence import persistence

config = configparser.ConfigParser()
config.read('config.ini')


# Bot
bot_token_test = config['BOT']['TOKEN_TEST']
bot_token = config['BOT']['TOKEN']
proxy = config['BOT']['PROXY']
bot_api = config['BOT']['API']

# Test(with proxy)
update_info = {
  'token': bot_token,
  'use_context': True,
  'request_kwargs': {
    'proxy_url':proxy
  },
  'persistence': persistence,
  # 'base_url': bot_api
}


# Build
# update_info = {
#   'token': bot_token,
#   'use_context': True,
#   'persistence': persistence
# }
