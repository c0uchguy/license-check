from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse
import re
import datetime
import json
from guildedRequest import guildedPut, guildedDelete
from ratelimit.core import get_usage
from .gumroadRequest import getPurchaseFromLicense
from asgiref.sync import sync_to_async, async_to_sync
from .config import getConfig, asyncGetConfig

from .models import Subscription, GuildedUser, Verification, Invite, \
  IntegrationError


licenseFormat = re.compile(r'[a-zA-Z0-9]{8}-[a-zA-Z0-9]{8}-[a-zA-Z0-9]{8}-[a-zA-Z0-9]{8}')

async def verify(request, user_id):
  body = json.loads(request.body)
  usage = get_usage(request, key='ip', rate='12/h', group='doVerify', increment=True)
  if usage is not None and usage['should_limit']:
    return HttpResponse('ERROR: ' + (await asyncGetConfig('Rate_Limited')))
  
  result = await sync_to_async(syncDoVerify)(request, user_id)
  if result is None:    
    license = getLicenseFromMessage(body['license'])
    purchase = await getPurchaseFromLicense(license)
    if purchase is None:
      return HttpResponse('ERROR: ' + (await asyncGetConfig('License_Not_Found')))
    else:
      return await sync_to_async(tieUserToPurchase)(user_id, purchase, license)
  return result


def getLicenseFromMessage(content):
  try: 
    matcher = re.match(licenseFormat, content)
    return matcher.group(0)
  except:
    return False
  

def syncTransferAccount(request, user_id):
  body = json.loads(request.body)
  usage = get_usage(request, key='ip', rate='12/h', group='transferAccount', increment=True)
  if usage is not None and usage['should_limit']:
    return (HttpResponse('ERROR: ' + getConfig('Rate_Limited')), 1,2)
  
  user = get_object_or_404(GuildedUser, pk=user_id)
  license = getLicenseFromMessage(body['license'])
  existingUser = getUserByLicense(license)
  
  if existingUser.is_banned:
    return (HttpResponse('ERROR: ' + getConfig('Banned')), 1,2)
  existingUser.verified = False
  user.verified = True
  user.gumroad_license = license.upper()
  user.subscription = existingUser.subscription
  user.invites_allowed = existingUser.invites_allowed
  user.gumroad_id = existingUser.gumroad_id
  if getConfig('Capture_User_Email') == 'true':
    user.email = existingUser.email  
  existingUser.save()
  user.save()
  try:
    verification = Verification.objects.get(user=user)
    verification.delete()
  except Verification.DoesNotExist:
    IntegrationError(
        error_message='Failed to delete verification object for user',
        type='Application Error',
        debug='User ' + user.guilded_username + ' was created but their verification record could not be purged.'
      ).save()
  return (None, user, existingUser)
 
 
 
def syncDoVerify(request, user_id):
  body = json.loads(request.body)
  user = get_object_or_404(GuildedUser, pk=user_id)
  license = getLicenseFromMessage(body['license'])
  if not license:
    return HttpResponse('ERROR: ' + getConfig('Invalid_License'))
  
  if user.verified:
    user.subscription.guilded_role_id
    user.guilded_id
    async_to_sync(setUserRoles)(user)
    return HttpResponse('ERROR: ' + getConfig('User_Is_Verified'))
  license = license.upper()
  existingUser = getUserByLicense(license)
  
  if existingUser != False:
    if existingUser.is_banned:
      return HttpResponse('ERROR: ' + getConfig('Banned'))
    return HttpResponse('CONFIRM: ' + getConfig('License_In_Use'))
  
  invite = getInviteByCode(license)
  if invite != False:
    if invite.to_user is not None:
      return HttpResponse('ERROR: ' + getConfig('License_In_Use'))
    invite.to_user = user
    user.verified = True
    user.gumroad_license = 'Invited by ' + invite.from_user.guilded_username
    try:
      user.subscription = Subscription.objects.get(name='Invited User Role')
    except Subscription.DoesNotExist:
      IntegrationError(
        error_message='Invited User Role not found',
        type='Application Error',
        debug='User ' + user.guilded_username + ' was invited, but could not be tied to an invited user role'
      ).save()
    invite.save()
    user.save()
    onSuccess(user)
    
    return HttpResponse('SUCCESS: ' + getConfig('Successfully_Created'))
  return None  


