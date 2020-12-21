import datetime
BIAS = datetime.timedelta(hours=8)

def is_today(date):
  date += BIAS
  today = datetime.date.today() + BIAS
  return date == today

def get_today():
  return datetime.date.today() + BIAS