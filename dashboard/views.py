
from urllib import request
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from tickets.models import TicketHistory, Notification
from django.db.models import Q
from user.models import UserProfile
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib.auth import update_session_auth_hash
from django.core.exceptions import ValidationError
from django.contrib.auth.password_validation import validate_password

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
    profile, created = UserProfile.objects.get_or_create(user=user)

    if request.method == "POST":
        form_type = request.POST.get("form_type")

        if form_type == "profile":
            try:
                # Update profile fields
                profile.id_number = request.POST.get("id_number", "").strip() or None
                profile.department = request.POST.get("department", "").strip() or None
                profile.contact_number = request.POST.get("contact_number", "").strip() or None
                profile.address = request.POST.get("address", "").strip() or None

                # Handle profile picture upload
                if "profile_picture" in request.FILES:
                    profile_picture = request.FILES["profile_picture"]
                    # Optional: Delete old profile picture
                    if profile.profile_picture:
                        profile.profile_picture.delete(save=False)
                    profile.profile_picture = profile_picture

                profile.full_clean()
                profile.save()
                messages.success(request, "Profile updated successfully!")
            except ValidationError as e:
                error_messages = []
                for field, errors in e.message_dict.items():
                    error_messages.extend(errors)
                messages.error(request, " ".join(error_messages))
            except Exception as e:
                messages.error(request, f"Error saving profile: {str(e)}")

        elif form_type == "preferences":
            try:
                # Handle checkbox fields properly
                profile.email_notifications = "email_notifications" in request.POST
                profile.sms_notifications = "sms_notifications" in request.POST
                profile.language_preference = request.POST.get("language_preference", profile.language_preference)
                profile.region = request.POST.get("region", profile.region)
                profile.date_format = request.POST.get("date_format", profile.date_format)
                profile.number_format = request.POST.get("number_format", profile.number_format)

                profile.full_clean()
                profile.save()
                messages.success(request, "Preferences updated successfully!")
            except ValidationError as e:
                error_messages = []
                for field, errors in e.message_dict.items():
                    error_messages.extend(errors)
                messages.error(request, " ".join(error_messages))
            except Exception as e:
                messages.error(request, f"Error saving preferences: {str(e)}")

        elif form_type == "security":
            # Security tab: password change
            current_password = request.POST.get("current_password", "")
            new_password1 = request.POST.get("new_password1", "")
            new_password2 = request.POST.get("new_password2", "")

            if not current_password or not new_password1 or not new_password2:
                messages.error(request, "All password fields are required.")
            elif not user.check_password(current_password):
                messages.error(request, "Current password is incorrect.")
            elif new_password1 != new_password2:
                messages.error(request, "New passwords do not match.")
            else:
                try:
                    # Validate password against Django's validators
                    validate_password(new_password1, user)
                    user.set_password(new_password1)
                    user.save()
                    update_session_auth_hash(request, user)  # Keep user logged in
                    messages.success(request, "Password updated successfully!")
                except ValidationError as e:
                    messages.error(request, " ".join(e.messages))

        # For HTMX requests, return the settings page content
        if request.headers.get("HX-Request"):
            context = {
                "profile": profile,
                "user": user
            }
            return render(request, "dashboard/settings.html", context)
        
        # For regular requests, redirect
        return redirect("dashboard:settings")

    # GET request
    context = {
        "profile": profile,
        "user": user
    }

    return render(request, "dashboard/settings.html", context)

@login_required(login_url='user:login')
def tickets_view(request):
    context = {'user': request.user,}

    if request.headers.get("HX-Request"):
        return render(request, "tickets/partials/ticket_overview_partial.html", context)

    return render(request, "tickets/ticket_overview.html", context)

@login_required
@require_POST
def mark_notification_read(request, notification_id):
    """Mark a single notification as read"""
    try:
        notification = Notification.objects.get(
            id=notification_id,
            user=request.user
        )
        notification.is_read = True
        notification.save()
        return JsonResponse({'success': True})
    except Notification.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Notification not found'}, status=404)

@login_required
@require_POST
def mark_all_notifications_read(request):
    """Mark all notifications as read"""
    Notification.objects.filter(
        user=request.user,
        is_read=False
    ).update(is_read=True)
    
    return JsonResponse({'success': True})

@login_required
def notification_count(request):
    unread_count = Notification.objects.filter(
        user=request.user,
        is_read=False
    ).count()
    
    return JsonResponse({
        'unread_count': unread_count
    })

