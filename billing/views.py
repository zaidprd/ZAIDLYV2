from decouple import config
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from .analytics import hpp_summary
from .credits import add_credits
from .models import CreditPackage, CreditTransaction, Payment
from .payments import get_provider


@login_required
def credit_history(request):
    transactions = CreditTransaction.objects.filter(user=request.user).select_related('job')[:50]
    return render(request, 'billing/history.html', {
        'transactions': transactions,
        'credits': request.user.credits,
        'credits_used': request.user.credits_used,
        'hpp': hpp_summary(request.user, credit_price_usd=config('CREDIT_PRICE_USD', default=0.0, cast=float)),
        'credit_price_usd': config('CREDIT_PRICE_USD', default=0.0, cast=float),
    })


@login_required
def package_list(request):
    packages = CreditPackage.objects.filter(is_active=True)
    return render(request, 'billing/packages.html', {
        'packages': packages,
        'provider': config('PAYMENT_PROVIDER', default='mock'),
    })


@login_required
@require_POST
def package_checkout(request, pk):
    package = get_object_or_404(CreditPackage, pk=pk, is_active=True)
    payment = Payment.objects.create(
        user=request.user, package=package, provider=config('PAYMENT_PROVIDER', default='mock'),
        amount_idr=package.price_idr,
    )
    try:
        invoice = get_provider().create_invoice(payment)
    except Exception as e:
        payment.status = Payment.FAILED
        payment.raw = {'error': str(e)}
        payment.save(update_fields=['status', 'raw'])
        messages.error(request, f'Gagal membuat invoice: {e}')
        return redirect('package_list')

    payment.provider_ref = invoice.provider_ref
    payment.pay_url = invoice.pay_url
    payment.raw = invoice.raw
    payment.save(update_fields=['provider_ref', 'pay_url', 'raw'])
    return redirect(invoice.pay_url)


@login_required
def payment_mock_confirm(request, pk):
    """Mock provider checkout page: shows summary; POST marks paid."""
    payment = get_object_or_404(Payment, pk=pk, user=request.user, provider='mock')
    if request.method == 'POST' and payment.status == Payment.PENDING:
        _mark_paid_and_grant(payment)
        messages.success(request, f'Pembayaran berhasil. {payment.credits_granted} kredit ditambahkan.')
        return redirect('credit_history')
    return render(request, 'billing/mock_checkout.html', {'payment': payment})


@csrf_exempt
@require_POST
def mayar_webhook(request):
    """Mayar callback — find the pending payment by provider_ref and grant credits."""
    import json
    try:
        data = json.loads(request.body or '{}')
    except json.JSONDecodeError:
        data = {}
    ref = str(data.get('id') or data.get('transactionId') or data.get('reference') or '')
    status = (data.get('status') or '').lower()
    if not ref:
        return redirect('credit_history')

    payment = Payment.objects.filter(provider='mayar', provider_ref=ref).first()
    if not payment or payment.status != Payment.PENDING:
        return redirect('credit_history')

    if status in ('paid', 'success', 'settled', 'completed'):
        _mark_paid_and_grant(payment)
    elif status in ('failed', 'cancelled', 'expired'):
        payment.status = Payment.FAILED if status != 'expired' else Payment.EXPIRED
        payment.save(update_fields=['status'])
    return redirect('credit_history')


def _mark_paid_and_grant(payment):
    """Grant credits exactly once per payment (idempotent)."""
    if payment.status == Payment.PAID:
        return
    add_credits(payment.user, payment.package.credits,
                description=f'Top-up paket {payment.package.name} ({payment.package.credits} kredit)')
    payment.status = Payment.PAID
    payment.credits_granted = payment.package.credits
    payment.paid_at = timezone.now()
    payment.save(update_fields=['status', 'credits_granted', 'paid_at'])
