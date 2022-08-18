from .models import Configuration
from inspect import iscoroutinefunction
from asgiref.sync import sync_to_async
CONFIG = None

def config():
  global CONFIG
  if CONFIG is None:
    CONFIG = {}
    for setting in Configuration.objects.all():
      CONFIG[setting.name] = setting.value
  return CONFIG


def getConfig(prop):
  return config()[prop]

async def asyncGetConfig(prop):
  conf = (await sync_to_async(config)())
  return conf[prop]
