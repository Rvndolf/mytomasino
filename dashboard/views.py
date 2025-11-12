
from urllib import request
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from tickets.models import TicketHistory
from django.db.models import Q
from user.models import UserProfile
from django.contrib import messages

@login_required(login_url='user:login')
def dashboard_home(request):
    context = {'user': request.user}

    if request.headers.get("HX-Request"):
        # Render only the partial content for HTMX
        return render(request, "dashboard/partials/home_partial.html", context)

    return render(request, "dashboard/home.html", context)


@login_required
def dashboard_history(request):
    history_entries = TicketHistory.objects.filter(
        Q(ticket__created_by=request.user) | Q(ticket__isnull=True)
    ).order_by('-timestamp')

    context = {
        'history_entries': history_entries
    }

    if request.headers.get("HX-Request"):
        return render(request, "dashboard/partials/history_partial.html", context)

    return render(request, "dashboard/history.html", context)


@login_required
def dashboard_settings(request):
    user = request.user
    profile = getattr(user, "profile", None)

    if not profile:
        profile = UserProfile.objects.create(user=user)

    if request.method == "POST":
        profile_picture = request.FILES.get("profile_picture")
        profile.id_number = request.POST.get("id_number") or profile.id_number
        profile.department = request.POST.get("department") or profile.department
        profile.contact_number = request.POST.get("contact_number") or profile.contact_number
        profile.address = request.POST.get("address") or profile.address
        if profile_picture:
            profile.profile_picture = profile_picture

        profile.email_notifications = bool(request.POST.get("email_notifications"))
        profile.sms_notifications = bool(request.POST.get("sms_notifications"))
        profile.language_preference = request.POST.get("language_preference") or profile.language_preference
        profile.region = request.POST.get("region") or profile.region
        profile.date_format = request.POST.get("date_format") or profile.date_format
        profile.number_format = request.POST.get("number_format") or profile.number_format

        try:
            profile.full_clean()
            profile.save()
            messages.success(request, "Settings updated successfully!")
        except Exception as e:
            messages.error(request, f"Error saving profile: {e}")

        return redirect("dashboard:settings")

    context = {"profile": profile}

    if request.headers.get("HX-Request"):
        return render(request, "dashboard/partials/settings_partial.html", context)

    return render(request, "dashboard/settings.html", context)


@login_required(login_url='user:login')
def tickets_view(request):
    context = {'user': request.user}

    if request.headers.get("HX-Request"):
        return render(request, "tickets/partials/ticket_overview_partial.html", context)

    return render(request, "tickets/ticket_overview.html", context)