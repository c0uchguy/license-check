import uuid
from django.db import models

class Profanity(models.Model):
  id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
  word = models.CharField(max_length=200)
  word_to_swap = models.CharField(max_length=200, null=True, blank=True)
  must_be_start_of_word = models.BooleanField(default=True)  
  how_to_handle = models.CharField(max_length=100, choices=(
    ('Censor word', 'Censor word'),
    ('Delete message', 'Delete message'),
    ('Instant ban', 'Instant ban'),
    ('Swap word with another', 'Swap word with another'),
    ('Delete and mute user', 'Delete and mute user'),
    #('Leave and notify moderator', 'Leave and notify moderator')
  ), default='Censor word')
  
  class Meta:
        verbose_name_plural = "Profanities"
  
  def __str__(self):
    return self.word


class Configuration(models.Model):
  id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
  name = models.CharField(max_length=200)
  value = models.TextField()  
  type = models.CharField(max_length=100, choices=(
    ('Application Setting', 'Application Setting'), 
    ('Integration Id', 'Integration Id'),
    ('Command Label', 'Command Label'),
    ('Label', 'Label')
  ), default='Label')
  
  def __str__(self):
    return self.name
  
  
class Subscription(models.Model):
  id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
  name = models.CharField(max_length=200)
  gumroad_id = models.CharField(max_length=200, blank=True, null=True)
  gumroad_permalink = models.CharField(max_length=200, blank=True, null=True)
  guilded_role_id = models.CharField(max_length=200, blank=True, null=True)
  invites_allowed = models.IntegerField(default=0)
  
  created_on = models.DateTimeField(auto_now_add=True, editable=False)
  updated_on = models.DateTimeField(auto_now=True)
  
  
  def __str__(self):
    return self.name


class GuildedUser(models.Model):
  id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
  guilded_username = models.CharField(max_length=200, blank=True)
  email = models.CharField(max_length=200, blank=True)
  guilded_id = models.CharField(max_length=200, blank=True, null=True)
  gumroad_id = models.CharField(max_length=200, blank=True, null=True)
  gumroad_license = models.CharField(max_length=100, blank=True, null=True)
  subscription = models.ForeignKey(Subscription, on_delete=models.PROTECT, blank=True, null=True)
  avatar = models.CharField(max_length=255, default="", null=True, blank=True)
  
  is_banned = models.BooleanField(default=False)
  ban_reason = models.CharField(max_length=255, blank=True, null=True)
  banned_on = models.DateTimeField(blank=True, null=True)
  
  verified = models.BooleanField(max_length=255, default=False, null=True)
  invites_allowed = models.SmallIntegerField(default=0)
  
  created_on = models.DateTimeField(auto_now_add=True, editable=False)
  updated_on = models.DateTimeField(auto_now=True)
  
  def __str__(self):
    return self.guilded_username
  
  

class Verification(models.Model):
  id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
  user = models.ForeignKey(GuildedUser, on_delete=models.CASCADE)
    
  created_on = models.DateTimeField(auto_now_add=True, editable=False)
  updated_on = models.DateTimeField(auto_now=True)
  

class Invite(models.Model):
  id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
  from_user = models.ForeignKey(GuildedUser, on_delete=models.PROTECT)
  to_user = models.ForeignKey(GuildedUser, on_delete=models.PROTECT, blank=True, related_name='to_user', null=True)
  code = models.CharField(max_length=255)
  
  created_on = models.DateTimeField(auto_now_add=True, editable=False)
  updated_on = models.DateTimeField(auto_now=True)
  
  def __str__(self):
    return 'Invite from ' + self.from_user.guilded_username
  
  
class IntegrationError(models.Model):
  error_message = models.CharField(max_length=200)
  debug = models.TextField()
  created_on = models.DateTimeField(auto_now_add=True, editable=False)
  
  type = models.CharField(max_length=100, choices=(
    ('Network Error', 'Network Error'), 
    ('Application Error', 'Application Error'), 
    ('Bot Error', 'Bot Error'), 
    ('Misc', 'Misc')
  ), default='Misc')
  
  def __str__(self):
    return self.type + ' ' + str(self.id)
  

class ScheduledJob(models.Model):
  id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
  name = models.CharField(max_length=200)
  run_function = models.CharField(max_length=200, choices=(
    ('unmute', 'Unmute User'),
    ('tweetstream', 'Post New Tweets to Channel'),
    ('licensecheck', 'Check Gumroad Licenses'),
    #('pullFromWeb', 'Pull data from website'),
  ))
  function_parameters = models.TextField()
  paused = models.BooleanField(default=False)
  next_run = models.DateTimeField(auto_now_add=True, editable=True)
  job_data = models.TextField(null=True, blank=True)
  
  def __str__(self):
    return self.name