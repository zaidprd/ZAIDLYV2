from django.urls import path
from . import views

urlpatterns = [
    path('', views.project_list, name='project_list'),
    path('new/', views.project_new, name='project_new'),
    path('<int:pk>/', views.project_detail, name='project_detail'),
    path('<int:pk>/edit/', views.project_edit, name='project_edit'),
    path('<int:pk>/delete/', views.project_delete, name='project_delete'),
    path('<int:project_pk>/sites/new/', views.site_new, name='site_new'),
    path('<int:project_pk>/sites/<int:pk>/delete/', views.site_delete, name='site_delete'),
    path('<int:project_pk>/sites/<int:pk>/test/', views.site_test, name='site_test'),
]
