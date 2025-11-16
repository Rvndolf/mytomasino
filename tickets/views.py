from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from .models import Ticket, TicketHistory, Notification
from django.utils import timezone 
from .forms import (
    TicketForm,
    TechnicalSupportForm,
    AcademicSupportForm,
    LostAndFoundForm,
    WelfareForm,
    FacilitiesForm
)
from .utils import assign_office_and_staff
from admin_panel.utils import send_ticket_status_email

FORM_MAP = {
    "technical": TechnicalSupportForm,
    "academic": AcademicSupportForm,
    "lostfound": LostAndFoundForm,
    "welfare": WelfareForm,
    "facilities": FacilitiesForm,
}

@login_required
def ticket_list(request):
    tickets = Ticket.objects.filter(created_by=request.user).order_by('-created_at')
    
    context = {
        'open_tickets': tickets.filter(status='open'),
        'in_progress_tickets': tickets.filter(status='in_progress'),
        'completed_tickets': tickets.filter(status='completed'),
    }

    if request.headers.get('HX-Request'):  
        return render(request, 'tickets/partials/ticket_overview_partial.html', context)

    return render(request, 'tickets/ticket_overview.html', context)

@login_required
def ticket_detail(request, pk):
    ticket = get_object_or_404(Ticket, pk=pk, created_by=request.user)
    
    ticket.last_viewed_by_user = timezone.now()
    ticket.save(update_fields=['last_viewed_by_user'])

    history = TicketHistory.objects.filter(ticket=ticket).order_by('-timestamp')
    admin_notes = history.filter(action__icontains='Note added by')
    ticket_history = history.exclude(action__icontains='Note added by')

    form = None
    if ticket.status != 'completed' and request.user == ticket.created_by:
        form = TicketForm(instance=ticket)

    context = {
        'ticket': ticket,
        'history': ticket_history,
        'admin_notes': admin_notes,
        'form': form,
    }

    template = 'tickets/partials/ticket_detail_partial.html' if request.headers.get('HX-Request') else 'tickets/ticket_detail.html'
    return render(request, template, context)

@login_required
def create_ticket(request):

    DEFAULT_CATEGORY = "technical"

    if request.method == "POST":
        category = request.POST.get("category", DEFAULT_CATEGORY)
    else:  
        category = request.GET.get("category", DEFAULT_CATEGORY)

    form_class = FORM_MAP.get(category, TicketForm)

    if request.method == "POST":
        form = form_class(request.POST, request.FILES)
        if form.is_valid():
            ticket = form.save(commit=False)
            ticket.created_by = request.user
            ticket.category = category
            ticket.save()

            assign_office_and_staff(ticket)
            TicketHistory.objects.create(ticket=ticket, action="Ticket created by user")

            Notification.objects.create(
                user=request.user,
                ticket=ticket,
                notification_type='ticket_created',
                title='Ticket Created Successfully',
                message=f'Your {ticket.get_category_display()} ticket #{ticket.id} "{ticket.title}" has been successfully submitted and is being reviewed.'
            )

            if request.headers.get("HX-Request"):
                tickets = Ticket.objects.filter(created_by=request.user).order_by('-created_at')
                context = {
                    "open_tickets": tickets.filter(status='open'),
                    "in_progress_tickets": tickets.filter(status='in_progress'),
                    "completed_tickets": tickets.filter(status='completed'),
                }
                return render(request, "tickets/partials/ticket_overview_partial.html", context)
            
            return redirect("tickets:ticket_overview")
    else:
        form = form_class()

    if request.headers.get("HX-Request") and request.method == "GET" and "category" in request.GET:
        return render(
            request,
            "tickets/partials/forms/category_form_partial.html",
            {"form": form, "category": category}
        )
    
    if request.headers.get("HX-Request"):
        return render(
            request,
            "tickets/partials/create_ticket_partial.html",
            {"form": form, "category": category}
        )
    
    return render(
        request,
        "tickets/create_ticket.html",
        {"form": form, "category": category}
    )

@login_required
def update_ticket(request, pk):
    ticket = get_object_or_404(Ticket, pk=pk, created_by=request.user)

    # Select the right form class based on ticket category
    form_class = FORM_MAP.get(ticket.category, TicketForm)

    if request.method == "POST":
        # Bind POST data to the ticket instance
        form = form_class(request.POST, instance=ticket)
        if form.is_valid():
            updated_ticket = form.save()

            # Add history
            TicketHistory.objects.create(ticket=updated_ticket, action="Ticket updated by user")

            # Create notification
            Notification.objects.create(
                user=request.user,
                ticket=updated_ticket,
                notification_type='ticket_updated',
                title='Ticket Updated',
                message=f'You have successfully updated ticket #{updated_ticket.id} "{updated_ticket.title}".'
            )

            # HTMX: render updated ticket detail
            if request.headers.get('HX-Request'):
                history = TicketHistory.objects.filter(ticket=updated_ticket).order_by('-timestamp')
                admin_notes = history.filter(action__icontains='Note added by')
                ticket_history = history.exclude(action__icontains='Note added by')
                context = {
                    'ticket': updated_ticket,
                    'history': ticket_history,
                    'admin_notes': admin_notes,
                }
                return render(request, 'tickets/partials/ticket_detail_partial.html', context)

            return redirect('tickets:ticket_detail', pk=ticket.pk)

    else:
        # On GET, instantiate the form **with instance=ticket** to pre-fill current data
        form = form_class(instance=ticket)

    # Render HTMX partial for the update form
    template = 'tickets/partials/update_ticket_partial.html' if request.headers.get('HX-Request') else 'tickets/update_ticket.html'
    return render(request, template, {'form': form, 'ticket': ticket})

@login_required
def delete_ticket(request, pk):
    ticket = get_object_or_404(Ticket, pk=pk, created_by=request.user)

    if request.method == "POST":
        ticket_title = ticket.title
        ticket_id = ticket.id

        # Record history
        TicketHistory.objects.create(
            ticket=None,
            ticket_title=ticket_title,
            action="Ticket deleted by user"
        )

        # Create notification
        Notification.objects.create(
            user=request.user,
            ticket=None,
            notification_type='ticket_updated',
            title='Ticket Deleted',
            message=f'Ticket #{ticket_id} "{ticket_title}" has been deleted.'
        )

        # Delete ticket
        ticket.delete()

        if request.headers.get('HX-Request'):
            # Fetch updated ticket lists for dashboard
            tickets = Ticket.objects.filter(created_by=request.user).order_by('-created_at')
            context = {
                'open_tickets': tickets.filter(status='open'),
                'in_progress_tickets': tickets.filter(status='in_progress'),
                'completed_tickets': tickets.filter(status='completed'),
            }
            return render(request, 'tickets/partials/ticket_overview_partial.html', context)

        return redirect('tickets:ticket_overview')

    # GET → render delete confirmation partial
    return render(request, 'tickets/partials/delete_ticket_partial.html', {'ticket': ticket})
