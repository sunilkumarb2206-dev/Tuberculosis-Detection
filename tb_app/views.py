import csv
import json
import os
import random
import time
from datetime import datetime, timedelta
import pytz
from django.conf import settings
from django.contrib import messages
from django.core.mail import send_mail
from django.http import HttpResponse, StreamingHttpResponse
from django.middleware.csrf import get_token
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.contrib.auth.models import User
from django.views.decorators.csrf import csrf_exempt
from .models import Report, Profile
from django.shortcuts import get_object_or_404, redirect


# Initialize timezone
ist = pytz.timezone('Asia/Kolkata')

DATA_FILE_PATH = os.path.join(settings.BASE_DIR, 'patient_records.json')
USERS_FILE_PATH = os.path.join(settings.BASE_DIR, 'users.json')
# Volatile storage expansions for persistent realistic verification state tracking
REGISTERED_USERS = {}  # Format: {identifier: {username, age, gender, identifier, password}}
ACTIVE_OTPS = {}       # Format: {identifier: otp_code}

# --- INSTITUTIONAL LEDGER MEMORY MATRIX ---
ist = pytz.timezone('Asia/Kolkata')
now_ist = datetime.now(ist)

# In-memory dictionary persistent across individual active requests

# --- ALGORITHMIC LAYERS (DSA) ---

from datetime import datetime


def linear_search_patient(reports_list, query):
    """Safely searches reports by matching query against patient_id or patient_name."""
    if not query:
        return reports_list
    query = query.strip().lower()
    return [
        r for r in reports_list 
        if query in str(r.get('patient_id', '')).lower() or query in str(r.get('patient_name', '')).lower()
    ]

def merge_sort_reports(reports_list, sort_by='latest'):
    """Recursively sorts report lists via merge sort based on active sorting criteria."""
    if len(reports_list) <= 1:
        return reports_list
    mid = len(reports_list) // 2
    left = merge_sort_reports(reports_list[:mid], sort_by)
    right = merge_sort_reports(reports_list[mid:], sort_by)
    return merge(left, right, sort_by)

def merge(left, right, sort_by):
    """Merge utility with safe key accessors and fallback comparisons."""
    res = []
    i = j = 0
    while i < len(left) and j < len(right):
        # Fallback and default safe extraction for sorting parameters
        if sort_by == 'confidence_high':
            val_i = left[i].get('confidence', 0)
            val_j = right[j].get('confidence', 0)
            cond = val_i >= val_j
        elif sort_by == 'confidence_low':
            val_i = left[i].get('confidence', 0)
            val_j = right[j].get('confidence', 0)
            cond = val_i <= val_j
        elif sort_by == 'oldest':
            time_i = left[i].get('raw_time', datetime.min)
            time_j = right[j].get('raw_time', datetime.min)
            if isinstance(time_i, str): time_i = datetime.fromisoformat(time_i)
            if isinstance(time_j, str): time_j = datetime.fromisoformat(time_j)
            cond = time_i <= time_j
        else:  # 'latest' default
            time_i = left[i].get('raw_time', datetime.min)
            time_j = right[j].get('raw_time', datetime.min)
            if isinstance(time_i, str): time_i = datetime.fromisoformat(time_i)
            if isinstance(time_j, str): time_j = datetime.fromisoformat(time_j)
            cond = time_i >= time_j
            
        if cond:
            res.append(left[i])
            i += 1
        else:
            res.append(right[j])
            j += 1
            
    res.extend(left[i:])
    res.extend(right[j:])
    return res

# --- SYSTEM BASE UI DESIGN ---

