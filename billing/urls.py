from django.urls import path
from . import views

urlpatterns = [
    path('', views.credit_history, name='credit_history'),
]
