import sqlite3
import datetime
from gumroadRequest import *
import json
from collections import namedtuple
from applicationError import networkError
from guildedRequest import setRole, removeRole

CONFIG = None

def setConfig(c):
  global CONFIG
  CONFIG = c

async def checkLicenseJob():
  con = sqlite3.connect('db.sqlite3')
  (subscriptions, subsByName) = await getAllSubscriptions(con)
  users = await getAllUsers(con, subscriptions)
  since = (datetime.datetime.now() - datetime.timedelta(days=16)).strftime('%Y-%m-%d')
  salesData = json.loads((await gumroadGet('/v2/sales?after={}'.format(since))).decode('utf8'))
  
  if not salesData['success']:
    return networkError('Failed to retrieve sales data from Gumroad', '''Debug:
/sales?after='''+since+'''
SalesData:'''+json.dumps(salesData))
  
  changedUsers = {}
  
  salesData['sales'].reverse()
  
  for sale in salesData['sales']:
    gid = sale['id']
    try: 
      if gid in users:
        user = users[gid]
        if sale['cancelled'] or sale['ended']:
          changedUsers[gid] = user
          changedUsers[gid]['cancelled'] = True
        elif user['subscription']['name'] != sale['variants']['Tier']:
          changedUsers[gid] = user
          changedUsers[gid]['newSubscription'] = subsByName[sale['variants']['Tier']]
        elif gid in changedUsers and 'cancelled' in changedUsers[gid]:
          del changedUsers[gid]['cancelled']
        elif gid in changedUsers and 'newSubscription' in changedUsers[gid]:
          del changedUsers[gid]['newSubscription']
    except:
      pass
  print(changedUsers)
  cancelCount = 0
  updateCount = 0
  for gid in changedUsers:
    if 'cancelled' in changedUsers[gid]:
      cancelCount += 1
      await cancelUser(con, user)
    if 'newSubscription' in changedUsers[gid]:
      updateCount += 1
      await updateSubscription(con, user)
  
  con.commit()
  con.close()
  return (cancelCount, updateCount)
  

async def cancelUser(con, user):
  FakeUser = namedtuple('FakeUser', ('id', 'server'))
  u = FakeUser(id=user['guilded_id'], server=FakeUser(
      id=CONFIG['Guilded_Server_Id'], server=None))
  await removeRole(u, CONFIG['Basic_Member_Role_Id'])
  await removeRole(u, CONFIG['Muted_User_Role_Id'])
  await removeRole(u, user['subscription']['guilded_role_id'])
  con.cursor().execute(
      'UPDATE gumroad_guildeduser SET verified = 0 WHERE id = ?', (user['id'], ))


async def updateSubscription(con, user):
  FakeUser = namedtuple('FakeUser', ('id', 'server'))
  u = FakeUser(id=user['guilded_id'], server=FakeUser(
      id=CONFIG['Guilded_Server_Id'], server=None))

  await removeRole(u, user['subscription']['guilded_role_id'])
  await setRole(u, user['newSubscription']['guilded_role_id'])
  con.cursor().execute(
      'UPDATE gumroad_guildeduser SET subscription_id = ? WHERE id = ?', 
      (user['newSubscription']['id'], user['id'] ))
  
  

async def getAllSubscriptions(con):
  subscriptions = {}
  subsByName = {}
  for row in con.cursor().execute('SELECT id, name, gumroad_id, guilded_role_id '+\
      'FROM gumroad_subscription'):
    sub = {
      'id' : row[0],
      'name': row[1],
      'gumroad_id': row[2],
      'guilded_role_id': row[3]
    }
    subscriptions[row[0]] = sub
    subsByName[row[1]] = sub
  return (subscriptions, subsByName)
  

async def getAllUsers(con, subscriptions):  
  users = {}  
  for row in con.cursor().execute('SELECT id, gumroad_id, guilded_id, gumroad_license, subscription_id '+\
      'FROM gumroad_guildeduser WHERE verified = 1 AND is_banned = 0 AND gumroad_id IS NOT NULL'):
    if type(row[1]) is not str:
      continue
    users[row[1]] = {
      'id': row[0],
      'gumroad_id': row[1],
      'guilded_id': row[2],
      'gumroad_license': row[3],
      'subscription': subscriptions[row[4]]
    }
  return users