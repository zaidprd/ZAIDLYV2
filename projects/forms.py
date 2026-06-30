from django import forms
from .models import Project, WordPressSite

INPUT_CLASS = 'w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white placeholder-gray-500 focus:outline-none focus:border-violet-500 focus:ring-1 focus:ring-violet-500'


class ProjectForm(forms.ModelForm):
    class Meta:
        model = Project
        # Business Profile (PRD §5) di depan: Analyzer butuh website/description/niche/country/goal
        # untuk memahami bisnis sebelum keyword discovery jalan.
        fields = (
            'name', 'language', 'website_url', 'business_description', 'niche',
            'target_country', 'goal', 'target_audience', 'brand_voice',
            'tone', 'writing_style', 'default_length', 'default_cta', 'ai_model',
            'auto_publish', 'schedule_times', 'daily_limit', 'threads_enabled',
        )
        widgets = {
            'name': forms.TextInput(attrs={'placeholder': 'Contoh: Blog Teknologi Saya', 'class': INPUT_CLASS}),
            'website_url': forms.URLInput(attrs={'placeholder': 'https://bisnisanda.com', 'class': INPUT_CLASS}),
            'business_description': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Contoh: Kami menjual panel listrik dan jasa pemasangannya untuk industri & komersial.', 'class': INPUT_CLASS}),
            'niche': forms.TextInput(attrs={'placeholder': 'Contoh: panel listrik industri', 'class': INPUT_CLASS}),
            'target_country': forms.TextInput(attrs={'placeholder': 'ID', 'class': INPUT_CLASS}),
            'target_audience': forms.TextInput(attrs={'placeholder': 'Contoh: Manajer pabrik & kontraktor listrik di Indonesia', 'class': INPUT_CLASS}),
            'brand_voice': forms.Textarea(attrs={'rows': 2, 'placeholder': 'Contoh: profesional, lugas, berbasis data teknis', 'class': INPUT_CLASS}),
            'default_cta': forms.TextInput(attrs={'placeholder': 'Contoh: Hubungi kami untuk konsultasi gratis', 'class': INPUT_CLASS}),
            'ai_model': forms.TextInput(attrs={'placeholder': 'kosongkan = default .env', 'class': INPUT_CLASS}),
            'schedule_times': forms.TextInput(attrs={'placeholder': '08:00,13:00,20:00', 'class': INPUT_CLASS}),
            'daily_limit': forms.NumberInput(attrs={'min': 0, 'class': INPUT_CLASS}),
        }
        help_texts = {
            'website_url': 'Sumber utama Business Analyzer & Discovery. Opsional, tapi sangat disarankan diisi.',
            'business_description': 'Wajib untuk AI Campaign — bahan baku Analyzer memahami bisnismu.',
            'niche': 'Topik utama bisnis. Membantu klasterisasi keyword.',
            'target_country': 'Kode negara Google (mis. ID, US). Default ID.',
            'goal': 'Tujuan utama: traffic, leads, sales — memandu prioritas keyword.',
            'writing_style': 'Bentuk artikel default. Bisa diubah saat generate.',
            'default_length': 'Panjang artikel default. Bisa diubah saat generate.',
            'brand_voice': 'Karakter/gaya brand yang tercermin di artikel.',
            'default_cta': 'Call-to-action default di akhir artikel.',
            'schedule_times': 'Jam publish dipisah koma. Kosongkan untuk publish langsung.',
            'daily_limit': '0 = tidak terbatas.',
            'threads_enabled': 'Otomatis post ke Threads setelah artikel publish ke WordPress.',
        }

    @property
    def business_profile_ready(self):
        """True bila Business Analyzer punya cukup input untuk dijalankan."""
        data = self.cleaned_data if self.is_valid() else {}
        return bool(
            (data.get('website_url') or data.get('business_description'))
            and (data.get('niche') or data.get('target_audience'))
        )


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
