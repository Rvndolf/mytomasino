from django.urls import path
from . import views

app_name = 'tickets'

urlpatterns = [
    path('', views.ticket_list, name='ticket_overview'),
    path('create/', views.create_ticket, name='create_ticket'),
    path('<int:pk>/', views.ticket_detail, name='ticket_detail'),
    path('<int:pk>/delete/', views.delete_ticket, name='delete_ticket'),
    path('<int:pk>/update/', views.update_ticket, name='update_ticket'),
    path('ticket/<int:ticket_id>/reply/', views.add_user_reply, name='add_user_reply'),
]
