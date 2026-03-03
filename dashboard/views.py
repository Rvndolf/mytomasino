
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
from tickets.models import Ticket, TicketHistory
from django.db.models import Count



@login_required(login_url='user:login')
def dashboard_home(request):
    # Calculate ticket completion percentage
    completed_tickets = request.user.tickets_created.filter(status='completed').count()
    total_tickets = request.user.tickets_created.count()
    
    if total_tickets > 0:
        completion_percentage = round((completed_tickets / total_tickets) * 100)
    else:
        completion_percentage = 0
    
    # Get last 3 ticket histories for the user's tickets (including deleted ones)
    history_entries = TicketHistory.objects.filter(
        Q(ticket__created_by=request.user) | Q(ticket__isnull=True, created_by=request.user)  # ADD created_by filter
    ).order_by('-timestamp')[:3]
    
    # Get tickets count by category (including open, in_progress, and completed)
    category_counts = (
        Ticket.objects.filter(
            status__in=['open', 'in_progress', 'completed'], 
            created_by=request.user
        )
        .values('category')
        .annotate(count=Count('id'))
        .order_by('-count')
    )
    
    # Get display names for categories
    category_dict = dict(Ticket.CATEGORY_CHOICES)
    category_data = [
        {
            'category_display': category_dict.get(item['category'], item['category']),
            'count': item['count']
        }
        for item in category_counts
    ]
    
    context = {
        'user': request.user,
        'completion_percentage': completion_percentage,
        'history_entries': history_entries,
        'category_counts': category_data,
    }

    if request.headers.get("HX-Request"):
        # Render only the partial content for HTMX
        return render(request, "dashboard/partials/home_partial.html", context)

    # For full page load (refresh), render the base template
    return render(request, "dashboard_base.html", context)

@login_required
def dashboard_history(request):
       history_entries = TicketHistory.objects.filter(
           Q(ticket__created_by=request.user) | 
           Q(ticket__isnull=True, created_by=request.user)  # Show deleted tickets created by this user
       ).order_by('-timestamp')

       context = {
           'history_entries': history_entries
       }

       if request.headers.get("HX-Request"):
           return render(request, "dashboard/partials/history_partial.html", context)

       return render(request, "dashboard_base.html", context)

@login_required
def dashboard_settings(request):
    user = request.user
    profile, created = UserProfile.objects.get_or_create(user=user)
    active_tab = 'profile'  # default tab

    if request.method == "POST":
        form_type = request.POST.get("form_type")

        if form_type == "profile":
            active_tab = 'profile'
            try:
                profile.contact_number = request.POST.get("contact_number", "").strip() or None
                profile.address = request.POST.get("address", "").strip() or None

                if request.POST.get("reset_picture"):
                    if profile.profile_picture:
                        try:
                            import cloudinary.uploader
                            cloudinary.uploader.destroy(profile.profile_picture.public_id)
                        except Exception:
                            pass
                    profile.profile_picture = None
                    profile.save()
                    messages.success(request, "Profile picture reset to default!")

                elif "profile_picture" in request.FILES:
                    import cloudinary.uploader
                    if profile.profile_picture:
                        try:
                            cloudinary.uploader.destroy(profile.profile_picture.public_id)
                        except Exception:
                            pass

                    upload_result = cloudinary.uploader.upload(
                        request.FILES["profile_picture"],
                        folder="profile_pictures",
                        resource_type="image",
                    )
                    profile.profile_picture = upload_result["public_id"]
                    profile.save()
                    messages.success(request, "Profile updated successfully!")

                else:
                    # Only validate fields relevant to the profile form
                    profile.full_clean(exclude=[
                        'id_number', 'grade_level', 'section', 'profile_picture',
                        'email_notifications', 'sms_notifications', 'language_preference',
                        'region', 'date_format', 'number_format'
                    ])
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
            active_tab = 'preferences'
            try:
                profile.email_notifications = "email_notifications" in request.POST
                profile.sms_notifications = "sms_notifications" in request.POST
                profile.language_preference = request.POST.get("language_preference", profile.language_preference)
                profile.region = request.POST.get("region", profile.region)
                profile.date_format = request.POST.get("date_format", profile.date_format)
                profile.number_format = request.POST.get("number_format", profile.number_format)

                # Only validate fields relevant to the preferences form
                profile.full_clean(exclude=[
                    'id_number', 'grade_level', 'section', 'profile_picture',
                    'contact_number', 'address'
                ])
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
            active_tab = 'security'
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
                    validate_password(new_password1, user)
                    user.set_password(new_password1)
                    user.save()
                    update_session_auth_hash(request, user)
                    messages.success(request, "Password updated successfully!")
                except ValidationError as e:
                    for error in e.messages:
                        messages.error(request, error)

        if request.headers.get("HX-Request"):
            context = {
                "profile": profile,
                "user": user,
                "active_tab": active_tab
            }
            return render(request, "dashboard/settings.html", context)

        return redirect("dashboard:settings")

    # GET request
    context = {
        "profile": profile,
        "user": user,
        "active_tab": active_tab
    }

    if request.headers.get("HX-Request"):
        return render(request, "dashboard/settings.html", context)

    return render(request, "dashboard_base.html", context)


@login_required(login_url='user:login')
def tickets_view(request):
    context = {'user': request.user}

    if request.headers.get("HX-Request"):
        return render(request, "tickets/partials/ticket_overview_partial.html", context)

    # For full page load (refresh), render the base template
    return render(request, "dashboard_base.html", context)


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

