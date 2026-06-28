from django.contrib import admin
from django.urls import path, include
from django.views.generic import RedirectView
from .monitoring import monitoring

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', RedirectView.as_view(url='/dashboard/', permanent=False)),
    path('auth/', include('accounts.urls')),
    path('dashboard/', include('queue_manager.urls')),
    path('projects/', include('projects.urls')),
    path('generate/', include('generator.urls')),
    path('', include('publisher.urls')),
    path('credits/', include('billing.urls')),
    path('monitoring/', monitoring, name='monitoring'),
]
