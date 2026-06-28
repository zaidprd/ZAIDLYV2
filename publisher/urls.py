from django.urls import path
from . import views

urlpatterns = [
    path('publish/<int:job_id>/', views.publish_now, name='publish_now'),
    path('bulk/', views.bulk_new, name='bulk_new'),
    path('bulk/create/', views.bulk_create, name='bulk_create'),
]
