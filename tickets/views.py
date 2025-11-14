from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from .models import Ticket, TicketHistory
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


# --------------------------
# MAP CATEGORY → FORM CLASS
# --------------------------
FORM_MAP = {
    "technical": TechnicalSupportForm,
    "academic": AcademicSupportForm,
    "lost_and_found": LostAndFoundForm,
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
    history = TicketHistory.objects.filter(ticket=ticket).order_by('-timestamp')

    context = {'ticket': ticket, 'history': history}

    if request.headers.get('HX-Request'):
        return render(request, 'tickets/partials/ticket_detail_partial.html', context)

    return render(request, 'tickets/ticket_detail.html', context)


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

    form_class = FORM_MAP.get(ticket.category, TicketForm)

    if request.method == 'POST':
        form = form_class(request.POST, instance=ticket)

        if form.is_valid():
            updated_ticket = form.save()
            TicketHistory.objects.create(ticket=updated_ticket, action="Ticket updated by user")

            if request.headers.get('HX-Request'):
                context = {
                    'ticket': updated_ticket,
                    'history': TicketHistory.objects.filter(ticket=updated_ticket).order_by('-timestamp')
                }
                return render(request, 'tickets/partials/ticket_detail_partial.html', context)

            return redirect('tickets:ticket_detail', pk=ticket.pk)

    else:
        form = form_class(instance=ticket)

    template = 'tickets/partials/update_ticket_partial.html' if request.headers.get('HX-Request') else 'tickets/update_ticket.html'
    return render(request, template, {'form': form, 'ticket': ticket})



@login_required
def delete_ticket(request, pk):
    ticket = get_object_or_404(Ticket, pk=pk, created_by=request.user)

    TicketHistory.objects.create(
        ticket=None,
        ticket_title=ticket.title,
        action="Ticket deleted by user"
    )

    ticket.delete()

    if request.headers.get('HX-Request'):
        tickets = Ticket.objects.filter(created_by=request.user).order_by('-created_at')
        context = {
            'open_tickets': tickets.filter(status='open'),
            'in_progress_tickets': tickets.filter(status='in_progress'),
            'completed_tickets': tickets.filter(status='completed'),
        }
        return render(request, 'tickets/partials/ticket_overview_partial.html', context)

    return redirect('tickets:ticket_overview')
