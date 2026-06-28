from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from .models import CreditTransaction
from .analytics import hpp_summary


@login_required
def credit_history(request):
    transactions = CreditTransaction.objects.filter(user=request.user).select_related('job')[:50]
    return render(request, 'billing/history.html', {
        'transactions': transactions,
        'credits': request.user.credits,
        'credits_used': request.user.credits_used,
        'hpp': hpp_summary(request.user),
    })
