import configparser

from telegram.ext import Defaults
from telegram.constants import ParseMode

config = configparser.ConfigParser()
config.read("config.ini")  # Read the configuration file on your machine.


# Bot
bot_token = config["BOT"]["TOKEN"]
bot_api = config["BOT"]["API"]
# podcast_vault = config["BOT"]["PODCAST_VAULT"]
defaults = Defaults(parse_mode=ParseMode.HTML, disable_web_page_preview=True)

# Dev
dev = config["DEV"]["USER_ID"]
dev_name = config["DEV"]["USER_NAME"]
dev_email = config["DEV"]["EMAIL"]

# Spotify
client_id = config["SPOTIFY"]["CLIENT_ID"]
client_secret = config["SPOTIFY"]["CLIENT_SECRET"]

# Path
EXT_PATH = config["SQL"]["EXT_PATH"]

# commands
private_commands = [
    ("search", "搜寻新播客"),
    ("help", "Castpod 说明书"),
    ("about", "其他信息"),
]

dev_commands = [
    ("search", "搜寻新播客"),
    ("help", "Castpod 说明书"),
    ("about", "关于"),
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
    bot_id = "cspdbot"
    author = "Daha"
    author_id = "dahawong"
    author_url = "https://daha.me/"
    version = "0.1.8"
    discription = ""
    repo = "https://github.com/dahawong/castpod"
