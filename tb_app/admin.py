from django.contrib import admin
from .models import Profile, Report

@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = ('id', 'patient_id', 'patient_name', 'result', 'confidence', 'created_at', 'user')
    search_fields = ('patient_id', 'patient_name', 'result')
    list_filter = ('result', 'created_at')

@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'phone', 'age', 'gender', 'purpose')
    search_fields = ('user__username', 'user__email', 'phone')