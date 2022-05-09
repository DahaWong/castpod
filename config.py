import configparser
from telegram.ext import Defaults


config = configparser.ConfigParser()
config.read('config.ini')  # Read the configuration file on your machine.


# Bot
bot_token = config['BOT']['TOKEN_TEST']
proxy = config['BOT']['PROXY']
bot_api = config['BOT']['API']
podcast_vault = config['BOT']['PODCAST_VAULT']
defaults = Defaults(
    parse_mode="MARKDOWN",
    disable_notification=True
)

# Dev
dev = config['DEV']['USER_ID']
dev_name = config['DEV']['USER_NAME']
dev_email = config['DEV']['EMAIL']

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
    "listen": '136.244.105.159',
    "port": 8848,
    "url_path": bot_token,
    "webhook_url": f'http://127.0.0.1:8848/{bot_token}',
    "max_connections": 1000,
    "drop_pending_updates": True,
}

# commands
private_commands = [
    ('search', '搜索播客'),
    ('manage', '订阅列表'),
    ('favorite', '单集收藏'),
    ('help', '使用指南'),
    ('about', '关于我们')
]

dev_commands = [
    ('search', '搜索播客'),
    ('manage', '订阅列表'),
    ('favorite', '单集收藏'),
    ('help', '使用指南'),
    ('about', '关于我们'),
    ('stat', '数据汇总')
]

group_commands = [
    ('wander', '随机漫步'),
    ('update', '更新节目'),
]


# Build
# persistence = PicklePersistence(filename='persistence')
# update_info = {
#     'token': bot_token,
#     'use_context': True,
#     'persistence': persistence,
#     'base_url': bot_api,
#     'defaults': defaults,
#     'workers': 6
# }

# Manifest


class manifest:
    name = "Castpod"
    bot_id = "testdahabot"
    author = "Daha"
    author_id = 'dahawong'
    author_url = "https://office.daha.me/"
    version = "0.1.8"
    discription = ""
    repo = "https://github.com/dahawong/castpod"
