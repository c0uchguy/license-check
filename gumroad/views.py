from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse
import re
import json
import traceback
from ratelimit.core import get_usage
from .gumroadRequest import getProducts
from asgiref.sync import sync_to_async, async_to_sync
from .config import config, getConfig, asyncGetConfig
from .verify import setUserRoles, verify, syncTransferAccount, removeUserRoles
from .models import Subscription, GuildedUser, Verification, \
  IntegrationError, Profanity


shortCodeFormat = re.compile(r'.+/l/(.+)')

def index(request, verification_id):
  verification = get_object_or_404(Verification, pk=verification_id)
  user = verification.user
  print(request.GET.get('avatar'))
  return render(request, 'verify.html', {
    'guildedUser': user,
    'config': config()
  })

def generateNewUser(request, guilded_id, username):
  usage = get_usage(request, key='ip', rate='8/h', group='generateUser', increment=True)
  if usage is not None and usage['should_limit']:
    return HttpResponse('ERROR: ' + getConfig('Rate_Limited'))
  
  user = None
  verification = None
  try: 
    try:
      user = GuildedUser.objects.get(guilded_id=guilded_id)
      if user.verified:
        print(user.subscription.guilded_role_id)
        print(user.guilded_id)
        async_to_sync(setUserRoles)(user)
        return HttpResponse('ERROR: ' + getConfig('User_Is_Verified'))
      try:
        verification = Verification.objects.get(user=user)
      except Verification.DoesNotExist:
        verification = Verification(user=user)
        verification.save()
      return HttpResponse(str(verification.id))
    
    except GuildedUser.DoesNotExist:
      
      user = GuildedUser(guilded_id=guilded_id, guilded_username=username, \
        avatar=request.GET.get('avatar'))
      user.save()
      verification = Verification(user=user)
      verification.save()
      return HttpResponse(str(verification.id))
    
  except:
    print('exception caught:' )
    IntegrationError(
        error_message='New user generation crashed',
        type='Application Error',
        debug=traceback.format_exc()
      ).save()
    traceback.print_exc()
  return HttpResponse('ERROR: ' + getConfig('Internal_Server_Error')) 
    

async def doVerify(request, user_id):
  await verify(request, user_id)


async def transferAccount(request, user_id):
  (response, user, existingUser) = await sync_to_async(syncTransferAccount)(request, user_id)
  if response is not None:
    return response
  
  await removeUserRoles(existingUser)
  await setUserRoles(user)
  return HttpResponse('SUCCESS: ' + (await asyncGetConfig('Successfully_Created')))

 

async def buildProducts(request):
  print('Here')
  products = await getProducts()

  await sync_to_async(createMissingProduct)(products)
      
  return HttpResponse('Success')



def getConfigData(request):
  return HttpResponse(json.dumps(config()))
  
def getProfanity(request):
  profanity = {}
  for word in Profanity.objects.all():
    profanity[word.word] = {
      'must_be_start_of_word': word.must_be_start_of_word,
      'how_to_handle': word.how_to_handle,
      'word_to_swap': word.word_to_swap
    }
  return HttpResponse(json.dumps(profanity))

def createMissingProduct(products):
  for product in products['products']:
    permalink = re.match(shortCodeFormat, product['short_url']).group(1)
    gumroad_id = product['id']
    for variant in product['variants']:
      for option in variant['options']:
        try:
          sub = Subscription.objects.get(name=option['name'])
        except Subscription.DoesNotExist:
          sub = Subscription(gumroad_id=gumroad_id, 
                              gumroad_permalink=permalink, 
                              name=option['name'])
          sub.save()