def tieUserToPurchase(user_id, purchase, license):
  user = get_object_or_404(GuildedUser, pk=user_id)
  purchase = purchase['purchase']
  if not isActivePurchase(purchase):
    return HttpResponse('ERROR: ' + getConfig('License_Inactive'))
    
  if getConfig('Capture_User_Email') == 'true':
    user.email = purchase['email']
  user.gumroad_id = purchase['id']
  
  for subscription in Subscription.objects.all():
    if subscription.name in purchase['variants']:
      user.subscription = subscription
      user.verified = True
      user.gumroad_license = license.upper()
      user.invites_allowed = subscription.invites_allowed
      user.save()
      break
  
  onSuccess(user)
    
  return HttpResponse('SUCCESS: ' + getConfig('Successfully_Created'))

  
def isActivePurchase(purchase):
  if purchase['refunded'] or purchase['disputed']:
    return False
  if dateInPast(purchase['subscription_ended_at']) or \
      dateInPast(purchase['subscription_cancelled_at']) or \
      dateInPast(purchase['subscription_failed_at']):
    return False
  return True
  
  
def dateInPast(dateOrNone):
  try:
    if dateOrNone is not None:
      date = datetime.datetime.strptime(dateOrNone, '%Y-%m-%dT%H:%M:%SZ')
      now = datetime.datetime.now
      if date < now:
        return True
  except:
    pass
  return False

def getUserByLicense(license):
  try:
    user = GuildedUser.objects.get(gumroad_license=license.upper(), verified=True)
    return user
  except GuildedUser.DoesNotExist:
    return False


def getInviteByCode(license):
  try:
    invite = Invite.objects.get(code=license)
    return invite
  except Invite.DoesNotExist:
    return False


def onSuccess(user):
  try:
    verification = Verification.objects.get(user=user)
    verification.delete()
  except Verification.DoesNotExist:
    IntegrationError(
        error_message='Failed to delete verification object for user',
        type='Application Error',
        debug='User ' + user.guilded_username + ' was created but their verification record could not be purged.'
      ).save()
  async_to_sync(setUserRoles)(user)
  
  
async def setUserRoles(user):
  serverId = await asyncGetConfig('Guilded_Server_Id')
  memberRole = await asyncGetConfig('Basic_Member_Role_Id')
  guestRole = await asyncGetConfig('Basic_Guest_Role_Id')
  response = await guildedPut('/servers/' + serverId + '/members/' + 
               str(user.guilded_id) + '/roles/' + str(user.subscription.guilded_role_id))
  
  if 'code' in response:
    await sync_to_async(onGuildedError)(response, user)
  r2 = await guildedPut('/servers/' + serverId + '/members/' +  str(user.guilded_id) + '/roles/' + memberRole)
  if 'code' in r2:
    await sync_to_async(onGuildedError)(r2, user)
  r3 = await guildedDelete('/servers/' + serverId + '/members/' + str(user.guilded_id) + '/roles/' + guestRole)
  if 'code' in r3:
    await sync_to_async(onGuildedError)(r3, user)
    
    

async def removeUserRoles(user):
  serverId = await asyncGetConfig('Guilded_Server_Id')
  memberRole = await asyncGetConfig('Basic_Member_Role_Id')
  guestRole = await asyncGetConfig('Basic_Guest_Role_Id')
  response = await guildedDelete('/servers/' + serverId + '/members/' + 
               str(user.guilded_id) + '/roles/' + str(user.subscription.guilded_role_id))
  
  if 'code' in response:
    await sync_to_async(onGuildedError)(response, user)
  r2 = await guildedDelete('/servers/' + serverId + '/members/' +  str(user.guilded_id) + '/roles/' + memberRole)
  if 'code' in r2:
    await sync_to_async(onGuildedError)(r2, user)
  r3 = await guildedPut('/servers/' + serverId + '/members/' + str(user.guilded_id) + '/roles/' + guestRole)
  if 'code' in r3:
    await sync_to_async(onGuildedError)(r3, user)



def onGuildedError(response, user):
  IntegrationError(
    error_message='Guilded communication failure',
    type='Network Error',
    debug='User ' + user.guilded_username + ' did not receive roles because: ' + response['message']
  ).save()