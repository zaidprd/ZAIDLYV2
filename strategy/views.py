"""Campaign UI views — mewujudkan PRD §31 goal:
'Isi Website -> Klik Generate Campaign -> Approve -> Start'.

Engine sudah ada di strategy/campaign.py & strategy/execution.py. View ini hanya
membungkus dengan UI sederhana. PRD §15: dilarang bikin generator kedua.
"""
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_POST

from projects.models import Project
from .campaign import start_ai_campaign
from .execution import start_campaign, run_campaign_tick
from .models import Campaign


def _project_ready_for_ai(project):
    """Project punya cukup info untuk Business Analyzer (PRD §6)."""
    has_input = bool(project.website_url or project.business_description)
    has_focus = bool(project.niche or project.target_audience)
    return has_input and has_focus


@login_required
def campaign_list(request):
    campaigns = Campaign.objects.filter(project__user=request.user).select_related('project')[:50]
    projects_ready = [p for p in Project.objects.filter(user=request.user) if _project_ready_for_ai(p)]
    return render(request, 'strategy/list.html', {
        'campaigns': campaigns,
        'projects_ready': projects_ready,
    })


@login_required
@require_POST
def campaign_start_ai(request, project_pk):
    """Trigger Build AI Campaign: analyzer -> discovery -> intelligence -> planner.
    Heavy work runs di django_q; view return instan, halaman detail polling status.
    """
    project = get_object_or_404(Project, pk=project_pk, user=request.user)
    if not _project_ready_for_ai(project):
        messages.error(request, 'Lengkapi Business Profile (website/deskripsi + niche/audience) dulu agar AI bisa menganalisa bisnismu.')
        return redirect('project_detail', pk=project.pk)

    try:
        articles_per_day = int(request.POST.get('articles_per_day') or 3)
    except (TypeError, ValueError):
        articles_per_day = 3
    try:
        limit = int(request.POST.get('limit') or 20)
    except (TypeError, ValueError):
        limit = 20

    campaign = start_ai_campaign(
        project,
        name=request.POST.get('name', '').strip() or f"Campaign {project.name}",
        articles_per_day=max(1, min(articles_per_day, 50)),
        limit=max(5, min(limit, 100)),
    )
    messages.success(request, 'Campaign dibuat. AI sedang menganalisa bisnismu, menemukan keyword, dan menyusun strategi.')
    return redirect('campaign_detail', pk=campaign.pk)


@login_required
def campaign_detail(request, pk):
    campaign = get_object_or_404(Campaign.objects.select_related('project'),
                                 pk=pk, project__user=request.user)
    items = list(campaign.items.select_related('keyword').order_by('-priority')[:200])
    return render(request, 'strategy/detail.html', {
        'campaign': campaign,
        'items': items,
    })


@login_required
@require_POST
def campaign_approve(request, pk):
    """Approve content plan -> mulai daily drip.

    start_campaign mendaftarkan Schedule DAILY ke django_q. Drip pertama dijalankan
    langsung supaya customer melihat artikel mulai diproses, bukan menunggu besok.
    """
    campaign = get_object_or_404(Campaign, pk=pk, project__user=request.user)
    if campaign.status != 'plan_ready':
        messages.error(request, 'Campaign belum siap dijalankan. Tunggu plan selesai dibuat.')
        return redirect('campaign_detail', pk=campaign.pk)

    start_campaign(campaign)                  # status -> 'running' + register daily Schedule
    run_campaign_tick(campaign)               # first drip immediately (menyenangkan customer)
    messages.success(request, 'Campaign dimulai. Artikel pertama sedang diproses; sisanya menyusul setiap hari.')
    return redirect('campaign_detail', pk=campaign.pk)


@login_required
def campaign_status_poll(request, pk):
    """HTMX partial: progress step + counts + status badge. Polled tiap 3 detik
    selama campaign masih building/running."""
    campaign = get_object_or_404(Campaign, pk=pk, project__user=request.user)
    return render(request, 'strategy/_status_block.html', {'campaign': campaign})
