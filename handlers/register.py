from handlers.message import handlers as message
from handlers.callback_query import handlers as callback_query
from handlers.inline_query import handlers as inline_query
from handlers.command import handlers as command
from callbacks.error import handle_error 

handlers = []
handlers.extend(command)
handlers.extend(message)
handlers.extend(inline_query)
handlers.extend(callback_query)

def register(dispatcher):
    for handler in handlers:
      dispatcher.add_handler(handler)

    dispatcher.add_error_handler(handle_error, run_async = True)