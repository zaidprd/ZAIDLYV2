from django import forms
from .models import Project, WordPressSite

INPUT_CLASS = 'w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white placeholder-gray-500 focus:outline-none focus:border-violet-500 focus:ring-1 focus:ring-violet-500'


class ProjectForm(forms.ModelForm):
    class Meta:
        model = Project
        fields = ('name', 'language', 'target_audience', 'tone', 'ai_model',
                  'auto_publish', 'schedule_times', 'daily_limit', 'threads_enabled')
        widgets = {
            'name': forms.TextInput(attrs={'placeholder': 'Contoh: Blog Teknologi Saya', 'class': INPUT_CLASS}),
            'target_audience': forms.TextInput(attrs={'placeholder': 'Contoh: Pengusaha UMKM 25-45 tahun', 'class': INPUT_CLASS}),
            'ai_model': forms.TextInput(attrs={'placeholder': 'gpt-4o-mini', 'class': INPUT_CLASS}),
            'schedule_times': forms.TextInput(attrs={'placeholder': '08:00,13:00,20:00', 'class': INPUT_CLASS}),
            'daily_limit': forms.NumberInput(attrs={'min': 0, 'class': INPUT_CLASS}),
        }
        help_texts = {
            'schedule_times': 'Jam publish dipisah koma. Kosongkan untuk publish langsung.',
            'daily_limit': '0 = tidak terbatas.',
            'threads_enabled': 'Otomatis post ke Threads setelah artikel publish ke WordPress.',
        }


class WordPressSiteForm(forms.ModelForm):
    class Meta:
        model = WordPressSite
        fields = ('name', 'url', 'username', 'app_password')
        widgets = {
            'name': forms.TextInput(attrs={'placeholder': 'Contoh: Blog Utama', 'class': INPUT_CLASS}),
            'url': forms.URLInput(attrs={'placeholder': 'https://bloganda.com', 'class': INPUT_CLASS}),
            'username': forms.TextInput(attrs={'placeholder': 'Username WordPress', 'class': INPUT_CLASS}),
            'app_password': forms.PasswordInput(attrs={'placeholder': 'Application Password WordPress', 'class': INPUT_CLASS}, render_value=True),
        }
        help_texts = {
            'app_password': 'Buat di WordPress → Users → Profile → Application Passwords',
        }
