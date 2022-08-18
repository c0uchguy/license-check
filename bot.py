import asyncio
import datetime
import guilded
import json
import os
import re
import sqlite3
import traceback
import urllib.parse
import uuid
from apiRequest import apiGet
from collections import namedtuple
from gumroadLicenseCheck import checkLicenseJob, setConfig
from guildedRequest import *
from helpers import inviteGenerator, timeFromParams
from profanity import setupProfanity, checkForProfanity, handleProfanity
from scheduledJobs import getPendingJobs, createScheduledJob, deleteScheduledJob
from twitterRequest import sendRecentAttachments, setTwitterToken, getUserByUsername

client = guilded.Client()

GUILDED_BOT_TOKEN = os.environ.get('GUILDED_BOT_TOKEN')
SERVER_URL = os.environ.get('SERVER_URL') or '127.0.0.1:8000'
licenseFormat = re.compile(r'[a-zA-Z0-9]{8}-[a-zA-Z0-9]{8}-[a-zA-Z0-9]{8}-[a-zA-Z0-9]{8}')


CONFIG = None
loop = None

#===============================================================================
# Event Handlers
#===============================================================================

@client.event
async def on_ready():
  global  loop, CONFIG
  CONFIG = json.loads(await apiGet('/api/config/'))
  setConfig(CONFIG)
  setConfig2(CONFIG)  
  setupProfanity(CONFIG, json.loads(await apiGet('/api/profanity/')))
  setTwitterToken(CONFIG['Twitter_Token'])
  loop = asyncio.get_event_loop()
  loop.create_task(periodic())


@client.event
async def on_message(message):
  global CONFIG
  try:
    await handleMessage(message)
  except:
    print('exception caught:' )
    traceback.print_exc()


@client.event
async def on_member_join(member):
  global CONFIG
  await setRole(member, CONFIG['Basic_Guest_Role_Id'])


@client.event
async def on_message_edit(before, after):
  global CONFIG
  await handleMessage(after)
  

#===============================================================================
# Message Handling
#===============================================================================

async def handleMessage(message):
  if message.type is not guilded.MessageType.default or message.author.bot or not message.server:
    return

  if message.channel.id == CONFIG['License_Channel']:
    await handleRulesAgreement(message)

  if message.content[0] == '!':
    await handleCommand(message)

  profanity = checkForProfanity(message.content)
  if profanity is not None:
    await handleProfanity(message, profanity)


async def handleRulesAgreement(message):
  response = CONFIG['On_Rules_Not_Agreed_To']
  if 'i agree' in message.content.lower():
    response = CONFIG['On_Rules_Agreed_To']
  token = await apiGet('/api/generate/' + str(message.author.id) + '/' +
                       urllib.parse.quote(str(message.author.name)) +
                       '?avatar='+urllib.parse.quote(str(message.author.avatar)))
  token = token.decode()
  if 'ERROR:' in token:
    response = token.replace('ERROR: ', '')
  else:
    response = response.replace(
        '$URL', 'https://' + SERVER_URL + '/api/verify/'+token)
  await message.reply(response, private=True)
  return await message.delete()


#===============================================================================
# Commands
#===============================================================================

async def handleCommand(message):
  isSuperUser = await canExecuteCommand(message)
    
  commandList = {'mute', 'unmute', 'tweetstream', 'endtweetstream', 'help', 
    'checklicenses', 'invites', 'generateinvite', 'ban'}
  basicCommands = {'help', 'invites', 'generateinvite'}
  body = message.content[1:].split(' ')
  command = body[0].lower()
  
  if command not in basicCommands and not isSuperUser:
    return await message.reply(CONFIG['Bot_No_Command_Access'])
  
  if command not in commandList:
    await message.reply(CONFIG['Bot_Unknown_Command'].format(command), silent=True)
  
  if command == 'help':
    if not isSuperUser:
      return await basicHelp(message, body)
    return await help(message, body)
  elif command == 'mute':
    return await mute(message, body)
  elif command == 'unmute':
    return await unmute(message, body)
  elif command == 'ban':
    return await ban(message, body)
  elif command == 'tweetstream':
    return await tweetstream(message, body)
  elif command == 'endtweetstream':
    return await endtweetstream(message, body)
  elif command == 'invites':
    return await invites(message, body, False)
  elif command == 'generateinvite':
    return await invites(message, body, True)
  elif command == 'checklicenses':
    return await checkLicenses(message, body)
  return


