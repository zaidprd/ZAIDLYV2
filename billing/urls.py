from django.urls import path
from . import views

urlpatterns = [
    path('', views.credit_history, name='credit_history'),
    path('packages/', views.package_list, name='package_list'),
    path('packages/<int:pk>/checkout/', views.package_checkout, name='package_checkout'),
    path('payments/mock/<int:pk>/', views.payment_mock_confirm, name='payment_mock_confirm'),
    path('payments/mayar/webhook/', views.mayar_webhook, name='mayar_webhook'),
]
