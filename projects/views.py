import requests as http
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages

from .forms import ProjectForm, WordPressSiteForm
from .models import Project, WordPressSite


@login_required
def project_list(request):
    projects = Project.objects.filter(user=request.user)
    return render(request, 'projects/list.html', {'projects': projects})


@login_required
def project_new(request):
    if request.method == 'POST':
        form = ProjectForm(request.POST)
        if form.is_valid():
            project = form.save(commit=False)
            project.user = request.user
            project.save()
            messages.success(request, f'Project "{project.name}" berhasil dibuat.')
            return redirect('project_detail', pk=project.pk)
    else:
        form = ProjectForm()
    return render(request, 'projects/form.html', {'form': form, 'title': 'Buat Project Baru'})


@login_required
def project_detail(request, pk):
    project = get_object_or_404(Project, pk=pk, user=request.user)
    sites = project.sites.all()
    return render(request, 'projects/detail.html', {'project': project, 'sites': sites})


@login_required
def project_edit(request, pk):
    project = get_object_or_404(Project, pk=pk, user=request.user)
    if request.method == 'POST':
        form = ProjectForm(request.POST, instance=project)
        if form.is_valid():
            form.save()
            messages.success(request, 'Project berhasil diperbarui.')
            return redirect('project_detail', pk=project.pk)
    else:
        form = ProjectForm(instance=project)
    return render(request, 'projects/form.html', {'form': form, 'title': 'Edit Project', 'project': project})


@login_required
def project_delete(request, pk):
    project = get_object_or_404(Project, pk=pk, user=request.user)
    if request.method == 'POST':
        project.delete()
        messages.success(request, 'Project dihapus.')
        return redirect('project_list')
    return render(request, 'projects/confirm_delete.html', {'project': project})


@login_required
def site_new(request, project_pk):
    project = get_object_or_404(Project, pk=project_pk, user=request.user)
    if request.method == 'POST':
        form = WordPressSiteForm(request.POST)
        if form.is_valid():
            site = form.save(commit=False)
            site.project = project
            site.save()
            messages.success(request, f'Site "{site.name}" berhasil ditambahkan.')
            return redirect('project_detail', pk=project.pk)
    else:
        form = WordPressSiteForm()
    return render(request, 'projects/site_form.html', {'form': form, 'project': project})


@login_required
def site_delete(request, project_pk, pk):
    project = get_object_or_404(Project, pk=project_pk, user=request.user)
    site = get_object_or_404(WordPressSite, pk=pk, project=project)
    if request.method == 'POST':
        site.delete()
        messages.success(request, 'Site dihapus.')
        return redirect('project_detail', pk=project.pk)
    return render(request, 'projects/confirm_delete_site.html', {'site': site, 'project': project})


@login_required
def site_test(request, project_pk, pk):
    project = get_object_or_404(Project, pk=project_pk, user=request.user)
    site = get_object_or_404(WordPressSite, pk=pk, project=project)
    try:
        resp = http.get(
            f"{site.url}/wp-json/wp/v2/users/me",
            auth=(site.username, site.app_password),
            timeout=10,
        )
        if resp.status_code == 200:
            wp_user = resp.json().get('name', '')
            html = f'<span class="badge-success">✓ Terhubung sebagai {wp_user}</span>'
        else:
            html = f'<span class="badge-error">✗ WordPress mengembalikan kode {resp.status_code}</span>'
    except Exception as e:
        html = f'<span class="badge-error">✗ {e}</span>'
    return HttpResponse(html)
