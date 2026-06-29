from django.contrib import admin

from .models import BusinessAnalysis


@admin.register(BusinessAnalysis)
class BusinessAnalysisAdmin(admin.ModelAdmin):
    list_display = ('project', 'website_fetched', 'model_used', 'cost_usd', 'created_at')
    list_filter = ('provider', 'language', 'website_fetched')
    search_fields = ('project__name',)
    readonly_fields = ('created_at', 'updated_at')
