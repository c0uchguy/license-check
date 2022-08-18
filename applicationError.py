import sqlite3
import uuid
import datetime

def throwError(message, debug, errorType):
  errorType = errorType or 'Misc'
  con = sqlite3.connect('db.sqlite3')
  cur = con.cursor()
  cur.execute('INSERT INTO gumroad_integrationerror (error_message, debug, type, created_on)', (
      message,
      debug,
      errorType,
      str(datetime.datetime.now(datetime.timezone.utc))
  ))
  con.commit()
  con.close()


def applicationError(message,debug):
  return throwError(message, debug, 'Application Error')


def networkError(message,debug):
  return throwError(message, debug, 'Network Error')


def botError(message,debug):
  return throwError(message, debug, 'Bot Error')