from django.contrib import admin

from .models import ContentBrief


@admin.register(ContentBrief)
class ContentBriefAdmin(admin.ModelAdmin):
    list_display = ('keyword', 'search_intent', 'recommended_word_count', 'provider',
                    'model_used', 'cost_usd', 'created_at')
    list_filter = ('provider', 'language', 'search_intent')
    search_fields = ('keyword',)
    readonly_fields = ('created_at', 'updated_at')
