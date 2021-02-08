# Castpod

> v0.1.0

一个 [Telegram 机器人](https://core.telegram.org/bots/api)。点击[链接](https://t.me/castpodbot)开始使用吧！

## 基本

点击 `开始` 以启动机器人，所有的交互在对话框之间完成。

### 指令
点击文本输入框一旁的 `/` 可以唤出主要指令。全部指令如下：
- `/manage`：管理已订阅的播客
- `/help`：帮助与指南

- `/about`：关于本机器人与作者
- `/setting`：偏好设置
- `/export`：导出订阅文件
- `/logout`：注销账号并清空所有数据

### 订阅与下载
...

## 部署

如果您有一点技术背景，可以考虑自己部署这个机器人，这样可以减少我们服务器的压力，同时带给您更流畅的使用体验。

### 安装依赖

使用 `python -m pip install -r requirements.txt` 安装所有依赖。

### 配置

在根目录新建一个配置文件 `config.ini` ，填写所需的变量。
```config.ini
[BOT]
TOKEN_TEST = 机器人测试token，可无视
TOKEN = 机器人token，找 @BotFather 领取
PROXY = 本地测试代理 http 链接，避开网路封锁
API = 自部署的 telegram-bot-api 地址，如不使用请在根目录 `config.py` 的 `update_info` 中删除使用此变量的其他语句
PODCAST_VAULT = Telegram「播客广场」的频道ID，即@后面的内容。这与本机器人的播客分发模式有关，可能不太好理解。

[WEBHOOK]
PORT = Webhook 端口数字，不使用请无视

[DEV]
USER_ID = 开发者（您）的 Telegram ID，整数。

[MONGODB]
USER = 用户名，可选
PWD = 密码，可选
DB_NAME = 数据库的名字
REMOTE_HOST = 服务器IP，用于本地测试（但并不安全），可选
```
### 数据库
安装 MongoDB，运行 `mongod`

### Polling v.s Webhook
[Webhook](https://github.com/python-telegram-bot/python-telegram-bot/wiki/Webhooks) 和 Polling 两种方法择其一，**建议从 Polling 直接上手**，无需更多配置。

在 `bot.py` 文件中注释掉含 #webhook 的**两条语句**、取消注释含 polling 的**两条语句**即可。

### 部署 Telegram Bot API
得益于近日 Bot API 已经开源，现在我们可以自己部署一个 Bot API 服务器。这是因为播客音频往往比较大，超出了 Telegram 对 Bot 的上传限制，所以我们需要自己部署它。

关于如何部署，请参考 Telegram 的[官方部署指南](https://tdlib.github.io/telegram-bot-api/build.html)。

### 运行
- 直接运行： `python bot.py`
- 推荐使用进程管理器运行，如 [PM2](https://pm2.keymetrics.io/docs/usage/pm2-doc-single-page/) ：`pm2 start bot.py --name castpod --interpreter python --kill-timeout 3000`

## 支持本项目

### 文档支持
帮助我们填写[资料库](https://github.com/dahawong/castpod/wiki)。文档填写进度详见[文档书写](https://github.com/DahaWong/castpod/projects/5)

### 技术支持
> 我们熟悉 Telegram 的生态，但对 Python 特性与数据库相关处理并不熟练，代码亟待优化。欢迎提供建议/学习资源/PR

更多信息请参见[开发行程](https://github.com/DahaWong/castpod/projects/2)、[项目漏洞](https://github.com/DahaWong/castpod/projects/3)

### 经济支持
<a href="https://www.buymeacoffee.com/daha"><img src="https://img.buymeacoffee.com/button-api/?text=Buy me a Cherry  : )&emoji=🍒&slug=daha&button_colour=FF5F5F&font_colour=ffffff&font_family=Poppins&outline_colour=000000&coffee_colour=FFDD00"></a>
