from django.urls import path
from . import views

urlpatterns = [
    path('', views.campaign_list, name='campaign_list'),
    path('start/<int:project_pk>/', views.campaign_start_ai, name='campaign_start_ai'),
    path('<int:pk>/', views.campaign_detail, name='campaign_detail'),
    path('<int:pk>/approve/', views.campaign_approve, name='campaign_approve'),
    path('<int:pk>/status/', views.campaign_status_poll, name='campaign_status_poll'),
]
