from handlers import command, conversation
from handlers.message import link_handler
from handlers.callbackquery import unlike_link_handler,like_link_handler,delete_link_handler
from handlers.command import about_handler, today_handler

handlers = [conversation.login_handler, conversation.quit_handler, about_handler, today_handler]
handlers.append(link_handler)
handlers += [unlike_link_handler,like_link_handler,delete_link_handler]

def register(dispatcher):
  for handler in handlers:
    dispatcher.add_handler(handler)