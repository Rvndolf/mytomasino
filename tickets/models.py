from django.db import models
from django.contrib.auth.models import User

from django.db import models
from django.contrib.auth.models import User

class Ticket(models.Model):
    CATEGORY_CHOICES = [
        ('academic', 'Academic and Enrollment Concerns'),
        ('technical', 'Technical / Account Support'),
        ('facilities', 'Facilities and Maintenance'),
        ('lostfound', 'Lost and Found'),
        ('welfare', 'Student Welfare and Counselling'),
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

  
    urgency = models.CharField(max_length=10, choices=URGENCY_CHOICES, null=True, blank=True)
    attachment = models.FileField(upload_to='ticket_attachments/', null=True, blank=True)

    def ticket_id(self):
        return f"TCKT-{self.pk:04d}"
    
    def __str__(self):
        return self.title


class TicketHistory(models.Model):
    ticket = models.ForeignKey(
        'Ticket',
        on_delete=models.SET_NULL,  # Set to NULL if ticket is deleted
        null=True,                  # Allow null for deleted tickets
        blank=True
    )
    ticket_title = models.CharField(max_length=255, null=True, blank=True)
    action = models.CharField(max_length=255)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.ticket_title or 'Deleted ticket'} - {self.action}"




