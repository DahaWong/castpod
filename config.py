import configparser
from utils.persistence import bot_persistence

config = configparser.ConfigParser()
config.read('config.ini')


# Bot
bot_token_test = config['BOT']['TOKEN_TEST']
bot_token = config['BOT']['TOKEN']
proxy = config['BOT']['PROXY']


# Oauth
oauth_consumer_id = config['OAUTH']['CONSUMER_ID']
oauth_consumer_secret = config['OAUTH']['CONSUMER_SECRET']

# Encrypt
encrypt_key = config['ENCRYPT']['KEY']

#Database:
mongo_user = config['MONGODB']['USER']
mongo_pwd = config['MONGODB']['PWD']
mongo_ip = config['MONGODB']['IP']
mongodb_uri = f"mongodb://{mongo_user}:{mongo_pwd}@{mongo_ip}/instasaver"

# Test(with proxy)
# update_info = {
#   'token': bot_token_test,
#   'use_context': True,
#   'request_kwargs': {
#     'proxy_url':proxy
#   },
#   'persistence': bot_persistence
# }


# Build
update_info = {
  'token': bot_token,
  'use_context': True,
  'persistence': bot_persistence
}
