import os
import http.client

SERVER_URL = os.environ.get('SERVER_URL') or '127.0.0.1:8000'

async def apiRequest(path, method):
  conn = None
  try:
    conn = http.client.HTTPConnection(SERVER_URL)
  except:
    conn = http.client.HTTPConnection(SERVER_URL)
  
  if path[0] != '/':
    path = '/' + path
  conn.request(method, path)
  req = conn.getresponse()
  data = req.read()
  return data

async def apiGet(path):
  return await apiRequest(path, 'GET')