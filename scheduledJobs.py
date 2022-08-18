import sqlite3
import uuid
import json
import datetime


async def getPendingJobs():
  con = sqlite3.connect('db.sqlite3')
  jobs = []
  for row in con.cursor()\
    .execute('SELECT id, name, run_function, function_parameters, paused, ' +
              'next_run, job_data FROM gumroad_scheduledjob '+
              'WHERE paused = false AND next_run < \''+str(datetime.datetime.now(datetime.timezone.utc))+'\''):
    jobs.append({
        'id': row[0],
        'name': row[1],
        'run_function': row[2],
        'function_parameters': row[3],
        'paused': row[4],
        'next_run': row[5],
        'job_data': {} if (row[6] == b'' or row[6] == '' or row[6] is None) else json.loads(row[6])
    })
  con.close()
  return jobs


async def createScheduledJob(job):
  con = sqlite3.connect('db.sqlite3')
  if 'job_data' in job and job['job_data'] != b'' and type(job['job_data'] is dict):
    job['job_data'] = json.dumps(job['job_data'])
  row = (str(uuid.uuid4()).replace('-', ''), job['name'], job['run_function'], job['function_parameters'], job['paused'],
         job['next_run'], job['job_data'])

  cur = con.cursor()
  cur.execute('INSERT INTO gumroad_scheduledjob VALUES (?,?,?,?,?,?,?)', row)
  con.commit()
  con.close()
  return


async def updateScheduledJob(job):
  con = sqlite3.connect('db.sqlite3')
  if 'job_data' in job and job['job_data'] != b'':
    if (type(job['job_data']) is dict):
      job['job_data'] = json.dumps(job['job_data'])
  row = (job['name'], job['run_function'], job['function_parameters'], job['paused'],
         job['next_run'], job['job_data'], job['id'])
  cur = con.cursor()
  cur.execute('UPDATE gumroad_scheduledjob SET name=?, run_function=?, function_parameters=?, paused=?, ' +
              'next_run=?, job_data=? WHERE id=?', row)
  con.commit()
  con.close()
  return


async def deleteScheduledJob(job):
  con = sqlite3.connect('db.sqlite3')
  cur = con.cursor()
  cur.execute('DELETE FROM gumroad_scheduledjob WHERE id=?', (job['id'],))
  con.commit()
  con.close()
  return