async def canExecuteCommand(message):
  superusers = CONFIG['Can_Execute_Commands'].split(',')  
  try:    
    user = await client.http.get_member_roles(message.server.id, message.author.id)
    for role in user['roleIds']:
      if str(role) in superusers:
        return True
  except:
    pass
  return False


async def basicHelp(message, body):
  await message.reply(CONFIG['Bot_Basic_Help_Command'], private=True)
  return


async def help(message, body):
  await message.reply(CONFIG['Bot_Help_Command'], private=True)
  return


async def mute(message, body):
  if CONFIG['Enable_Mute_Command'] != 'true':
    await message.reply('Mute command currently disabled', private=True)
    
  if len(message.mentions) == 0:
    await message.reply(CONFIG['Bot_Invalid_Mute_No_User'], private=True)
  
  time = timeFromParams(body)
  
  if time == 0:
    time = int(CONFIG['Default_Mute_Time'])
    
  for user in message.mentions:
    await muteUser(user)
    await createScheduledJob({
      'name': 'Unmute ' + user.name,
      'run_function': 'unmute',
      'function_parameters': user.id,
      'paused': False,
      'next_run': datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(minutes=time),
      'job_data': b''
    })
    
  if len(message.mentions) == 1:
    await message.reply(CONFIG['Bot_Mute_Success'].format(message.mentions[0].name, time), private=True)
  else:
    await message.reply(CONFIG['Bot_Mute_Success'].format(str(len(message.mentions)) + ' users', time), private=True)
  return


async def unmute(message, body):
  if len(message.mentions) == 0:
    message.reply(CONFIG['Bot_Invalid_Mute_No_User'], private=True)
  
  for user in message.mentions:
    await unmuteUser(user)
  if len(message.mentions) == 1:
    await message.reply(CONFIG['Bot_Unmute_Success'].format(message.mentions[0].name), private=True)
  else:
    await message.reply(CONFIG['Bot_Unmute_Success'].format(str(len(message.mentions)) + ' users'), private=True)
  return


async def ban(message, body):
  if len(message.mentions) == 0:
    message.reply(CONFIG['Bot_Invalid_Mute_No_User'], private=True)

  con = sqlite3.connect('db.sqlite3')
  now = str(datetime.datetime.now(datetime.timezone.utc))
  for user in message.mentions:
    con.cursor().execute('UPDATE gumroad_guildeduser SET is_banned = ?, ban_reason = ?, banned_on = ? WHERE guilded_id = ?',
                         (1, ' '.join(body), now, user.id))
    await user.ban()
  con.commit()
  con.close()

async def tweetstream(message, body):
  try:
    fetchTypes = ['all', 'media', 'videos', 'images', 'text']
    if len(body) == 1:
      return await message.reply(CONFIG['Bot_Tweetstream_User_Not_Found'].format(''), private=True)
    if len(body) == 2 or body[2] not in fetchTypes:
      body = [*body[:2], 'media', *body[2:]]
    
    twitterUser = await getUserByUsername(body[1])
    
    if twitterUser is None:
      return await message.reply(CONFIG['Bot_Tweetstream_User_Not_Found'].format(body[1]), private=True)
    
    webhook = await guildedPost('/servers/'+str(message.server.id)+'/webhooks', json.dumps({
      'name': twitterUser['name'] + ' tweetstream',
      'channelId': message.channel.id
    }))
    
    time = timeFromParams(body)
    
    if time == 0:
      time = 60
    jobData = {
      'webhook': '/webhooks/{0}/{1}'.format(webhook['webhook']['id'], webhook['webhook']['token']),
      'webhook_id': webhook['webhook']['id'],
      'timedelta': time,
      'id': twitterUser['id']
    }
    await createScheduledJob({
      'name': twitterUser['username'] + ' TweetStream Task',
      'run_function': 'tweetstream',
      'function_parameters': ','.join(body[1:]),
      'paused': False,
      'next_run': datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(minutes=1),
      'job_data': json.dumps(jobData)
    })
    await message.reply(CONFIG['Bot_Tweetstream_Created_Successfully'].format(twitterUser['name']), private=True)
    return await periodic()
    
  except:
    print('exception caught:' )
    traceback.print_exc()
  return