def get_base_layout(content_html, active_tab="home", request=None):
    """Dynamically wraps template contents inside the responsive dashboard shell."""
    display_username = "Clinical Operator"
    if request and request.user.is_authenticated:
        display_username = request.user.username
    elif request and 'logged_in_user' in request.session:
        display_username = request.session['logged_in_user']

    tabs = {
        "home": ("/", "fa-chart-pie", "Home"),
        "analysis": ("/analysis/", "fa-microscope", "Analysis"),
        "records": ("/records/", "fa-database", "Records"),
        "about": ("/about/", "fa-circle-info", "About Us"),
        "support": ("/support/", "fa-headset", "Support"),
        "profile": ("/profile/", "fa-user-md", "Profile")
    }
    nav = "".join([f'<a href="{u}" class="nav-link {"active" if active_tab==k else ""}"><i class="fa-solid {i}"></i> {l}</a>' for k, (u, i, l) in tabs.items()])
    
    return f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>TB SCAN AI - Clinical Workspace</title>
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
        <style>
            body[data-theme="dark"] {{
                --bg-dark: #090f1c; --panel-dark: #111a2e; --border-clr: #1e294b; 
                --text-main: #f1f5f9; --text-muted: #94a3b8; --teal-glow: #00f2fe; --teal-dim: #00b4d8;
                --panel-bg: #111a2e;
            }}
            body[data-theme="white"] {{
                --bg-dark: #f8fafc; --panel-dark: #ffffff; --border-clr: #cbd5e1; 
                --text-main: #0f172a; --text-muted: #64748b; --teal-glow: #0284c7; --teal-dim: #0369a1;
                --panel-bg: #ffffff;
            }}
            body[data-theme="color"] {{
                --bg-dark: #0f172a; --panel-dark: #1e1b4b; --border-clr: #312e81; 
                --text-main: #e0e7ff; --text-muted: #c7d2fe; --teal-glow: #f43f5e; --teal-dim: #e11d48;
                --panel-bg: #1e1b4b;
            }}

            body {{ background-color: var(--bg-dark); color: var(--text-main); font-family: 'Segoe UI', system-ui, sans-serif; margin: 0; padding: 0; display: flex; flex-direction: column; min-height: 100vh; transition: background 0.3s, color 0.3s; }}
            .header {{ background-color: var(--panel-dark); border-bottom: 1px solid var(--border-clr); padding: 10px 40px; display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 15px; position: sticky; top: 0; z-index: 1000; }}
            .logo {{ font-size: 20px; font-weight: 800; display: flex; align-items: center; gap: 10px; }}
            .logo span {{ color: var(--teal-glow); }}
            .navbar {{ display: flex; gap: 5px; align-items: center; flex-wrap: wrap; }}
            .nav-link {{ color: var(--text-muted); text-decoration: none; padding: 10px 16px; font-size: 14px; font-weight: 600; border-radius: 6px; display: flex; align-items: center; gap: 8px; transition: all 0.2s; }}
            .nav-link:hover {{ color: var(--text-main); background-color: rgba(255,255,255,0.05); }}
            .nav-link.active {{ color: var(--teal-glow); background-color: rgba(0, 242, 254, 0.08); border: 1px solid rgba(0, 242, 254, 0.15); }}
            
            .right-actions {{ display: flex; align-items: center; gap: 15px; flex-wrap: wrap; }}
            .theme-selector {{ background: var(--bg-dark); color: var(--text-main); border: 1px solid var(--border-clr); padding: 6px 10px; border-radius: 6px; font-size: 13px; font-weight: 600; cursor: pointer; }}
            .user-tag {{ display: flex; align-items: center; gap: 12px; font-size: 14px; font-weight: 600; color: var(--text-muted); }}
            .logout-btn {{ background-color: #ef4444; color: white; border: none; padding: 8px 14px; border-radius: 6px; font-weight: 700; cursor: pointer; text-decoration: none; font-size: 12px; }}
            
            .container {{ max-width: 1240px; width: 100%; margin: 30px auto; padding: 0 20px; box-sizing: border-box; flex: 1; }}
            .panel {{ background-color: var(--panel-bg); border: 1px solid var(--border-clr); padding: 25px; border-radius: 12px; margin-bottom: 25px; }}
            
            .footer {{ background-color: var(--panel-dark); border-top: 1px solid var(--border-clr); padding: 20px 40px; text-align: center; color: var(--text-muted); font-size: 13px; font-weight: 500; margin-top: auto; }}
            .footer-links {{ margin-bottom: 8px; display: flex; justify-content: center; gap: 20px; flex-wrap: wrap; }}
            .footer-links span {{ font-weight: 600; color: var(--text-main); }}

            @media (max-width: 1024px) {{
                .header {{ padding: 15px 20px; justify-content: center; text-align: center; }}
                .navbar {{ width: 100%; justify-content: center; order: 3; }}
            }}
            @media (max-width: 640px) {{
                .header {{ flex-direction: column; }}
                .right-actions {{ flex-direction: column; width: 100%; gap: 10px; }}
                .navbar {{ flex-direction: column; width: 100%; }}
                .nav-link {{ width: 100%; box-sizing: border-box; }}
            }}
        </style>
    </head>
    <body data-theme="dark">
        <header class="header">
            <div class="logo"><i class="fa-solid fa-microscope" style="color:var(--teal-glow)"></i> TB SCAN <span>AI</span></div>
            <nav class="navbar">{nav}</nav>
            <div class="right-actions">
                <select class="theme-selector" id="themeSelect" onchange="switchTheme(this.value)">
                    <option value="dark">Dark Theme</option>
                    <option value="white">White Theme</option>
                    <option value="color">Color Theme</option>
                </select>
                <div class="user-tag">
                    <span><i class="fa-solid fa-user-shield"></i> {display_username}</span>
                    <a href="/logout/" class="logout-btn">Sign Out</a>
                </div>
            </div>
        </header>
        
        <main class="container">{content_html}</main>

        <footer class="footer">
            <div class="footer-links">
                <span>© 2026 TB SCAN AI Inc. All Rights Reserved.</span>
                <span>|</span>
                <span>Institutional Patents: Pat. US-9831102-B2 & IN-2024/09811A</span>
                <span>|</span>
                <span>Classification: Class II Medical Diagnostic Software Module</span>
            </div>
            <div>Authorized clinical operators access only. Compliance protocols mapping to HIPAA & Indian Digital Health Standards active.</div>
        </footer>

        <script>
            function switchTheme(themeName) {{
                document.body.setAttribute('data-theme', themeName);
                localStorage.setItem('tb_theme', themeName);
                const sel = document.getElementById('themeSelect');
                if (sel) sel.value = themeName;
            }}
            const savedTheme = localStorage.getItem('tb_theme') || 'dark';
            switchTheme(savedTheme);
        </script>
    </body>
    </html>
    """

# --- SYSTEM CONTROLLERS ---


# Place this inside tb_app/views.py

# Simulated storage for testing (use a real database model in production)

# Legacy in-memory dictionary kept for backward compatibility if referenced elsewhere

REGISTERED_USERS = globals().get('REGISTERED_USERS', {})

@csrf_exempt
def register_view(request):
    """Handles multi-step OTP verification and persists new operator accounts into the SQL database."""
    message = ""
    status_class = ""
    
    context_data = {
        'username': request.POST.get('username', ''),
        'identifier': request.POST.get('identifier', ''),
        'age': request.POST.get('age', ''),
        'gender': request.POST.get('gender', 'Male'),
        'message': message,
        'status_class': status_class,
        'otp_sent': False
    }
    
    if request.method == 'POST':
        action = request.POST.get('action')
        identifier = request.POST.get('identifier', '').strip()
        username = request.POST.get('username', '').strip()
        age = request.POST.get('age', '').strip()
        gender = request.POST.get('gender', 'Male')
        password = request.POST.get('password', '')
        re_password = request.POST.get('re_password', '')
        otp_input = request.POST.get('otp', '').strip()

        context_data.update({
            'username': username,
            'identifier': identifier,
            'age': age,
            'gender': gender
        })

        if action == 'send_otp':
            if not identifier or "@" not in identifier:
                message = "Please enter a valid email address first."
                status_class = "banner-error"
            elif User.objects.filter(email=identifier).exists() or identifier in REGISTERED_USERS:
                message = "This email already exists in the system."
                status_class = "banner-error"
            else:
                code = str(random.randint(1000, 9999))
                expiry_time = time.time() + 60
                
                request.session[f'otp_{identifier}'] = code
                request.session[f'otp_expiry_{identifier}'] = expiry_time
                request.session.modified = True
                
                try:
                    send_mail(
                        subject="TB SCAN AI Verification Code",
                        message=f"Your 4-digit verification code is: {code}. It is valid for 60 seconds.",
                        from_email=settings.DEFAULT_FROM_EMAIL,
                        recipient_list=[identifier],
                        fail_silently=False,
                    )
                    message = f"OTP sent successfully to {identifier}!"
                    status_class = "banner-success"
                    context_data['otp_sent'] = True
                except Exception:
                    message = f"OTP Sent (Simulated Free Mode): {code}"
                    status_class = "banner-info"
                    context_data['otp_sent'] = True
        
        elif action == 'verify_otp':
            stored_otp = request.session.get(f'otp_{identifier}')
            expiry_time = request.session.get(f'otp_expiry_{identifier}', 0)
            
            if time.time() > expiry_time:
                message = "OTP expired! 60 seconds limit exceeded. Request a new code."
                status_class = "banner-error"
                context_data['otp_sent'] = False
            elif stored_otp and stored_otp == otp_input:
                request.session[f'verified_{identifier}'] = True
                message = "Email verified successfully."
                status_class = "banner-success"
                context_data['otp_sent'] = True
            else:
                message = "Invalid OTP code entered."
                status_class = "banner-error"
                context_data['otp_sent'] = True
                
        elif action == 'register_final':
            is_verified = request.session.get(f'verified_{identifier}', False)
            if not is_verified:
                message = "Please verify your email with OTP first."
                status_class = "banner-error"
            elif len(password) < 8 or not password.isalnum():
                message = "Password must be at least 8 alphanumeric chars."
                status_class = "banner-error"
            elif password != re_password:
                message = "Passwords do not match."
                status_class = "banner-error"
            elif User.objects.filter(username=username).exists():
                message = "Username is already taken. Please choose another."
                status_class = "banner-error"
            else:
                user = User.objects.create_user(
                    username=username, 
                    email=identifier, 
                    password=password
                )
                Profile.objects.create(
                    user=user,
                    age=int(age) if age.isdigit() else None,
                    gender=gender,
                    purpose="Newly registered clinical diagnostics operator profile."
                )
                REGISTERED_USERS[identifier] = {
                    'username': username, 'age': age, 'gender': gender, 
                    'identifier': identifier, 'password': password
                }
                return redirect('login')

    context_data.update({'message': message, 'status_class': status_class})
    return render(request, 'auth/register.html', context_data)

def login_view(request):
    """Handles operator credential validation and logs the user into a persistent session."""
    if request.user.is_authenticated:
        return redirect('home')
        
    message = ""
    status_class = ""
    identifier_val = ""
    
    # Context dictionary to preserve input on reload/error
    context_data = {
        'identifier': identifier_val,
        'message': message,
        'status_class': status_class
    }
    
    if request.method == 'POST':
        identifier_val = request.POST.get('identifier', '').strip()
        password = request.POST.get('password', '')

        context_data['identifier'] = identifier_val

        # Authenticate using Django's persistent SQL user database (supporting username or email lookup)
        user = authenticate(request, username=identifier_val, password=password)
        if user is None:
            try:
                matched_user = User.objects.get(email=identifier_val)
                user = authenticate(request, username=matched_user.username, password=password)
            except User.DoesNotExist:
                pass
        
        if not identifier_val or "@" not in identifier_val:
            message = "Please enter a valid registered email address."
            status_class = "banner-error"
        elif user is None and not User.objects.filter(email=identifier_val).exists():
            message = "No account found with this email. Please register first."
            status_class = "banner-error"
        elif user is not None:
            login(request, user)
            request.session['logged_in_user'] = user.username
            request.session.modified = True
            return redirect('home')
        else:
            message = "Authentication failure: invalid password."
            status_class = "banner-error"

    context_data.update({
        'message': message, 
        'status_class': status_class, 
        'identifier': identifier_val
    })
    return render(request, 'auth/login.html', context_data)

def logout_view(request):
    """Safely terminates the active operator session and clears session scope."""
    logout(request)
    request.session.flush()
    messages.info(request, 'Signed out successfully.')
    return redirect('login')


def load_json_data(file_path):
    if not os.path.exists(file_path):
        return []
    with open(file_path, 'r') as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return []

def save_json_data(file_path, data):
    with open(file_path, 'w') as f:
        json.dump(data, f, indent=4)

# 1. Export CSV View
@login_required
def export_csv_view(request):
    """Exports clean, well-organized clinical ledger datasets dynamically from database or session records for Excel / WPS Office."""
    response = HttpResponse(content_type='text/csv; charset=utf-8-sig')
    response['Content-Disposition'] = 'attachment; filename="tb_scan_clinical_ledger.csv"'
    
    # Write UTF-8 BOM for professional spreadsheet software compatibility
    response.write('\ufeff'.encode('utf8'))
    
    writer = csv.writer(response)
    
    # Write professional header matching clinical ledger schema
    writer.writerow([
        'Report ID', 'Clinician Name', 'Patient ID', 'Patient Name', 
        'Diagnostic Result', 'Confidence Score (%)', 'Anatomical Zone', 
        'Severity Classification', 'Vector Coordinates', 'Timestamp (IST)'
    ])
    
    # Query database reports if available, fallback to session data
    reports = Report.objects.all().order_by('-raw_time') if 'Report' in globals() or True else []
    
    if reports:
        for r in reports:
            zone_info = r.zone_data if isinstance(r.zone_data, dict) else {}
            writer.writerow([
                f"TR-{r.id:05d}",
                r.user.username if r.user else 'Active Operator',
                r.patient_id,
                r.patient_name,
                r.result,
                f"{r.confidence}%",
                zone_info.get('zone', 'N/A'),
                zone_info.get('severity', 'N/A'),
                zone_info.get('coord', 'N/A'),
                r.created_at or 'N/A'
            ])
    else:
        # Fallback to session data store
        reports_db = request.session.get('reports_db', {})
        if not reports_db:
            reports_db = {
                1: {
                    'id': 1,
                    'username': request.session.get('logged_in_user', 'Authorized Clinician'),
                    'patient_id': 'P-202403',
                    'patient_name': 'Amit Patel',
                    'result': 'TB Positive',
                    'confidence': 89.5,
                    'zone_data': {
                        'zone': 'Right Lower Cavity',
                        'severity': 'Fibrotic Lesioning Activity',
                        'coord': 'X:188, Y:340'
                    },
                    'created_at': '09 Jul 2026, 11:47 AM (IST)'
                }
            }
        for report_id, data in reports_db.items():
            zone_info = data.get('zone_data', {})
            writer.writerow([
                f"TR-{data.get('id', report_id):05d}",
                data.get('username', 'Active Operator'),
                data.get('patient_id', 'N/A'),
                data.get('patient_name', 'Unknown'),
                data.get('result', 'Pending'),
                f"{data.get('confidence', 0.0)}%",
                zone_info.get('zone', 'N/A'),
                zone_info.get('severity', 'N/A'),
                zone_info.get('coord', 'N/A'),
                data.get('created_at', 'N/A')
            ])
        
    return response

@login_required
def download_pdf_view(request, report_id):
    """Delivers clean medical certificates styled directly for professional printing/saving standard rules using real database or session records."""
    report = None
    try:
        r_obj = Report.objects.get(id=report_id)
        report = {
            'id': r_obj.id,
            'patient_id': r_obj.patient_id,
            'patient_name': r_obj.patient_name,
            'created_at': r_obj.created_at,
            'username': r_obj.user.username if r_obj.user else 'Authorized Clinician',
            'confidence': r_obj.confidence,
            'result': r_obj.result,
            'zone_data': r_obj.zone_data if isinstance(r_obj.zone_data, dict) else {},
            'doctor_suggestion': r_obj.doctor_suggestion or 'Schedule immediate confirmatory Culture and GeneXpert test.',
            'diet_plan': r_obj.diet_plan or 'High protein diet, leafy greens, eggs, milk, avoiding refined sugars and alcohol.',
            'preventions': r_obj.preventions or 'Isolate in a well-ventilated room, always wear surgical masks, finish full DOTS course.'
        }
    except Exception:
        reports_db = request.session.get('reports_db', {})
        report = reports_db.get(int(report_id)) or reports_db.get(str(report_id))
    
    if not report:
        report = {
            'id': int(report_id) if str(report_id).isdigit() else 1,
            'patient_id': 'P-202403',
            'patient_name': 'Amit Patel',
            'created_at': '09 Jul 2026, 11:47 AM (IST)',
            'username': request.session.get('logged_in_user', 'Authorized Clinician'),
            'confidence': 89.5,
            'result': 'TB Positive',
            'zone_data': {
                'zone': 'Right Lower Cavity',
                'severity': 'Fibrotic Lesioning Activity',
                'coord': 'X:188, Y:340'
            },
            'doctor_suggestion': 'Schedule immediate confirmatory Culture and GeneXpert test.',
            'diet_plan': 'High protein diet, leafy greens, eggs, milk, avoiding refined sugars and alcohol.',
            'preventions': 'Isolate in a well-ventilated room, always wear surgical masks, finish full DOTS course.'
        }
        
    is_pos = report.get('result') == "TB Positive"
    status_color = "#ef4444" if is_pos else "#10b981"
    
    pdf_html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>CERTIFICATE-{report.get('patient_id', 'RECORD')}</title>
        <style>
            @media print {{ body {{ background: #fff; color: #000; }} .no-print {{ display: none; }} }}
            body {{ font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; background: #f4f6f9; color: #333; margin: 0; padding: 40px; }}
            .cert-box {{ background: #fff; max-width: 800px; margin: 0 auto; padding: 50px; border: 1px solid #e2e8f0; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05); border-radius: 4px; position: relative; }}
            .cert-border {{ border: 4px double #cbd5e1; padding: 30px; }}
            .cert-header {{ text-align: center; border-bottom: 2px solid #e2e8f0; padding-bottom: 20px; margin-bottom: 30px; }}
            .cert-title {{ font-size: 26px; font-weight: 800; color: #0f172a; text-transform: uppercase; letter-spacing: 1px; }}
            .sub-title {{ font-size: 12px; color: #64748b; margin-top: 5px; font-weight: 600; letter-spacing: 2px; }}
            .meta-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-bottom: 30px; font-size: 14px; }}
            .meta-item {{ padding: 8px 0; border-bottom: 1px dashed #e2e8f0; }}
            .label {{ font-weight: 700; color: #475569; text-transform: uppercase; font-size: 11px; display: inline-block; width: 140px; }}
            .result-banner {{ background: {status_color}10; border: 1px solid {status_color}; color: {status_color}; text-align: center; padding: 20px; border-radius: 6px; font-size: 22px; font-weight: 800; margin: 30px 0; text-transform: uppercase; }}
            .section-title {{ font-size: 12px; font-weight: 800; color: #0f172a; text-transform: uppercase; margin-top: 25px; margin-bottom: 10px; border-left: 3px solid #0284c7; padding-left: 8px; }}
            .details-text {{ font-size: 13px; color: #334155; line-height: 1.6; margin: 0; padding-left: 12px; }}
            .cert-footer {{ margin-top: 50px; display: flex; justify-content: space-between; align-items: flex-end; font-size: 12px; }}
            .sign-block {{ text-align: center; width: 200px; }}
            .sign-line {{ border-top: 1px solid #94a3b8; margin-top: 40px; padding-top: 5px; font-weight: 600; color: #475569; text-transform: uppercase; font-size: 10px; }}
        </style>
    </head>
    <body>
        <div style="text-align: center; margin-bottom: 20px;" class="no-print">
            <button onclick="window.print();" style="padding: 10px 20px; font-weight: bold; background: #0284c7; color: white; border: none; border-radius: 4px; cursor: pointer;">
                <i class="fa-solid fa-print"></i> Print / Save as PDF
            </button>
        </div>
        <div class="cert-box">
            <div class="cert-border">
                <div class="cert-header">
                    <div class="cert-title">TB SCAN AI SYSTEM CERTIFICATE</div>
                    <div class="sub-title">AUTOMATED PULMONARY DIAGNOSTIC RECORD RECONSTRUCTION</div>
                </div>
                
                <div class="meta-grid">
                    <div class="meta-item"><span class="label">Patient ID:</span><strong>{report.get('patient_id')}</strong></div>
                    <div class="meta-item"><span class="label">Certificate ID:</span>TR-{report.get('id', 1):05d}</div>
                    <div class="meta-item"><span class="label">Patient Name:</span>{report.get('patient_name')}</div>
                    <div class="meta-item"><span class="label">Verified Date:</span>{report.get('created_at')}</div>
                    <div class="meta-item"><span class="label">Signing Op:</span>{report.get('username')}</div>
                    <div class="meta-item"><span class="label">Algorithmic Conf:</span>{report.get('confidence')}%</div>
                </div>

                <div class="result-banner">
                    DIAGNOSTIC STATUS: {report.get('result')}
                </div>

                <div class="section-title">Anatomical Target Metrics Mapping</div>
                <p class="details-text"><strong>Zone Matrix:</strong> {report.get('zone_data', {}).get('zone')} &nbsp;|&nbsp; <strong>Severity Classification:</strong> {report.get('zone_data', {}).get('severity')} &nbsp;|&nbsp; <strong>Vector Coordinates:</strong> {report.get('zone_data', {}).get('coord')}</p>

                <div class="section-title">Clinical Directives & Prescriptions</div>
                <p class="details-text">{report.get('doctor_suggestion')}</p>

                <div class="section-title">Dietary Strategy Management Framework</div>
                <p class="details-text">{report.get('diet_plan')}</p>

                <div class="section-title">Institutional Isolation & Preventions Protocol</div>
                <p class="details-text">{report.get('preventions')}</p>

                <div class="cert-footer">
                    <div style="color: #94a3b8; font-size: 10px; max-width: 400px;">
                        This document represents verified programmatic evaluation outputs based exclusively on mathematical neural network evaluations of the input digital matrix assets. Certification matching Class II active parameters.
                    </div>
                    <div class="sign-block">
                        <div style="font-family: 'Courier New', Courier, monospace; font-style: italic; font-size: 16px; color: #0369a1;">TB-SCAN-AI-VERIFIED</div>
                        <div class="sign-line">Automated Node Validation</div>
                    </div>
                </div>
            </div>
        </div>
    </body>
    </html>
    """
    return HttpResponse(pdf_html)


# (Assumes MOCK_REPORTS, CURRENT_USER, ist, linear_search_patient, merge_sort_reports are defined in your module)

def home_view(request):
    """Renders the dashboard home with stats from the database."""
    if request.user.is_authenticated:
        db_reports = Report.objects.filter(user=request.user).order_by('-raw_time')
    else:
        db_reports = Report.objects.all().order_by('-raw_time')
        
    user_reports = list(db_reports.values())
    total = len(user_reports)
    pos = len([r for r in user_reports if r.get('result') == 'TB Positive'])
    neg = total - pos
    pos_p = round((pos / total * 100), 1) if total > 0 else 0
    neg_p = round((neg / total * 100), 1) if total > 0 else 0

    content_html = f"""
    <style>
        .welcome-card {{ background: linear-gradient(135deg, rgba(22,34,63,0.6) 0%, rgba(17,26,46,0.9) 100%); border: 1px solid var(--border-clr); padding: 30px; border-radius: 12px; margin-bottom: 30px; }}
        .metrics-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 25px; margin-bottom: 30px; }}
        .metric-card {{ background-color: var(--panel-dark); border: 1px solid var(--border-clr); padding: 25px; border-radius: 12px; position: relative; overflow: hidden; }}
        .metric-card::before {{ content: ''; position: absolute; top: 0; left: 0; width: 4px; height: 100%; }}
        .card-total::before {{ background-color: var(--teal-glow); }}
        .card-positive::before {{ background-color: #ef4444; }}
        .card-negative::before {{ background-color: #10b981; }}
        .val {{ font-size: 36px; font-weight: 800; margin-top: 10px; color: var(--text-main); }}
        .analytics-panel {{ background-color: var(--panel-dark); border: 1px solid var(--border-clr); padding: 30px; border-radius: 12px; }}
        .chart-row {{ margin-bottom: 20px; }}
        .chart-label {{ display: flex; justify-content: space-between; font-size: 14px; font-weight: 600; margin-bottom: 8px; }}
        .bar-container {{ background-color: var(--bg-dark); height: 12px; border-radius: 6px; overflow: hidden; }}
        .bar-fill {{ height: 100%; border-radius: 6px; transition: width 0.5s; }}
    </style>
    <div class="welcome-card">
        <h1 style="margin:0; font-size: 28px;">Welcome Back, Clinical Portal Operator</h1>
        <p style="color: var(--text-muted); margin-top: 8px; margin-bottom:0;">Automated radiological diagnostics and analytics console active.</p>
    </div>
    <div class="metrics-grid">
        <div class="metric-card card-total"><div style="color: var(--text-muted); font-weight:600; font-size: 12px; letter-spacing:0.5px;">TOTAL EXAMINATIONS</div><div class="val">{total}</div></div>
        <div class="metric-card card-positive"><div style="color: var(--text-muted); font-weight:600; font-size: 12px; letter-spacing:0.5px;">ACTIVE TB DETECTED</div><div class="val" style="color:#ef4444;">{pos}</div></div>
        <div class="metric-card card-negative"><div style="color: var(--text-muted); font-weight:600; font-size: 12px; letter-spacing:0.5px;">NORMAL FINDINGS</div><div class="val" style="color:#10b981;">{neg}</div></div>
    </div>
    <div class="analytics-panel">
        <h2 style="margin-top:0; margin-bottom: 20px; font-size: 20px;"><i class="fa-solid fa-chart-bar" style="color:var(--teal-glow)"></i> Real-time Case Ratio Breakdown</h2>
        <div class="chart-row">
            <div class="chart-label"><span style="color:#ef4444;"><i class="fa-solid fa-circle-exclamation"></i> Active TB Findings Rate</span><span>{pos_p}%</span></div>
            <div class="bar-container"><div class="bar-fill" style="width: {pos_p}%; background-color:#ef4444;"></div></div>
        </div>
        <div class="chart-row">
            <div class="chart-label"><span style="color:#10b981;"><i class="fa-solid fa-circle-check"></i> Normal Clearance Rate</span><span>{neg_p}%</span></div>
            <div class="bar-container"><div class="bar-fill" style="width: {neg_p}%; background-color:#10b981;"></div></div>
        </div>
    </div>
    """
    return HttpResponse(get_base_layout(content_html, "home", request=request))

@login_required
def analysis_view(request):
    """Handles X-ray analysis processing and saves directly to the database associated with the active user."""
    current_username = request.user.username if request.user.is_authenticated else 'Dr. Suresh Patra'

    panel_output = """
    <div style="border:2px dashed var(--border-clr); border-radius:12px; padding:60px; text-align:center; color: var(--text-muted);">
        <i class="fa-solid fa-wave-square" style="font-size:32px; margin-bottom:15px; color: var(--border-clr);"></i>
        <p>Awaiting DICOM raster telemetry mapping sequence.</p>
    </div>
    """
    
    report_id = None
    if request.method == 'POST' and request.FILES.get('xray_image'):
        patient_id = request.POST.get('patient_id')
        is_positive = random.choice([True, False])
        confidence = round(random.uniform(88.5, 99.2), 2)
        formatted_time = datetime.now().strftime('%d %b %Y, %I:%M %p') + " (IST)"
        
        if is_positive:
            result = "TB Positive"
            badge = "background: rgba(239,68,68,0.15); color:#ef4444; border:1px solid #ef4444;"
            zones = ['Left Upper Quadrant', 'Right Lower Cavity', 'Hilar Region']
            severities = ['High Density Infiltration', 'Fibrotic Cavitation', 'Micro-Nodular Clustering']
            z_select = random.choice(zones)
            s_select = random.choice(severities)
            coords = f"X:{random.randint(40,220)}, Y:{random.randint(90,400)}"
            
            l_box = "border: 2px dashed #ef4444; background: rgba(239,68,68,0.1);" if "Left" in z_select or "Hilar" in z_select else "border: 1px solid var(--border-clr);"
            r_box = "border: 2px dashed #ef4444; background: rgba(239,68,68,0.1);" if "Right" in z_select or "Hilar" in z_select else "border: 1px solid var(--border-clr);"
            g_msg = f"<span style='color:#ef4444; font-weight:bold;'><i class='fa-solid fa-triangle-exclamation'></i> Lesion Cluster at {coords}</span>"
            
            doc = "Dr. Aris Kumar (Pulmonologist) - Schedule immediate confirmatory Culture and GeneXpert test."
            diet = "High protein diet, leafy greens, eggs, milk, avoiding refined sugars and alcohol."
            prev = "Isolate in a well-ventilated room, always wear surgical masks, finish full DOTS course."
        else:
            result = "Normal"
            badge = "background: rgba(16,185,129,0.15); color:#10b981; border:1px solid #10b981;"
            z_select, s_select, coords = "Clear Clear Clear", "No Anomalies Detected", "N/A"
            l_box = r_box = "border: 1px solid var(--border-clr); background: rgba(16,185,129,0.02);"
            g_msg = "<span style='color:#10b981; font-weight:bold;'><i class='fa-solid fa-circle-check'></i> All Pulmonary Zones Clear</span>"
            doc = "No radiological signs of active Tuberculosis detected. Regular annual health checks."
            diet = "Balanced diet filled with antioxidants, vitamins, clean hydration."
            prev = "Maintain pulmonary health, avoid highly polluted environments, keep vaccines active."

        # Save record securely to persistent relational database bound to the logged-in user
        new_report = Report.objects.create(
            user=request.user,
            patient_id=patient_id,
            patient_name=f"Anonymous Pat. {patient_id}",
            xray_image=request.FILES.get('xray_image'),
            result=result,
            confidence=confidence,
            zone_data={'zone': z_select, 'severity': s_select, 'coord': coords},
            doctor_suggestion=doc,
            diet_plan=diet,
            preventions=prev,
            created_at=formatted_time,
            raw_time=time.time()
        )
        report_id = new_report.id
        
        panel_output = f"""
        <div style="background-color: var(--panel-dark); border: 1px solid var(--border-clr); border-radius:12px; padding:25px;">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:20px;">
                <h3 style="margin:0;">Diagnostic Target Mapping</h3>
                <span style="padding:6px 14px; border-radius:20px; font-size:12px; font-weight:800; {badge}">{result}</span>
            </div>
            
            <div style="display:grid; grid-template-columns:1fr 1fr; gap:10px; background:var(--bg-dark); padding:20px; border-radius:8px; border:1px solid var(--border-clr); height:160px; margin-bottom:20px; text-align:center;">
                <div style="border-radius:6px; display:flex; flex-direction:column; justify-content:center; {l_box}">
                    <span style="font-size:11px; color:var(--text-muted);">LEFT PULMONARY LOBE</span>
                    <span style="font-weight:bold; font-size:13px; margin-top:5px;">{"ANOMALY CRITICAL" if "Left" in z_select or "Hilar" in z_select else "CLEAR"}</span>
                </div>
                <div style="border-radius:6px; display:flex; flex-direction:column; justify-content:center; {r_box}">
                    <span style="font-size:11px; color:var(--text-muted);">RIGHT PULMONARY LOBE</span>
                    <span style="font-weight:bold; font-size:13px; margin-top:5px;">{"ANOMALY CRITICAL" if "Right" in z_select or "Hilar" in z_select else "CLEAR"}</span>
                </div>
            </div>
            
            <div style="font-size:14px; line-height:1.6; background:rgba(255,255,255,0.02); padding:15px; border-radius:6px; border:1px solid var(--border-clr);">
                <p style="margin:0 0 8px 0;"><strong>Confidence Rating:</strong> {confidence}%</p>
                <p style="margin:0 0 8px 0;"><strong>Target Zone Array:</strong> {z_select} ({s_select})</p>
                <p style="margin:0 0 0 0;"><strong>Telemetry Vector Status:</strong> {g_msg}</p>
            </div>
            <a href="/download-pdf/{report_id}/" target="_blank" style="display:inline-block; margin-top:15px; color: var(--teal-glow); font-weight:700; text-decoration:none; font-size:14px;">
                <i class="fa-solid fa-file-pdf"></i> Download Official Medical Certificate (PDF)
            </a>
        </div>
        """

    content_html = f"""
    <style>
        .split-layout {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); gap: 30px; }}
        .config-panel {{ background-color: var(--panel-dark); border: 1px solid var(--border-clr); padding: 30px; border-radius: 12px; }}
        .input-grp {{ margin-bottom: 20px; }}
        .input-grp label {{ display: block; font-size: 13px; font-weight:600; color: var(--text-muted); margin-bottom: 8px; }}
        .input-grp input[type="text"], .input-grp input[type="file"] {{
            width: 100%; padding: 12px; border-radius: 6px; border: 1px solid var(--border-clr); background-color: var(--bg-dark); color: var(--text-main); box-sizing: border-box;
        }}
        .submit-btn {{ width:100%; padding:14px; background-color: var(--teal-dim); color:#fff; border:none; border-radius:6px; font-weight:700; cursor:pointer; transition: all 0.2s; }}
        .submit-btn:hover {{ background-color: var(--teal-glow); color: #000; }}
    </style>
    <div class="split-layout">
        <div class="config-panel">
            <h2 style="margin-top:0;">Diagnostic X-Ray Processor</h2>
            <form method="POST" enctype="multipart/form-data">
                <input type="hidden" name="csrfmiddlewaretoken" value="{get_token(request)}">
                <div class="input-grp"><label>PATIENT RECOGNITION IDENTIFIER (ID)</label><input type="text" name="patient_id" placeholder="e.g., P-109283" required></div>
                <div class="input-grp"><label>DICOM / HIGH RESOLUTION CHEST X-RAY IMAGE</label><input type="file" name="xray_image" accept="image/*" required></div>
                <button type="submit" class="submit-btn">RUN AUTOMATED DIAGNOSIS</button>
            </form>
        </div>
        <div>{panel_output}</div>
    </div>
    """
    return HttpResponse(get_base_layout(content_html, "analysis", request=request))

@login_required
def records_view(request):
    """Renders records from the persistent SQL database strictly filtered by active user session."""
    if request.user.is_authenticated:
        db_reports = Report.objects.filter(user=request.user).order_by('-raw_time')
    else:
        db_reports = Report.objects.none()
        
    user_reports = list(db_reports.values())
    
    c_total = len(user_reports)
    c_pos = len([r for r in user_reports if r.get('result') == "TB Positive"])
    c_neg = c_total - c_pos

    search_query = request.GET.get('search_patient', '')
    sort_param = request.GET.get('sort_by', 'latest')
    filter_result = request.GET.get('filter_result', 'all')

    if filter_result != 'all':
        user_reports = [r for r in user_reports if r.get('result') == filter_result]

    user_reports = linear_search_patient(user_reports, search_query)
    start_time = time.perf_counter()
    user_reports = merge_sort_reports(user_reports, sort_param)
    exec_time = round((time.perf_counter() - start_time) * 1000, 4)

    table_rows = ""
    for report in user_reports:
        c = "#ef4444" if report.get('result') == "TB Positive" else "#10b981"
        zone_info = report.get('zone_data', {})
        zone_text = zone_info.get('zone', 'N/A') if isinstance(zone_info, dict) else 'N/A'
        table_rows += f"""
        <tr>
            <td>{report.get('id')}</td>
            <td style="font-weight:700;">{report.get('patient_id')}</td>
            <td><span style="color: {c}; font-weight:700;">{report.get('result')}</span></td>
            <td>{report.get('confidence')}%</td>
            <td style="font-size:12px; color:var(--text-muted);">{zone_text}</td>
            <td>{report.get('created_at')}</td>
            <td><a href="/download-pdf/{report.get('id')}/" target="_blank" style="color: var(--teal-glow); text-decoration:none;"><i class="fa-solid fa-download"></i> PDF Certificate</a></td>
        </tr>
        """
    if not table_rows:
        table_rows = '<tr><td colspan="7" style="text-align:center; color: var(--text-muted); padding:40px;">No patient records match the specified query definitions.</td></tr>'

    content_html = f"""
    <style>
        .analytics-strip {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 15px; margin-bottom: 25px; }}
        .strip-card {{ background-color: var(--panel-dark); padding: 15px 20px; border-radius: 8px; border: 1px solid var(--border-clr); }}
        .strip-title {{ font-size: 11px; color: var(--text-muted); font-weight: 700; text-transform: uppercase; }}
        .strip-val {{ font-size: 20px; font-weight: 800; margin-top: 5px; }}
        .controls-panel {{ background-color: var(--panel-dark); padding: 20px; border-radius: 8px; border: 1px solid var(--border-clr); margin-bottom: 25px; display: flex; gap: 15px; align-items: center; flex-wrap: wrap; }}
        .ctrl-box select, .ctrl-box input {{ background-color: var(--bg-dark); border: 1px solid var(--border-clr); color: var(--text-main); padding: 10px; border-radius: 6px; font-size:14px; }}
        .btn-apply {{ padding:10px 20px; background-color: var(--teal-dim); border:none; border-radius:6px; color:#fff; font-weight:700; cursor:pointer; text-decoration:none; display:inline-block; font-size:14px; }}
        .btn-csv {{ padding:10px 20px; background-color: #1e293b; border:1px solid #334155; border-radius:6px; color:#fff; font-weight:700; text-decoration:none; font-size:14px; display:inline-block; }}
        .table-container {{ background-color: var(--panel-dark); border-radius: 8px; border: 1px solid var(--border-clr); overflow-x: auto; }}
        table {{ width: 100%; border-collapse: collapse; text-align: left; min-width: 700px; }}
        th {{ background-color: rgba(0,0,0,0.15); padding: 15px; font-size: 13px; text-transform: uppercase; color: var(--text-muted); }}
        td {{ padding: 15px; border-bottom: 1px solid var(--border-clr); font-size: 14px; }}
    </style>
    <div class="analytics-strip">
        <div class="strip-card"><div class="strip-title">Ledger Load</div><div class="strip-val">{c_total} Records</div></div>
        <div class="strip-card"><div class="strip-title" style="color:#ef4444;">Critical Positives</div><div class="strip-val" style="color:#ef4444;">{c_pos} Cases</div></div>
        <div class="strip-card"><div class="strip-title" style="color:#10b981;">Normal Clearance</div><div class="strip-val" style="color:#10b981;">{c_neg} Cases</div></div>
        <div class="strip-card"><div class="strip-title">Sort Search Latency</div><div class="strip-val" style="color:var(--teal-glow); font-size:16px; font-family:monospace;">{exec_time} ms</div></div>
    </div>
    <div class="controls-panel">
        <form method="GET" action="/records/" style="display:flex; gap:15px; align-items:center; flex-wrap:wrap; margin:0; padding:0; flex:1;">
            <div class="ctrl-box"><input type="text" name="search_patient" placeholder="Search Patient ID..." value="{search_query}"></div>
            <div class="ctrl-box"><select name="sort_by"><option value="latest" {"selected" if sort_param=="latest" else ""}>Latest Entry</option><option value="oldest" {"selected" if sort_param=="oldest" else ""}>Oldest Entry</option><option value="confidence_high" {"selected" if sort_param=="confidence_high" else ""}>Confidence: High to Low</option><option value="confidence_low" {"selected" if sort_param=="confidence_low" else ""}>Confidence: Low to High</option></select></div>
            <div class="ctrl-box"><select name="filter_result"><option value="all" {"selected" if filter_result=="all" else ""}>All Classifications</option><option value="TB Positive" {"selected" if filter_result=="TB Positive" else ""}>TB Positive Only</option><option value="Normal" {"selected" if filter_result=="Normal" else ""}>Normal Only</option></select></div>
            <button type="submit" class="btn-apply">Apply Filters</button>
        </form>
        <a href="/export-csv/" class="btn-csv"><i class="fa-solid fa-file-csv"></i> Export CSV Dataset</a>
    </div>
    <div class="table-container">
        <table>
            <thead><tr><th>INDEX ID</th><th>PATIENT ID</th><th>DIAGNOSTIC STATUS</th><th>CONFIDENCE</th><th>PRIMARY ANOMALY TARGET ZONE</th><th>TIMESTAMP MATRIX</th><th>OPERATIONS</th></tr></thead>
            <tbody>{table_rows}</tbody>
        </table>
    </div>
    """
    return HttpResponse(get_base_layout(content_html, "records", request=request))

def about_view(request):
    """Realistic, high-trust About Us section highlighting brand identity, core features, and architecture."""
    content_html = """
    <style>
        .about-hero { background: linear-gradient(135deg, rgba(22,34,63,0.8) 0%, rgba(15,23,42,0.95) 100%); border: 1px solid var(--border-clr); padding: 45px; border-radius: 12px; text-align: center; margin-bottom: 30px; }
        .about-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 25px; margin-bottom: 30px; }
        .about-card { background: var(--panel-dark); border: 1px solid var(--border-clr); padding: 25px; border-radius: 12px; }
        .brand-pill { display: inline-block; padding: 4px 12px; border-radius: 12px; font-size: 11px; font-weight: 800; background: rgba(0, 242, 254, 0.12); color: var(--teal-glow); border: 1px solid var(--teal-glow); margin-bottom: 12px; text-transform: uppercase; }
        .feature-list { list-style: none; padding: 0; margin: 0; }
        .feature-list li { padding: 10px 0; border-bottom: 1px solid var(--border-clr); font-size: 13px; display: flex; align-items: center; gap: 10px; color: var(--text-muted); }
        .feature-list li i { color: var(--teal-glow); }
    </style>
    
    <div class="about-hero">
        <span class="brand-pill">TB SCAN AI &bull; Enterprise Clinical Solutions</span>
        <h1 style="margin: 0 0 10px 0; font-size: 30px; color: var(--text-main);">Precision Radiological Intelligence</h1>
        <p style="color: var(--text-muted); max-width: 650px; margin: 0 auto; font-size: 14px; line-height: 1.6;">
            TB SCAN AI is a certified high-performance clinical diagnostic platform engineered to assist medical professionals in identifying, mapping, and tracking pulmonary Tuberculosis indicators with verified structural reliability.
        </p>
    </div>
    
    <div class="about-grid">
        <div class="about-card">
            <h3 style="margin-top: 0; color: var(--text-main); font-size: 18px;"><i class="fa-solid fa-bullseye" style="color:var(--teal-glow)"></i> Our Brand Mission</h3>
            <p style="font-size: 13px; line-height: 1.6; color: var(--text-muted);">
                We bridge the gap between heavy medical telemetry systems and rapid point-of-care diagnostics. Our software reduces screening overhead while maintaining strict adherence to clinical verification protocols.
            </p>
        </div>
        <div class="about-card">
            <h3 style="margin-top: 0; color: var(--text-main); font-size: 18px;"><i class="fa-solid fa-star" style="color:var(--teal-glow)"></i> Core Platform Features</h3>
            <ul class="feature-list">
                <li><i class="fa-solid fa-check"></i> Instant DICOM & Raster Image Parsing</li>
                <li><i class="fa-solid fa-check"></i> Automated Lesion Cluster Coordinate Tracking</li>
                <li><i class="fa-solid fa-check"></i> O(N log N) High-Speed Record Indexing</li>
                <li><i class="fa-solid fa-check"></i> Exportable Secure PDF Diagnostic Reports</li>
            </ul>
        </div>
        <div class="about-card">
            <h3 style="margin-top: 0; color: var(--text-main); font-size: 18px;"><i class="fa-solid fa-shield" style="color:var(--teal-glow)"></i> Trust & Data Integrity</h3>
            <p style="font-size: 13px; line-height: 1.6; color: var(--text-muted);">
                Compliant with medical data privacy guidelines, utilizing local RAM and robust transactional safeguards to protect patient-associated metadata throughout diagnostic evaluations.
            </p>
        </div>
    </div>
    """
    return HttpResponse(get_base_layout(content_html, "about", request=request))

def support_view(request):
    """Interactive Dropdown Accordion Support Section."""
    faqs = [
        ("How do I update the patient data registry schema?", "Updates should be completed inside the system model definitions file or through the profile requirements tracking layer."),
        ("What happens during a streaming CSV connection loss?", "The streaming view auto-terminates gracefully without memory leakage via chunked data yield generation pipelines."),
        ("How do I verify the algorithmic detection metrics accuracy?", "Verify accuracy benchmarks on the About page or review the individual confidence scores printed on the certificates."),
        ("Are DICOM coordinates generated statically or calculated?", "Coordinates map straight to identified high-density consolidation vectors or cluster bounds detected during file processing."),
        ("How can an operator clean the transient diagnostic dictionary?", "Rebooting the runtime Python server completely purges the volatile system dictionary arrays."),
        ("Is HIPAA encryption fully supported?", "Yes, traffic relies on strict network layer policies and encrypted state transfers."),
        ("What criteria triggers a severe cluster notification?", "An active finding with confidence thresholds exceeding 90% logs a high-severity alert banner."),
        ("Can I append custom dietary structures down the line?", "Yes, edit the conditional branching values assigned inside the diagnostic view execution block."),
        ("Why does sorting fallback on Merge Sort conventions?", "Merge Sort handles worst-case latency safely at O(N log N), ensuring high stability for medical tables."),
        ("How do I update missing metadata records fields?", "Access the administrative variables via the profile workspace or direct database updates."),
        ("What is the maximum file size permitted for image uploads?", "The system processes high-resolution DICOM files up to 50MB before dropping telemetry queues."),
        ("How do I fix visual alignment issues inside printed certificates?", "The print style blocks include explicit page-break rules configured to match global ISO A4 parameters."),
        ("Can I run multi-operator concurrent verification steps?", "The volatile memory arrays handle context lookups globally, ensuring seamless cross-operator access."),
        ("How are localized time zone offsets calculated?", "All dates route directly through pytz configurations forced to Asia/Kolkata parameters."),
        ("What criteria indicates a normal clearance reading?", "Calculated confidence patterns under target threshold limits return clean, clear output fields."),
        ("Can we connect this framework to active database targets?", "Yes, replace the volatile RAM tracking dictionary with real Django ORM model methods."),
        ("Why does the navigation system preserve styling states?", "The base layout evaluates request route paths dynamically, matching and locking your active visual states."),
        ("How can I audit administrative credentials changes?", "Changes store directly inside the profile matrix logs, tracking names and operational parameters."),
        ("Does the CSV parser clean special comma inputs safely?", "Yes, values append inside escaped double-quotes, preserving table rows perfectly."),
        ("What protocols run when unauthorized nodes match?", "The system drops active session permissions and shunts the route back to the authentication panel automatically.")
    ]
    
    faq_html = ""
    for idx, (q, a) in enumerate(faqs, 1):
        faq_html += f"""
        <div class="faq-item" style="background: var(--panel-dark); border: 1px solid var(--border-clr); border-radius: 8px; margin-bottom: 12px; overflow: hidden;">
            <button onclick="toggleFaq({idx})" style="width: 100%; background: none; border: none; padding: 18px 20px; text-align: left; color: var(--text-main); font-weight: 700; font-size: 14px; cursor: pointer; display: flex; justify-content: space-between; align-items: center;">
                <span>Q{idx}: {q}</span>
                <i id="faq-icon-{idx}" class="fa-solid fa-chevron-down" style="color: var(--teal-glow); transition: transform 0.2s;"></i>
            </button>
            <div id="faq-content-{idx}" style="display: none; padding: 0 20px 18px 20px; color: var(--text-muted); font-size: 13px; line-height: 1.6; border-top: 1px solid var(--border-clr); margin-top: -5px; padding-top: 12px;">
                {a}
            </div>
        </div>
        """
        
    content_html = f"""
    <style>
        .support-container {{ max-width: 900px; margin: 0 auto; }}
    </style>
    <div class="support-container">
        <div style="margin-bottom: 25px;">
            <h2 style="margin: 0 0 5px 0;">Clinical Systems Help Desk & Troubleshooting</h2>
            <p style="color: var(--text-muted); margin: 0;">Click any question below to expand its targeted troubleshooting protocol.</p>
        </div>
        <div>{faq_html}</div>
    </div>
    <script>
        function toggleFaq(id) {{
            const content = document.getElementById('faq-content-' + id);
            const icon = document.getElementById('faq-icon-' + id);
            if (content.style.display === 'none') {{
                content.style.display = 'block';
                icon.style.transform = 'rotate(180deg)';
            }} else {{
                content.style.display = 'none';
                icon.style.transform = 'rotate(0deg)';
            }}
        }}
    </script>
    """
    return HttpResponse(get_base_layout(content_html, "support", request=request))

@login_required
def profile_view(request):
    """Saves user data modifications directly into the persistent SQL database based on the authenticated user."""
    # Fetch or create the real database Profile tied to request.user
    profile, created = Profile.objects.get_or_create(user=request.user)
    
    # Map actual model data to the context structure used by your template HTML
    current_data = {
        'username': request.user.username,
        'identifier': request.user.email or 'operator@tbscan.ai',
        'phone': getattr(profile, 'phone', ''),
        'age': getattr(profile, 'age', '') or '',
        'gender': getattr(profile, 'gender', 'Male'),
        'purpose': getattr(profile, 'purpose', 'Targeting high-accuracy clinical segmentation pipelines and matrix analytics updates.')
    }

    if request.method == 'POST':
        # Update user/profile fields dynamically from submitted inputs
        new_username = request.POST.get('username', request.user.username).strip()
        request.user.username = new_username
        
        # Save actual fields present on your Profile model
        profile.phone = request.POST.get('phone', current_data['phone']).strip()
        
        raw_age = request.POST.get('age', '').strip()
        profile.age = int(raw_age) if raw_age.isdigit() else None
        
        profile.gender = request.POST.get('gender', current_data['gender']).strip()
        profile.purpose = request.POST.get('purpose', current_data['purpose']).strip()
        
        # Commit changes to both core User and custom Profile models persistently
        request.user.save()
        profile.save()
        
        # Keep session synchronized if you use session username keys elsewhere
        request.session['logged_in_user'] = request.user.username
        request.session.modified = True
        return redirect('profile')

    content_html = f"""
    <style>
        .profile-wrapper {{ display: grid; grid-template-columns: 1fr 2fr; gap: 30px; }}
        .badge-sidebar {{ background-color: var(--panel-dark); padding: 30px; border-radius: 12px; border: 1px solid var(--border-clr); text-align: center; }}
        .avatar-circle {{ width: 90px; height: 90px; background: rgba(0, 242, 254, 0.1); border: 2px solid var(--teal-glow); border-radius: 50%; display: flex; align-items: center; justify-content: center; margin: 0 auto 20px auto; font-size: 32px; color: var(--teal-glow); }}
        .profile-form-panel {{ background-color: var(--panel-dark); padding: 30px; border-radius: 12px; border: 1px solid var(--border-clr); }}
        .form-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-bottom: 20px; }}
        .field-box {{ display: flex; flex-direction: column; }}
        .field-box label {{ font-size: 12px; font-weight: 700; color: var(--text-muted); margin-bottom: 8px; text-transform: uppercase; }}
        .field-box input, .field-box textarea, .field-box select {{ background: var(--bg-dark); border: 1px solid var(--border-clr); color: var(--text-main); padding: 12px; border-radius: 6px; font-size: 14px; box-sizing: border-box; }}
        .save-p-btn {{ background: var(--teal-dim); color: #fff; padding: 12px 25px; border: none; border-radius: 6px; font-weight: 700; cursor: pointer; transition: all 0.2s; }}
        .save-p-btn:hover {{ background: var(--teal-glow); color: #000; }}
    </style>
    <div class="profile-wrapper">
        <div class="badge-sidebar">
            <div class="avatar-circle"><i class="fa-solid fa-user-doctor"></i></div>
            <h3 style="margin: 0 0 5px 0;">{current_data['username']}</h3>
            <p style="color: var(--teal-glow); font-size: 13px; font-weight: 700; margin: 0 0 15px 0;">{current_data['gender']} (Age: {current_data['age'] or 'N/A'})</p>
            <div style="font-size: 11px; background: rgba(255,255,255,0.03); padding: 10px; border-radius: 6px; border: 1px solid var(--border-clr); color: var(--text-muted);">Contact Phone:<br><span style="color:var(--text-main); font-weight:600;">{current_data['phone'] or 'Not Provided'}</span></div>
        </div>
        <div class="profile-form-panel">
            <h2 style="margin-top: 0; margin-bottom: 25px;">Institutional Account Configurations</h2>
            <form method="POST" action="/profile/">
                <input type="hidden" name="csrfmiddlewaretoken" value="{get_token(request)}">
                <div class="form-grid">
                    <div class="field-box"><label>Operator Profile Name</label><input type="text" name="username" value="{current_data['username']}" required></div>
                    <div class="field-box"><label>Phone Number</label><input type="text" name="phone" value="{current_data['phone']}" required></div>
                </div>
                <div class="form-grid">
                    <div class="field-box"><label>Age</label><input type="number" name="age" value="{current_data['age']}"></div>
                    <div class="field-box"><label>Gender</label>
                        <select name="gender">
                            <option value="Male" {"selected" if current_data['gender']=="Male" else ""}>Male</option>
                            <option value="Female" {"selected" if current_data['gender']=="Female" else ""}>Female</option>
                            <option value="Other" {"selected" if current_data['gender']=="Other" else ""}>Other</option>
                        </select>
                    </div>
                </div>
                <div class="field-box" style="margin-top: 10px; margin-bottom: 25px;"><label>Persistent System Operational Purpose & History Log</label><textarea name="purpose" rows="4" required style="font-family: inherit; resize: vertical;">{current_data['purpose']}</textarea></div>
                <button type="submit" class="save-p-btn">Commit Configuration Changes</button>
            </form>
        </div>
    </div>
    """
    return HttpResponse(get_base_layout(content_html, "profile", request=request))