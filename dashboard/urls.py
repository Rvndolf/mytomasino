from django.urls import path
from . import views

app_name = 'dashboard'


urlpatterns = [
    path('', views.dashboard_home, name='home'),  
    path('history/', views.dashboard_history, name='history'),
    path('settings/', views.dashboard_settings, name='settings'),    
    path('notifications/<int:notification_id>/mark-read/', views.mark_notification_read, name='mark_notification_read'),
    path('notifications/mark-all-read/', views.mark_all_notifications_read, name='mark_all_notifications_read'),
]