async def endtweetstream(message, body):
  found = False
  try:
    con = sqlite3.connect('db.sqlite3')
    jobs = []
    for row in con.cursor().execute('SELECT id, function_parameters, job_data FROM '+\
      'gumroad_scheduledjob WHERE run_function = "tweetstream"'):
      if row[1].split(',')[0].lower() == body[1].lower():
        found = True
        job_data = json.loads(row[2])
        await guildedDelete('/servers/'+str(CONFIG['Guilded_Server_Id'])+'/webhooks/' + str(job_data['webhook_id']))
        await deleteScheduledJob({ 'id': row[0] })
        await message.reply(CONFIG['Bot_Tweetstream_Deleted'].format(body[1]))
    con.close()
  except:
    await message.reply('Failed to end tweetstream. An unexpected error occurred', private=True)
    print('exception caught:' )
    traceback.print_exc()
  if not found:
    await message.reply(CONFIG['Bot_Tweetstream_Not_Found'].format(body[1].lower()))
  
  
async def invites(message, body, forceGenerate):
  con = sqlite3.connect('db.sqlite3')
  me = None
  for row in con.cursor().execute('SELECT id, invites_allowed FROM gumroad_guildeduser WHERE guilded_id = ? AND verified = 1 LIMIT 1', (message.author.id,)):
    me = {
      'id': row[0],
      'invites_allowed': int(row[1])
    }
  if me is None:
    await message.reply('Who are you?', private=True)
    
  invites = []
  for row in con.cursor().execute('SELECT id, code FROM gumroad_invite WHERE from_user_id = ? AND to_user_id IS NULL', (me['id'], )):
    invites.append(row[1])  
  
  if len(invites) == 0 and me['invites_allowed'] <= 0:
    con.close()
    return await message.reply(CONFIG['Bot_No_Invites'])
  
  elif len(invites) == 0 or (forceGenerate and me['invites_allowed'] > 0):
    invite = inviteGenerator()
    now = str(datetime.datetime.now(datetime.timezone.utc))
    con.cursor().execute('INSERT INTO gumroad_invite (id, from_user_id, code, created_on, updated_on) VALUES (?,?,?,?,?)',
                         (str(uuid.uuid4()).replace('-',''), me['id'], invite, now, now))
    con.cursor().execute('UPDATE gumroad_guildeduser SET invites_allowed = ? WHERE id = ?',
                         (me['invites_allowed'] - 1, me['id']))
    con.commit()
    invites.append(invite)
  
  await message.reply(CONFIG['Bot_Invites'].format( ('\n'.join(invites)) ), private=True)
    
  con.close()

 
 
async def checkLicenses(message, body):
  (cancelCount, updateCount) = await checkLicenseJob()
  await message.reply(CONFIG['Bot_Licenses_Changed_Message']\
    .format(cancelCount, updateCount), private=True)

#===============================================================================
# Scheduled Job
#===============================================================================

async def periodic():
  while True:
    print('periodic')
    await runPendingJobs()    
    await asyncio.sleep(120)
   

async def runPendingJobs():
  jobs = await getPendingJobs()
  
  for job in jobs:
    if job['run_function'] == 'tweetstream' and CONFIG['Enable_Tweet_Streams'] == 'true':
      await sendRecentAttachments(job)
    if job['run_function'] == 'unmute':
      await unmuteJob(job)
  return

  

async def unmuteJob(job):
  params = job['function_parameters'].split(',')
  FakeUser = namedtuple('FakeUser', ('id', 'server'))
  u = FakeUser(id=params[0], server=FakeUser(id=CONFIG['Guilded_Server_Id'], server=None))
  await unmuteUser(u)
  await deleteScheduledJob(job)
  
  
client.run(GUILDED_BOT_TOKEN)