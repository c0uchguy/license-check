import http.client
import os
import json
import urllib.parse
from .models import Subscription
from asgiref.sync import sync_to_async

#https://api.gumroad.com/v2/products
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

async def getPurchaseFromLicense(license):
  permalinks = await sync_to_async(getPermalinks)()
  for permalink in permalinks:
    conn = http.client.HTTPSConnection('api.gumroad.com')
    params = urllib.parse.urlencode({
      'product_permalink': permalink,
      'license_key': license
    })
    print(params)
    conn.request('POST', '/v2/licenses/verify', params, headers={
      'Authorization': 'Bearer ' + GUMROAD_TOKEN
    })
    req = conn.getresponse()
    data = json.loads( (req.read()).decode('utf8') )
    print(data)
    if data['success']:
      return data
  return None

def getPermalinks():
  return [val for val in Subscription.objects\
    .order_by('gumroad_permalink')\
    .values_list('gumroad_permalink', flat=True).distinct()]