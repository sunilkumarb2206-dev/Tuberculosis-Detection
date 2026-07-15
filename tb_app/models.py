from django.db import models
from django.contrib.auth.models import User

class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    phone = models.CharField(max_length=15)
    age = models.IntegerField(null=True, blank=True)
    gender = models.CharField(max_length=10, choices=[('Male', 'Male'), ('Female', 'Female'), ('Other', 'Other')])
    purpose = models.CharField(max_length=100, blank=True)

    def __str__(self):
        return self.user.username

class Report(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    patient_id = models.CharField(max_length=50) 
    patient_name = models.CharField(max_length=100, blank=True, default="Unknown Patient")
    xray_image = models.ImageField(upload_to='xrays/', blank=True, null=True)
    result = models.CharField(max_length=20)  
    confidence = models.FloatField()
    zone_data = models.JSONField(default=dict, blank=True)  # Added to track anomaly target zones
    diet_plan = models.TextField(blank=True)
    preventions = models.TextField(blank=True)
    doctor_suggestion = models.TextField(blank=True)
    raw_time = models.DateTimeField(auto_now_add=True)
    created_at = models.CharField(max_length=50, blank=True)

    def __str__(self):
        return f"Report {self.patient_id} - {self.result}"