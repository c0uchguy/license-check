import random
import string
import re

timeFormat = re.compile(r'([0-9]+)([dhmw])')


def inviteGenerator():
  parts = []
  for i in range(4):
    parts.append(''.join(random.choice(
        string.ascii_uppercase + string.digits) for _ in range(8)))
  return '-'.join(parts)


def timeFromParams(body):
  time = 0
  body.reverse()
  for timeStr in body:
    if len(timeStr) > 0:
      try:
        matches = re.match(timeFormat, timeStr)
        multiplier = 1
        mString = matches.group(2)
        if mString == 'h':
          multiplier = 60
        elif mString == 'd':
          multiplier = 1440
        elif mString == 'w':
          multiplier = 10080
        time += int(matches.group(1)) * multiplier
      except:
        break
  body.reverse()
  return time