from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_POST
from django_q.tasks import async_task

from ai_service import generate_text
from projects.models import Project
from queue_manager.models import QueueJob
from .prompt_builder import build_titles_messages


@login_required
def generate_new(request):
    projects = Project.objects.filter(user=request.user)
    # Customer butuh tahu SEBELUM klik kalau kredit tidak cukup -> kasih CTA top-up langsung.
    return render(request, 'generator/new.html', {
        'projects': projects,
        'credits': request.user.credits,
        'out_of_credits': request.user.credits < 1,
    })


@login_required
@require_POST
def generate_titles(request):
    keyword = request.POST.get('keyword', '').strip()
    project_id = request.POST.get('project', '')

    if not keyword or not project_id:
        return HttpResponse('<p class="text-red-400 text-sm">Keyword dan project wajib diisi.</p>')

    try:
        project = Project.objects.get(pk=project_id, user=request.user)
    except Project.DoesNotExist:
        return HttpResponse('<p class="text-red-400 text-sm">Project tidak ditemukan.</p>')

    try:
        messages = build_titles_messages(
            keyword,
            language=project.language,
            tone=project.get_tone_display(),
            target_audience=project.target_audience,
            writing_style=project.writing_style,
        )
        raw = generate_text(messages, model=project.ai_model or None, max_tokens=800, temperature=0.8)
        titles = _parse_titles(raw)
    except Exception as e:
        return HttpResponse(f'<p class="text-red-400 text-sm">Gagal generate judul: {e}</p>')

    return render(request, 'generator/partials/title_list.html', {
        'titles': titles,
        'keyword': keyword,
        'project': project,
        'opt_length': request.POST.get('length', ''),
        'opt_writing_style': request.POST.get('writing_style', ''),
        'opt_secondary_keywords': request.POST.get('secondary_keywords', ''),
        'opt_faq': request.POST.get('faq', '1'),
    })


@login_required
@require_POST
def generate_start(request):
    keyword = request.POST.get('keyword', '').strip()
    title = request.POST.get('title', '').strip()
    project_id = request.POST.get('project', '')

    if not all([keyword, title, project_id]):
        return redirect('generate_new')

    project = get_object_or_404(Project, pk=project_id, user=request.user)

    options = _collect_options(request)

    job = QueueJob.objects.create(
        user=request.user,
        project=project,
        job_type=QueueJob.TYPE_GENERATE,
        keyword=keyword,
        title=title,
        options=options,
        status=QueueJob.PENDING,
    )

    async_task('generator.tasks.run_generate_article', job.id)

    return redirect('generate_result', pk=job.pk)


@login_required
def generate_result(request, pk):
    job = get_object_or_404(QueueJob, pk=pk, user=request.user)
    return render(request, 'generator/result.html', {'job': job})


@login_required
def generate_result_poll(request, pk):
    job = get_object_or_404(QueueJob, pk=pk, user=request.user)
    return render(request, 'generator/partials/result_status.html', {'job': job})


def _collect_options(request):
    """Per-generation overrides from the form. Empty -> fall back to project defaults."""
    def csv(name):
        raw = request.POST.get(name, '').strip()
        return [s.strip() for s in raw.split(',') if s.strip()]

    options = {}
    length = request.POST.get('length', '').strip()
    if length.isdigit():
        options['length'] = int(length)
    style = request.POST.get('writing_style', '').strip()
    if style:
        options['writing_style'] = style
    goal = request.POST.get('goal', '').strip()
    if goal:
        options['goal'] = goal
    cta = request.POST.get('cta', '').strip()
    if cta:
        options['cta'] = cta
    image_style = request.POST.get('image_style', '').strip()
    if image_style:
        options['image_style'] = image_style
    secondary = csv('secondary_keywords')
    if secondary:
        options['secondary_keywords'] = secondary
    lsi = csv('lsi_keywords')
    if lsi:
        options['lsi_keywords'] = lsi
    internal = csv('internal_links')
    if internal:
        options['internal_links'] = internal
    external = csv('external_links')
    if external:
        options['external_links'] = external
    options['faq'] = bool(request.POST.get('faq', '').strip())
    return options


def _parse_titles(raw):
    titles = []
    for line in raw.strip().split('\n'):
        line = line.strip()
        if not line:
            continue
        # Strip leading "1. ", "1) ", "- ", etc.
        clean = line.lstrip('0123456789.-) ').strip()
        if clean:
            titles.append(clean)
    return titles[:15]
