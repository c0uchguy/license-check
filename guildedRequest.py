import os
import http.client
import json
import urllib.parse

GUILDED_BOT_TOKEN = os.environ.get('GUILDED_BOT_TOKEN') or 'gapi_LkQwY++qeh3LUcv2EUUQWL3a+S2MSzJiT3DT0q61jhBuE3OI3mJlCXe7BuFoXwwBxM/eHDJ8/Jo82T74YYrgmw=='
CONFIG = None
def setConfig2(c):
  global CONFIG
  CONFIG = c

async def guildedRequest(path, method, params=None):
  conn = http.client.HTTPSConnection('www.guilded.gg')
  if path[0] != '/':
    path = '/' + path
  if params is not None:
    conn.request(method, '/api/v1' + path,  body=params, headers={
      'Authorization': 'Bearer ' + GUILDED_BOT_TOKEN,
      'Content-Type': 'application/json'
    })
  else:  
    conn.request(method, '/api/v1' + path, headers={
      'Authorization': 'Bearer ' + GUILDED_BOT_TOKEN  
    })
  req = conn.getresponse()
  data = req.read()
  return data


async def guildedGet(path):
  return json.loads( (await guildedRequest(path, 'GET')).decode('utf8') )


async def guildedPut(path):
  response = (await guildedRequest(path, 'PUT')).decode('utf8')
  if len(response) == 0:
    return {}
  return json.loads( (response) )


async def guildedDelete(path):
  response = (await guildedRequest(path, 'DELETE')).decode('utf8')
  if len(response) == 0:
    return {}
  return json.loads( (response) )


async def guildedPost(path, params):
  response = await guildedRequest(path, 'POST', params)
  return json.loads( response.decode('utf8') )

async def guildedWebhook(path, body):
  conn = http.client.HTTPSConnection('media.guilded.gg')
  if path[0] != '/':
    path = '/' + path
  if body is not None:    
    conn.request('POST', path, body=body,  headers={
      'Authorization': 'Bearer ' + GUILDED_BOT_TOKEN,
      'Content-Type': 'multipart/form-data; boundary=wL36Yn8afVp8Ag7AmP8qZ0SA4n1v9T'
    })
    req = conn.getresponse()
    data = req.read()
    return json.loads( (data).decode('utf8') )
  

async def notifyModerators(message):
  await guildedPost('/channels/' + CONFIG['Notification_Channel'] + '/messages', json.dumps({
      'content': message,
  }))
  
  

async def muteUser(user):
  await setRole(user, CONFIG['Muted_User_Role_Id'])
  return await removeRole(user, CONFIG['Basic_Member_Role_Id'])


async def unmuteUser(user):
  await removeRole(user, CONFIG['Muted_User_Role_Id'])
  return await setRole(user, CONFIG['Basic_Member_Role_Id'])


async def setRole(message, roleId):
  serverId = 0
  authorId = 0
  if (hasattr(message, 'author')):
    authorId = message.author.id
    serverId = message.id
  else:
    authorId = message.id
    serverId = message.server.id
  return await guildedPut('/servers/' + str(serverId) + '/members/' +
                          str(authorId) + '/roles/' + roleId)


async def removeRole(message, roleId):
  serverId = 0
  authorId = 0
  if (hasattr(message, 'author')):
    authorId = message.author.id
    serverId = message.id
  else:
    authorId = message.id
    serverId = message.server.id
  return await guildedDelete('/servers/' + str(serverId) + '/members/' +
                             str(authorId) + '/roles/' + roleId)
