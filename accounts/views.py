from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.views.decorators.http import require_POST

from .forms import RegisterForm
from . import threads_oauth


def register(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('dashboard')
    else:
        form = RegisterForm()
    return render(request, 'accounts/register.html', {'form': form})


@login_required
def profile(request):
    return render(request, 'accounts/profile.html')


@login_required
def threads_connect(request):
    """Start Threads connection. Real OAuth when configured, else an instant demo link."""
    if not threads_oauth.is_configured():
        request.user.threads_user_id = 'demo-threads-user'
        request.user.threads_access_token = 'demo-threads-token'
        request.user.save(update_fields=['threads_user_id', 'threads_access_token'])
        messages.success(request, 'Threads terhubung (mode demo). Tambahkan THREADS_APP_ID untuk OAuth asli.')
        return redirect('profile')
    return redirect(threads_oauth.authorize_url())


@login_required
def threads_callback(request):
    """OAuth redirect target (used only in real mode)."""
    code = request.GET.get('code')
    if not code:
        messages.error(request, 'Otorisasi Threads dibatalkan.')
        return redirect('profile')
    try:
        token, user_id = threads_oauth.exchange_code(code)
        request.user.threads_access_token = token
        request.user.threads_user_id = user_id
        request.user.save(update_fields=['threads_access_token', 'threads_user_id'])
        messages.success(request, 'Threads berhasil terhubung.')
    except Exception as e:
        messages.error(request, f'Gagal menghubungkan Threads: {e}')
    return redirect('profile')


@login_required
@require_POST
def threads_disconnect(request):
    request.user.threads_user_id = ''
    request.user.threads_access_token = ''
    request.user.save(update_fields=['threads_user_id', 'threads_access_token'])
    messages.success(request, 'Koneksi Threads diputuskan.')
    return redirect('profile')
