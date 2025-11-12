from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from .models import Ticket, TicketHistory
from .forms import TicketForm
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from .models import Ticket, TicketHistory
from .forms import TicketForm
from .utils import assign_office_and_staff
from admin_panel.utils import send_ticket_status_email

@login_required
def ticket_list(request):
    tickets = Ticket.objects.filter(created_by=request.user).order_by('-created_at')

    context = {
        'open_tickets': tickets.filter(status='open'),
        'in_progress_tickets': tickets.filter(status='in_progress'),
        'completed_tickets': tickets.filter(status='completed'),
    }

    if request.headers.get('HX-Request'):  # HTMX request
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
    if request.method == 'POST':
        form = TicketForm(request.POST)
        if form.is_valid():
            ticket = form.save(commit=False)
            ticket.created_by = request.user
            ticket.save()
            assign_office_and_staff(ticket)
            TicketHistory.objects.create(ticket=ticket, action="Ticket created by user")

            if request.headers.get('HX-Request'):
                # Redirect HTMX request to ticket overview
                return render(request, "tickets/partials/ticket_overview_partial.html", {
                    'open_tickets': Ticket.objects.filter(created_by=request.user, status='open'),
                    'in_progress_tickets': Ticket.objects.filter(created_by=request.user, status='in_progress'),
                    'completed_tickets': Ticket.objects.filter(created_by=request.user, status='completed'),
                }, status=200)

            return redirect('tickets:ticket_overview')
    else:
        form = TicketForm()

    template = "tickets/partials/create_ticket_partial.html" if request.headers.get('HX-Request') else "tickets/create_ticket.html"
    return render(request, template, {'form': form})



@login_required
def update_ticket(request, pk):
    ticket = get_object_or_404(Ticket, pk=pk, created_by=request.user)
    if request.method == 'POST':
        form = TicketForm(request.POST, instance=ticket)
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
        form = TicketForm(instance=ticket)

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
        # Return updated ticket overview partial
        tickets = Ticket.objects.filter(created_by=request.user).order_by('-created_at')
        context = {
            'open_tickets': tickets.filter(status='open'),
            'in_progress_tickets': tickets.filter(status='in_progress'),
            'completed_tickets': tickets.filter(status='completed'),
        }
        return render(request, 'tickets/partials/ticket_overview_partial.html', context)

    return redirect('tickets:ticket_overview')