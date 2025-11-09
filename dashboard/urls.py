from django.urls import path
from . import views

app_name = 'dashboard'


urlpatterns = [
    path('', views.dashboard_home, name='home'),  
    path('history/', views.dashboard_history, name='history'),
    path('settings/', views.dashboard_settings, name='settings'),    
]

