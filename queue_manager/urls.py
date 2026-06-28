from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard_summary, name='dashboard'),
    path('queue/', views.queue_list, name='queue_list'),
    path('queue/<int:pk>/', views.queue_detail, name='queue_detail'),
    path('queue/<int:pk>/<str:action>/', views.queue_action, name='queue_action'),
    path('queue/<int:pk>/poll/', views.queue_status_poll, name='queue_poll'),
]
