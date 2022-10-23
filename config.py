import configparser

from telegram.ext import Defaults
from telegram.constants import ParseMode

config = configparser.ConfigParser()
config.read("config.ini")  # Read the configuration file on your machine.


# Bot
bot_token = config["BOT"]["TOKEN"]
bot_api = config["BOT"]["API"]
# podcast_vault = config["BOT"]["PODCAST_VAULT"]
defaults = Defaults(parse_mode=ParseMode.HTML, disable_notification=True)

# Dev
dev = config["DEV"]["USER_ID"]
dev_name = config["DEV"]["USER_NAME"]
dev_email = config["DEV"]["EMAIL"]

# commands
private_commands = [
    ("search", "搜索播客"),
    ("manage", "我的订阅"),
    ("help", "使用指南"),
    ("about", "关于我们"),
]

dev_commands = [
    ("search", "搜索播客"),
    ("manage", "我的订阅"),
    ("help", "使用指南"),
    ("about", "关于我们"),
    ("stat", "数据汇总"),
]

group_commands = [
    ("wander", "随机漫步"),
    ("update", "更新节目"),
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
    author_id = "dahawong"
    author_url = "https://office.daha.me/"
    version = "0.1.8"
    discription = ""
    repo = "https://github.com/dahawong/castpod"
