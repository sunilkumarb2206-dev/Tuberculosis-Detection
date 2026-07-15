from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    # Core Dashboard Layout Views
    path('', views.home_view, name='home'),
    path('analysis/', views.analysis_view, name='analysis'),
    path('records/', views.records_view, name='records'),
    path('about/', views.about_view, name='about'),
    path('support/', views.support_view, name='support'),
    path('profile/', views.profile_view, name='profile'),
    
    # Authentication & Password Management Views
    path('login/', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('logout/', views.logout_view, name='logout'),
    
    # Built-in Django Password Reset & Change URLs
    path('password_change/', auth_views.PasswordChangeView.as_view(), name='password_change'),
    path('password_change/done/', auth_views.PasswordChangeDoneView.as_view(), name='password_change_done'),
    
    path('password_reset/', auth_views.PasswordResetView.as_view(), name='password_reset'),
    path('password_reset/done/', auth_views.PasswordResetDoneView.as_view(), name='password_reset_done'),
    path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    path('reset/done/', auth_views.PasswordResetCompleteView.as_view(), name='password_reset_complete'),
    
    # Document / PDF / CSV Actions
    path('download-pdf/<int:report_id>/', views.download_pdf_view, name='download_pdf'),
    path('export-csv/', views.export_csv_view, name='export_csv'),
]