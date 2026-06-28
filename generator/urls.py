from django.urls import path
from . import views

urlpatterns = [
    path('', views.generate_new, name='generate_new'),
    path('titles/', views.generate_titles, name='generate_titles'),
    path('start/', views.generate_start, name='generate_start'),
    path('<int:pk>/', views.generate_result, name='generate_result'),
    path('<int:pk>/poll/', views.generate_result_poll, name='generate_result_poll'),
]
