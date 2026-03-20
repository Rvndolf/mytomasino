from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone  # Add this import
from django.utils.timesince import timesince
from cloudinary.models import CloudinaryField
import cloudinary
import cloudinary.models

class Ticket(models.Model):
    CATEGORY_CHOICES = [
        ('academic', 'Academic and Enrollment Concerns'),
        ('technical', 'Technical / Account Support'),
        ('facilities', 'Facilities and Maintenance'),
        ('lostfound', 'Lost and Found'),
        ('welfare', 'Student Welfare and Counselling'),
        ('generalinquiry', 'General Inquiry'),
    ]

    STATUS_CHOICES = [
        ('open', 'Open'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
    ]

    URGENCY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
    ]

    title = models.CharField(max_length=200)
    description = models.TextField()
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES)
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='open')
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='tickets_created')
    assigned_to = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='tickets_assigned')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    metadata = models.JSONField(null=True, blank=True)
  
    urgency = models.CharField(max_length=10, choices=URGENCY_CHOICES, null=True, blank=True)
    attachment = CloudinaryField('image', null=True, blank=True)
    
    last_viewed_by_user = models.DateTimeField(null=True, blank=True)
    last_admin_update = models.DateTimeField(null=True, blank=True)
    
    def has_unread_admin_notes(self):
        """Check if there are admin notes the user hasn't seen"""
        if not self.last_admin_update:
            return False
        if not self.last_viewed_by_user:
            return True
        return self.last_admin_update > self.last_viewed_by_user
    
    def ticket_id(self):
        return f"TCKT-{self.pk:04d}"
    
    def __str__(self):
        return self.title


class TicketHistory(models.Model):
    ticket = models.ForeignKey(
        'Ticket',
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    ticket_title = models.CharField(max_length=255, null=True, blank=True)
    deleted_ticket_id = models.IntegerField(null=True, blank=True)  
    new_status = models.CharField(max_length=50, null=True, blank=True)  # NEW FIELD
    action = models.CharField(max_length=255)
    timestamp = models.DateTimeField(auto_now_add=True)
    attachment = cloudinary.models.CloudinaryField(
        resource_type='raw',
        null=True,
        blank=True
    )

    user = models.ForeignKey(
        'auth.User',  # or settings.AUTH_USER_MODEL
        on_delete=models.CASCADE,
        related_name='ticket_history',
        null=True,  # Allow null for migration
        blank=True
    )
    created_by = models.ForeignKey(
        'auth.User',
        on_delete=models.CASCADE,
        related_name='created_ticket_history',
        null=True,
        blank=True,
        help_text="Original creator of the ticket"
    )
    activity_type = models.CharField(
        max_length=20,
        choices=[
            ('created', 'Created'),
            ('updated', 'Updated'),
            ('status_change', 'Status Changed'),
            ('response', 'User Response'),
            ('deleted', 'Deleted'),
        ],
        default='updated',
        null=True,
        blank=True
    )

    def __str__(self):
        return f"{self.ticket_title or 'Deleted ticket'} - {self.action}"

class Notification(models.Model):
    NOTIFICATION_TYPES = [
        ('ticket_created', 'Ticket Created'),
        ('ticket_updated', 'Ticket Updated'),
        ('ticket_assigned', 'Ticket Assigned'),
        ('ticket_completed', 'Ticket Completed'),
        ('ticket_response', 'New Response'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    ticket = models.ForeignKey('Ticket', on_delete=models.CASCADE, null=True, blank=True)
    notification_type = models.CharField(max_length=20, choices=NOTIFICATION_TYPES)
    title = models.CharField(max_length=200)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username} - {self.title}"

    def time_ago(self):
        """Return human-readable time ago"""
        from django.utils.timesince import timesince
        return timesince(self.created_at).split(',')[0] + ' ago'


