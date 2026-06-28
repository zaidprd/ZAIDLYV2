from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ('email', 'display_name', 'plan', 'credits', 'credits_used', 'is_active', 'date_joined')
    list_filter = ('plan', 'is_active', 'is_staff')
    search_fields = ('email', 'first_name', 'last_name')
    ordering = ('-date_joined',)
    fieldsets = BaseUserAdmin.fieldsets + (
        ('SEO.Zaidly', {'fields': ('credits', 'credits_used', 'plan')}),
        ('Threads', {'fields': ('threads_user_id', 'threads_access_token')}),
    )
