from django.urls import path


from . import views
app_name = 'gumroad'
urlpatterns = [
    path('verify/<str:verification_id>', views.index, name='index'),
    path('doVerify/<str:user_id>', views.verify, name='doVerify'),
    path('transferAccount/<str:user_id>', views.transferAccount, name='transferAccount'),
    path('generate/<str:guilded_id>/<str:username>', views.generateNewUser, name='generate'),
    path('buildProducts/', views.buildProducts, name='buildProducts'),
    path('config/', views.getConfigData, name='getConfigData'),
    path('profanity/', views.getProfanity, name='getProfanity'),
]