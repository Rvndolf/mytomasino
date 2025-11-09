
from urllib import request
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from tickets.models import TicketHistory
from django.db.models import Q
from user.models import UserProfile
from django.contrib import messages

@login_required(login_url='user:login')  # redirects to login if not authenticated
def dashboard_home(request):
    user = request.user
    return render(request, 'dashboard/home.html', {'user': user,})

@login_required
def dashboard_history(request):
    
    history_entries = TicketHistory.objects.filter(
        Q(ticket__created_by=request.user) | Q(ticket__isnull=True)
    ).order_by('-timestamp')

    context = {
        'history_entries': history_entries
    }
    return render(request, 'dashboard/history.html', context)

@login_required
def dashboard_settings(request):
    user = request.user
    profile = getattr(user, "profile", None)

    if not profile:
        from user.models import UserProfile
        profile = UserProfile.objects.create(user=user)

    if request.method == "POST":
        profile_picture = request.FILES.get("profile_picture")
        id_number = request.POST.get("id_number")
        department = request.POST.get("department")
        contact_number = request.POST.get("contact_number")
        address = request.POST.get("address")
        profile.id_number = id_number or profile.id_number
        profile.department = department or profile.department
        profile.contact_number = contact_number or profile.contact_number
        profile.address = address or profile.address

        if profile_picture:
            profile.profile_picture = profile_picture

        profile.email_notifications = bool(request.POST.get("email_notifications"))
        profile.sms_notifications = bool(request.POST.get("sms_notifications"))
        profile.language_preference = request.POST.get("language_preference") or profile.language_preference
        profile.region = request.POST.get("region") or profile.region
        profile.date_format = request.POST.get("date_format") or profile.date_format
        profile.number_format = request.POST.get("number_format") or profile.number_format

        try:
            profile.full_clean()  # This runs all validators (like regex)
            profile.save()
            messages.success(request, "Settings updated successfully!")
        except Exception as e:
            messages.error(request, f"Error saving profile: {e}")

        return redirect("dashboard:settings")

    context = {
        "profile": profile,
    }
    return render(request, "dashboard/settings.html", context)

@login_required
def user_settings(request):
    user = request.user

    if request.method == 'POST':

        if "current_password" in request.POST:
            current_password = request.POST.get("current_password")
            new_password1 = request.POST.get("new_password1")
            new_password2 = request.POST.get("new_password2")

            if not user.check_password(current_password):
                messages.error(request, "Current password is incorrect.")
            elif new_password1 != new_password2:
                messages.error(request, "New passwords do not match.")
            else:
                user.set_password(new_password1)
                user.save()
                update_session_auth_hash(request, user)
                messages.success(request, "Password updated successfully.")
                
            return redirect("dashboard_settings")
        
        if 'id_number' in request.POST:
            user.id_number = request.POST.get('id_number', '').strip()
            user.department = request.POST.get('department', '').strip()
            user.contact_number = request.POST.get('contact_number', '').strip()
            user.address = request.POST.get('address', '').strip()

            if 'profile_picture' in request.FILES:
                user.profile_picture = request.FILES['profile_picture']

            user.save()
            messages.success(request, "Your profile information has been updated successfully.")
            return redirect('dashboard:settings')

        elif 'language_preference' in request.POST:
            user.email_notifications = 'email_notifications' in request.POST
            user.sms_notifications = 'sms_notifications' in request.POST
            user.language_preference = request.POST.get('language_preference', 'en')
            user.region = request.POST.get('region', 'asia-ph')
            user.date_format = request.POST.get('date_format', 'MM/DD/YYYY')
            user.number_format = request.POST.get('number_format', '1,000.00')

            user.save()
            messages.success(request, "Your preferences have been saved successfully.")
            return redirect('dashboard:settings')

    return render(request, 'dashboard/settings.html')

@login_required(login_url='user:login')
def tickets_view(request):
    user = request.user
    return render(request, 'tickets/tickets_overview.html', {'user': user,})