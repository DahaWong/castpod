# from ptbstats import set_application, register_stats, SimpleStats
# from telegram.ext import Filters


# def register(application):
#     set_application(application)

#     register_stats(
#         SimpleStats(
#             'text',
#             lambda u: bool(u.message and (filters.TEXT & ~ filters.COMMAND)(u))
#         )
#     )
#     register_stats(
#         SimpleStats(
#             'ilq', lambda u: bool(u.inline_query and u.inline_query.query))
#     )
