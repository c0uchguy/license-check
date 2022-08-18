import http.client
import os
import json
import urllib.parse


GUMROAD_TOKEN = os.environ.get('GUMROAD_TOKEN')

async def gumroadRequest(path, method):
  conn = http.client.HTTPSConnection('api.gumroad.com')
  if path[0] != '/':
    path = '/' + path
  conn.request(method, path, headers={
      'Authorization': 'Bearer ' + GUMROAD_TOKEN
  })
  req = conn.getresponse()
  data = req.read()
  return data


async def gumroadGet(path):
  return await gumroadRequest(path, 'GET')


async def gumroadPost(path, data):
  pass


async def getProducts():
  return json.loads((await gumroadGet('/v2/products')).decode('utf8'))
