from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver
from django.utils import timezone
from .models import Ticket, Notification, TicketHistory

@receiver(pre_save, sender=Ticket)
def ticket_status_changed(sender, instance, **kwargs):
    """Send notification when admin updates ticket status"""
    
    # Skip if this is a new ticket
    if instance.pk is None:
        return
    
    try:
        # Get the old ticket from database
        old_ticket = Ticket.objects.get(pk=instance.pk)
        
        # Check if status changed
        if old_ticket.status != instance.status:
            
            # Mark that admin updated the ticket
            instance.last_admin_update = timezone.now()
            
            # Ticket marked as completed
            if instance.status == 'completed':
                Notification.objects.create(
                    user=instance.created_by,
                    ticket=instance,
                    notification_type='ticket_completed',
                    title='Ticket Completed',
                    message=f'Your ticket #{instance.id} "{instance.title}" has been marked as completed. Please review the solution.'
                )
            
            # Ticket marked as in progress
            elif instance.status == 'in_progress' and old_ticket.status == 'open':
                assigned_to = instance.assigned_to.get_full_name() if instance.assigned_to else 'our team'
                Notification.objects.create(
                    user=instance.created_by,
                    ticket=instance,
                    notification_type='ticket_updated',
                    title='Ticket In Progress',
                    message=f'Your ticket #{instance.id} is now being processed by {assigned_to}.'
                )
            
            # Any other status change
            else:
                Notification.objects.create(
                    user=instance.created_by,
                    ticket=instance,
                    notification_type='ticket_updated',
                    title='Ticket Status Updated',
                    message=f'Your ticket #{instance.id} status has been updated to {instance.get_status_display()}.'
                )
        
        # Check if assigned staff changed
        elif old_ticket.assigned_to != instance.assigned_to and instance.assigned_to:
            instance.last_admin_update = timezone.now()
            Notification.objects.create(
                user=instance.created_by,
                ticket=instance,
                notification_type='ticket_assigned',
                title='Ticket Assigned',
                message=f'Your ticket #{instance.id} has been assigned to {instance.assigned_to.get_full_name()}.'
            )
    
    except Ticket.DoesNotExist:
        pass


@receiver(post_save, sender=TicketHistory)
def admin_note_added(sender, instance, created, **kwargs):
    """Update last_admin_update and create notification when admin adds a note"""
    if created and instance.ticket and 'Note added by' in instance.action:
        # Update ticket's last admin update timestamp
        instance.ticket.last_admin_update = timezone.now()
        instance.ticket.save(update_fields=['last_admin_update'])
        
        # Create notification for ticket owner
        if instance.ticket.created_by:
            Notification.objects.create(
                user=instance.ticket.created_by,
                ticket=instance.ticket,
                notification_type='ticket_response',
                title=f'New response on ticket: {instance.ticket.title}',
                message=f'An admin has responded to your ticket.'
            )