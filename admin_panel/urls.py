from django.urls import path
from . import views

app_name = 'admin_panel'

urlpatterns = [
    path('', views.admin_home, name='admin_home'),
    path('users/', views.users_list, name='users_list'),
    path('users/<int:user_id>/profile/', views.user_profile_view, name='user_profile_view'),
    path('tickets/', views.ticket_list, name='ticket_list'),
    path('tickets/<int:ticket_id>/', views.ticket_detail, name='ticket_detail'),
    path('tickets/<int:ticket_id>/update/', views.update_ticket_status, name='update_ticket'),
    path('tickets/<int:ticket_id>/add-note/', views.add_ticket_note, name='add_ticket_note'),
    path('tickets/<int:ticket_id>/delete/', views.delete_ticket, name='delete_ticket'),
    path('notification-count/', views.notification_count, name='notification_count'),
    path('notifications/<int:notification_id>/mark-read/', views.mark_notification_read, name='mark_notification_read'),
    path('notifications/mark-all-read/', views.mark_all_notifications_read, name='mark_all_notifications_read'),
]