from django.contrib.auth.views import LoginView, LogoutView
from django.urls import path
from .forms import LoginForm
from . import views

urlpatterns = [
    path('login/', LoginView.as_view(template_name='accounts/login.html', authentication_form=LoginForm), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('register/', views.register, name='register'),
    path('profile/', views.profile, name='profile'),
]
