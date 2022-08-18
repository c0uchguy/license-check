import aiohttp
import datetime
import http.client
import json
import traceback
import urllib.parse
from codecs import encode
from guildedRequest import guildedWebhook
from helpers import timeFromParams
from scheduledJobs import updateScheduledJob


TWITTER_TOKEN = None

def setTwitterToken(token):
  global TWITTER_TOKEN
  TWITTER_TOKEN = token
  
async def twitterRequest(path, method, params=None):
  global TWITTER_TOKEN
  conn = http.client.HTTPSConnection('api.twitter.com')
  if path[0] != '/':
    path = '/' + path
  if params is not None:
    params = urllib.parse.urlencode(params)
    conn.request(method, '/2' + path,  params, headers={
      'Authorization': 'Bearer ' + TWITTER_TOKEN
    })
  else:  
    conn.request(method, '/2' + path, headers={
      'Authorization': 'Bearer ' + TWITTER_TOKEN  
    })
  req = conn.getresponse()
  data = req.read()
  return data


async def twitterGet(path):
  response = await twitterRequest(path, 'GET')
  global TWITTER_TOKEN
  return json.loads( (response).decode('utf8') )


async def twitterPut(path):
  response = (await twitterRequest(path, 'PUT')).decode('utf8')
  if len(response) == 0:
    return {}
  return json.loads( (response) )


async def twitterDelete(path):
  response = (await twitterRequest(path, 'DELETE')).decode('utf8')
  if len(response) == 0:
    return {}
  return json.loads( (response) )


async def twitterPost(path, params):
  return json.loads( (await twitterRequest(path, 'POST', params)).decode('utf8') )


async def getUserByUsername(username):
  response = await twitterGet('users/by/username/' + username)
  if 'errors' in response:
    return None
  return response['data']


async def sendRecentAttachments(job):
  jobData = {}
  params = job['function_parameters'].split(',')

  if type(job['job_data']) is str:
    job['job_data'] = json.loads(job['job_data'])

  jobData = job['job_data']

  if 'id' not in jobData:
    id = (await getUserByUsername(params[0]))['id']
    if id is None:
      pass
    jobData['id'] = id

  id = jobData['id']

  if 'last_run' in jobData:
    response = await twitterGet('/users/' + str(id) + '/tweets?expansions=attachments.media_keys' +
                                '&media.fields=variants%2Curl%2Cmedia_key&tweet.fields=attachments&start_time=' + jobData['last_run'])  # start_time=2022-08-01T00%3A00%3A00Z
  else:
    response = await twitterGet('/users/' + str(id) + '/tweets?expansions=attachments.media_keys' +
                                '&media.fields=variants%2Curl%2Cmedia_key&tweet.fields=attachments')

  jobData['last_run'] = datetime.datetime.now(
      datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ').replace(':', '%3A')

  if 'timedelta' not in jobData:
    time = timeFromParams(params)
    if time == 0:
      time = 60
    jobData['timedelta'] = time
  job['job_data'] = json.dumps(jobData)
  job['next_run'] = datetime.datetime.now(
      datetime.timezone.utc) + datetime.timedelta(minutes=jobData['timedelta'])
  await updateScheduledJob(job)

  if 'includes' in response and 'media' in response['includes']:
    i = 0
    for media in response['includes']['media']:
      i += 1
      if i > 4:
        break
      if media['type'] == 'photo' and (params[1] == 'all' or params[1] == 'media' or params[1] == 'images'):
        await uploadPhoto(media, job, response)
      elif media['type'] == 'video' and (params[1] == 'all' or params[1] == 'media' or params[1] == 'videos'):
        await uploadVideo(media, job, response)

  return


async def uploadPhoto(media, job, response):
  params = job['function_parameters'].split(',')
  if type(job['job_data']) is str:
    job['job_data'] = json.loads(job['job_data'])
  job_data = job['job_data']
  webhook = job_data['webhook']
  postText = 'new post by ' + params[0]
  if 'data' in response:
    for post in response['data']:
      if 'attachments' in post and 'media_keys' in post['attachments'] \
              and media['media_key'] in post['attachments']['media_keys']:
        postText = '[' + post['text'] + \
            '](https://twitter.com/' + \
            params[0] + '/status/' + post['id'] + ')'
        break
  return await uploadFileViaWebhook(media['url'], postText, webhook)


async def uploadVideo(media, job, response):
  if type(job['job_data']) is str:
    job['job_data'] = json.loads(job['job_data'])
  job_data = job['job_data']
  webhook = job_data['webhook']
  params = job['function_parameters'].split(',')
  postText = 'new post by ' + params[0]
  if 'data' in response:
    for post in response['data']:
      if 'attachments' in post and 'media_keys' in post['attachments'] \
              and media['media_key'] in post['attachments']['media_keys']:
        postText = '[' + post['text'] + \
            '](https://twitter.com/' + \
            params[0] + '/status/' + post['id'] + ')'
        break
  if 'variants' in media:
    highestBitrate = 0
    url = ''
    for variant in media['variants']:
      if 'application' not in variant['content_type']:
        if highestBitrate < variant['bit_rate']:
          url = variant['url']
          highestBitrate = variant['bit_rate']
    return await uploadFileViaWebhook(url, postText, webhook)
  return


async def uploadFileViaWebhook(url, postText, webhook):
  try:
    fdata = b''
    async with aiohttp.ClientSession() as session:
      async with session.get(url) as resp:
        if resp.status == 200:
          data = await resp.read()
          fdata += data
        else:
          print('error')
    boundary = 'wL36Yn8afVp8Ag7AmP8qZ0SA4n1v9T'

    filename = 'upload.mp4'
    lowerurl = url.lower()
    fileType = 'video/mp4'
    if '.png' in lowerurl:
      filename = 'upload.png'
      fileType = 'image/png'
    elif '.gif' in lowerurl:
      filename = 'upload.gif'
      fileType = 'image/gif'
    elif '.jpg' in lowerurl:
      filename = 'upload.jpg'
      fileType = 'image/jpeg'
    elif '.jpeg' in lowerurl:
      filename = 'upload.jpg'
      fileType = 'image/jpeg'
    dataList = []
    dataList.append(encode('--' + boundary))
    dataList.append(
        encode('Content-Disposition: form-data; name=payload_json;'))
    dataList.append(encode('Content-Type: application/json'))
    dataList.append(encode(''))
    dataList.append(encode('''{
  "allowed_mentions": true,
  "content": "''' + postText + '''",
  "attachments": [{
    "id": 0,
    "filename": "'''+filename+'''"
  }]
}'''))
    dataList.append(encode('--' + boundary))
    dataList.append(
        encode('Content-Disposition: form-data; name="files[0]"; filename='+filename))

    dataList.append(encode('Content-Type: {}'.format(fileType)))
    dataList.append(encode(''))
    dataList.append(fdata)

    dataList.append(encode('--' + boundary + '--'))
    dataList.append(encode(''))
    body = b'\r\n'.join(dataList)

    await guildedWebhook(webhook, body)
  except Exception as e:
    print('exception caught:')
    traceback.print_exc()
  return
