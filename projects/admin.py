from django.contrib import admin
from .models import Project, WordPressSite


class WordPressSiteInline(admin.TabularInline):
    model = WordPressSite
    extra = 0
    fields = ('name', 'url', 'username', 'is_active')


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ('name', 'user', 'language', 'tone', 'auto_publish', 'created_at')
    list_filter = ('language', 'tone', 'auto_publish')
    search_fields = ('name', 'user__email')
    inlines = [WordPressSiteInline]
