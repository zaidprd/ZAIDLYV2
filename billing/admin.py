from django.contrib import admin
from .models import CreditTransaction, CreditPackage, Payment


@admin.register(CreditPackage)
class CreditPackageAdmin(admin.ModelAdmin):
    list_display = ('name', 'credits', 'price_idr', 'price_per_credit', 'is_popular', 'is_active', 'sort_order')
    list_editable = ('is_popular', 'is_active', 'sort_order')


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'package', 'provider', 'status', 'amount_idr', 'credits_granted', 'created_at')
    list_filter = ('provider', 'status')
    search_fields = ('user__email', 'provider_ref')
    readonly_fields = ('created_at', 'paid_at', 'provider_ref', 'pay_url', 'raw')


@admin.register(CreditTransaction)
class CreditTransactionAdmin(admin.ModelAdmin):
    list_display = ('user', 'transaction_type', 'amount', 'description', 'created_at')
    list_filter = ('transaction_type',)
    search_fields = ('user__email', 'description')
    readonly_fields = ('created_at',)
    date_hierarchy = 'created_at'

    def has_add_permission(self, request):
        return request.user.is_superuser

    def has_change_permission(self, request, obj=None):
        return False
