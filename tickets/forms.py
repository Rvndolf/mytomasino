from django import forms
from .models import Ticket

class TicketForm(forms.ModelForm):
    class Meta:
        model = Ticket
        fields = ['title', 'description', 'category']

class TechnicalSupportForm(forms.ModelForm):
    ISSUE_CHOICES = [
        ('login', 'Login/Password Issue'),
        ('software', 'Software/System Error'),
        ('hardware', 'Device/Hardware Issue'),
        ('other', 'Other'),
    ]

    issue_type = forms.ChoiceField(choices=ISSUE_CHOICES, label="Issue Type")

    class Meta:
        model = Ticket
        fields = ['title', 'issue_type', 'description']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4, 'placeholder': 'Describe your issue'}),
            'title': forms.TextInput(attrs={'placeholder': 'Ticket Title'}),
        }

class AcademicSupportForm(forms.Form):
    program_year = forms.CharField(
        max_length=50, 
        label="Program / Year Level",
        widget=forms.TextInput(attrs={'placeholder': 'Program / Year Level'})
    )
    
    INQUIRY_CHOICES = [
        ('enrollment','Enrollment / Registration'),
        ('grades','Grades / Transcript'),
        ('schedule','Schedule / Class Availability'),
        ('curriculum','Curriculum / Course Requirements'),
        ('other','Other')
    ]
    inquiry_type = forms.ChoiceField(choices=INQUIRY_CHOICES, label="Inquiry Type")
    
    question = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 4, 'placeholder': 'Describe your question/issue'}), 
        label="Question / Issue"
    )

class LostAndFoundForm(forms.Form):
    DEPARTMENT_CHOICES = [
        ('jhs', 'JHS'),
        ('shs', 'SHS'),
        ('college', 'College'),
    ]
    department = forms.ChoiceField(choices=DEPARTMENT_CHOICES, label="Department")
    
    item_description = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 3, 'placeholder': 'Describe the item'}), 
        label="Item Description"
    )
    
    location = forms.CharField(
        max_length=100, 
        label="Location Last Seen / Found",
        widget=forms.TextInput(attrs={'placeholder': 'Location'})
    )
    
    date_time = forms.DateTimeField(label="Date / Time")
    
    photo = forms.FileField(required=False, label="Upload Photo (optional)")
    
    notes = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 2, 'placeholder': 'Optional notes'}), 
        required=False
    )

class WelfareForm(forms.Form):
    CONTACT_CHOICES = [
        ('email', 'Email'),
        ('phone', 'Phone'),
        ('inperson', 'In-Person')
    ]
    contact_method = forms.ChoiceField(choices=CONTACT_CHOICES, label="Preferred Contact Method")
    
    REQUEST_CHOICES = [
        ('academic', 'Academic Stress / Guidance'),
        ('personal', 'Personal / Emotional Support'),
        ('mental', 'Mental Health Counselling'),
        ('peer', 'Peer / Conflict Mediation'),
        ('other', 'Other')
    ]
    request_type = forms.ChoiceField(choices=REQUEST_CHOICES, label="Request Type")
    
    description = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 4, 'placeholder': 'Brief Description of Concern'}),
        label="Description"
    )
    
    preferred_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'type': 'date'}),
        label="Preferred Meeting Date"
    )

class FacilitiesForm(forms.Form):
    ISSUE_CHOICES = [
        ('electrical', 'Electrical / Lighting'),
        ('plumbing', 'Plumbing / Water'),
        ('furniture', 'Furniture / Fixtures'),
        ('it', 'IT / AV Equipment'),
        ('safety', 'Safety / Security'),
        ('other', 'Other')
    ]
    
    URGENCY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High')
    ]
    
    location = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={'placeholder': 'Location of the issue'}),
        label="Location"
    )
    
    issue_type = forms.ChoiceField(choices=ISSUE_CHOICES, label="Issue Type")
    
    description = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 4, 'placeholder': 'Describe the issue'}),
        label="Description"
    )
    
    photo = forms.FileField(required=False, label="Attach a Photo (optional)")
    
    urgency = forms.ChoiceField(choices=URGENCY_CHOICES, label="Urgency Level")

