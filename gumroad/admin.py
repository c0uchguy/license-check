from django.contrib import admin
from gumroad.models import Configuration, GuildedUser, Subscription, Invite,\
  IntegrationError, Profanity, ScheduledJob

@admin.register(Configuration)
class ConfigurationAdmin(admin.ModelAdmin):
  list_display = ('type', 'name', 'value')
  icon_name = 'tune'
  ordering = ('type', 'name')
  search_fields = ('name', 'value')
  list_editable = ('value',)
  list_filter = ('type',)
  list_display_links = ('name',)


@admin.register(Profanity)
class ProfanityAdmin(admin.ModelAdmin):
  list_display = ('word', 'how_to_handle', 'must_be_start_of_word')
  icon_name = 'volume_off'
  ordering = ('word',)
  list_editable = ('how_to_handle', 'must_be_start_of_word')
  search_fields = ('word', 'word_to_swap')
  list_filter = ('how_to_handle', 'must_be_start_of_word')


@admin.register(GuildedUser)
class GuildedUserAdmin(admin.ModelAdmin):
  list_display = ('guilded_username', 'verified', 'subscription', 'invites_allowed', 'is_banned', 'ban_reason', 'created_on')
  icon_name = 'contacts'
  search_fields = ('guilded_username', 'email')
  ordering = ('guilded_username',)
  
  list_filter = ('verified','is_banned', 'subscription')
  

@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
  list_display = ('name', 'gumroad_id', 'guilded_role_id')
  icon_name = 'shopping_cart'
  list_editable = ('guilded_role_id',)
  ordering = ('created_on',)
  

@admin.register(Invite)
class InviteAdmin(admin.ModelAdmin):
  list_display = ('from_user', 'to_user', 'code')
  icon_name = 'person_add'
  ordering = ('-created_on',)
  

@admin.register(IntegrationError)
class IntegrationErrorAdmin(admin.ModelAdmin):
  list_display = ('error_message', 'debug', 'type', 'created_on')
  icon_name = 'report'
  ordering = ('-created_on',)
  
  
@admin.register(ScheduledJob)
class ScheduledJobAdmin(admin.ModelAdmin):
  list_display = ('name', 'run_function', 'function_parameters', 'paused', 'next_run')
  icon_name = 'timelapse'
  ordering = ('-next_run',)
  
  