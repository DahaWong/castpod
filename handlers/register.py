from handlers.message import handlers as message
# from handlers.callbackquery import handlers as callbackquery
from handlers.command import handlers as command

handlers = []
handlers.extend(command)
handlers.extend(message)

# handlers = [].extend([message, callbackquery, command,  conversation])

def register(dispatcher):
    for handler in handlers:
      dispatcher.add_handler(handler)