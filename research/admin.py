from django.contrib import admin

from .models import ResearchSnapshot, CompetitorPage


class CompetitorPageInline(admin.TabularInline):
    model = CompetitorPage
    extra = 0


@admin.register(ResearchSnapshot)
class ResearchSnapshotAdmin(admin.ModelAdmin):
    list_display = ('keyword', 'gl', 'provider', 'search_intent', 'median_word_count', 'created_at')
    list_filter = ('provider', 'gl', 'ai_overview_present')
    search_fields = ('keyword',)
    inlines = [CompetitorPageInline]
