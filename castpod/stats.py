# from ptbstats import set_dispatcher, register_stats, SimpleStats
# from telegram.ext import Filters


# def register(dispatcher):
#     set_dispatcher(dispatcher)

#     register_stats(
#         SimpleStats(
#             'text',
#             lambda u: bool(u.message and (Filters.text & ~ Filters.command)(u))
#         )
#     )
#     register_stats(
#         SimpleStats(
#             'ilq', lambda u: bool(u.inline_query and u.inline_query.query))
#     )
