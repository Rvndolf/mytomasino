import os
from django import forms
from django.core.exceptions import ValidationError
from .models import Ticket


def validate_image_extension(value):
    ext = os.path.splitext(value.name)[1].lower()
    if ext not in ['.jpeg', '.jpg', '.png']:
        raise ValidationError('Only .jpeg and .png files are allowed.')


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
        fields = ['title', 'description']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4, 'placeholder': 'Describe your issue'}),
            'title': forms.TextInput(attrs={'placeholder': 'Ticket Title'}),
        }

    def __init__(self, *args, **kwargs):
        instance = kwargs.get('instance')
        super().__init__(*args, **kwargs)
        if instance and instance.metadata:
            self.fields['issue_type'].initial = instance.metadata.get('issue_type')

    def save(self, commit=True):
        ticket = super().save(commit=False)
        issue_type = self.cleaned_data.get('issue_type')
        ticket.metadata = {
            'issue_type': issue_type,
            'issue_type_display': dict(self.ISSUE_CHOICES)[issue_type]
        }
        if commit:
            ticket.save()
        return ticket


class AcademicSupportForm(forms.ModelForm):
    program_year = forms.CharField(
        max_length=50,
        label="Program / Year Level",
        widget=forms.TextInput(attrs={'placeholder': 'Program / Year Level'})
    )

    INQUIRY_CHOICES = [
        ('enrollment', 'Enrollment / Registration'),
        ('grades', 'Grades / Transcript'),
        ('schedule', 'Schedule / Class Availability'),
        ('curriculum', 'Curriculum / Course Requirements'),
        ('other', 'Other')
    ]
    inquiry_type = forms.ChoiceField(choices=INQUIRY_CHOICES, label="Inquiry Type")

    question = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 4, 'placeholder': 'Describe your question/issue'}),
        label="Question / Issue"
    )

    class Meta:
        model = Ticket
        fields = ['title']
        widgets = {
            'title': forms.TextInput(attrs={'placeholder': 'Ticket Title'}),
        }

    def __init__(self, *args, **kwargs):
        instance = kwargs.get('instance')
        super().__init__(*args, **kwargs)
        if instance:
            if instance.metadata:
                self.fields['program_year'].initial = instance.metadata.get('program_year')
                self.fields['inquiry_type'].initial = instance.metadata.get('inquiry_type')
            if instance.description:
                self.fields['question'].initial = instance.description

    def save(self, commit=True):
        ticket = super().save(commit=False)
        program_year = self.cleaned_data.get('program_year')
        inquiry_type = self.cleaned_data.get('inquiry_type')
        question = self.cleaned_data.get('question')
        ticket.metadata = {
            'program_year': program_year,
            'inquiry_type': inquiry_type,
            'inquiry_type_display': dict(self.INQUIRY_CHOICES)[inquiry_type]
        }
        ticket.description = question
        if commit:
            ticket.save()
        return ticket


class LostAndFoundForm(forms.ModelForm):
    item_description = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 3, 'placeholder': 'Describe the item'}),
        label="Item Description"
    )

    location = forms.CharField(
        max_length=100,
        label="Location Last Seen / Found",
        widget=forms.TextInput(attrs={'placeholder': 'Location'})
    )

    date_time = forms.DateTimeField(
        label="Date / Time",
        widget=forms.DateTimeInput(attrs={'type': 'datetime-local'})
    )

    photo = forms.FileField(
        required=False,
        label="Upload Photo (optional)",
        validators=[validate_image_extension],
        widget=forms.FileInput(attrs={'accept': '.jpeg,.jpg,.png'})
    )

    notes = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 2, 'placeholder': 'Optional notes'}),
        required=False
    )

    class Meta:
        model = Ticket
        fields = ['title']
        widgets = {
            'title': forms.TextInput(attrs={'placeholder': 'Item Name'}),
        }

    def __init__(self, *args, **kwargs):
        instance = kwargs.get('instance')
        super().__init__(*args, **kwargs)
        if instance:
            if instance.metadata:
                self.fields['location'].initial = instance.metadata.get('location')
                raw_dt = instance.metadata.get('date_time')
                if raw_dt:
                    self.fields['date_time'].initial = raw_dt.replace(' ', 'T')
            if instance.description:
                desc_parts = instance.description.split('\n\nNotes: ', 1)
                self.fields['item_description'].initial = desc_parts[0]
                if len(desc_parts) > 1:
                    self.fields['notes'].initial = desc_parts[1]

    def save(self, commit=True):
        ticket = super().save(commit=False)
        item_description = self.cleaned_data.get('item_description')
        location = self.cleaned_data.get('location')
        date_time = self.cleaned_data.get('date_time')
        notes = self.cleaned_data.get('notes', '')
        photo = self.cleaned_data.get('photo')
        ticket.metadata = {
            'location': location,
            'date_time': date_time.strftime('%Y-%m-%d %H:%M'),
        }
        ticket.description = item_description
        if notes:
            ticket.description += f"\n\nNotes: {notes}"
        if photo:
            ticket.attachment = photo
        if commit:
            ticket.save()
        return ticket


class WelfareForm(forms.ModelForm):
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

    class Meta:
        model = Ticket
        fields = ['title']
        widgets = {
            'title': forms.TextInput(attrs={'placeholder': 'Counseling Request Title'}),
        }

    def __init__(self, *args, **kwargs):
        instance = kwargs.get('instance')
        super().__init__(*args, **kwargs)
        if instance:
            if instance.metadata:
                self.fields['contact_method'].initial = instance.metadata.get('contact_method')
                self.fields['request_type'].initial = instance.metadata.get('request_type')
                self.fields['preferred_date'].initial = instance.metadata.get('preferred_date')
            if instance.description:
                self.fields['description'].initial = instance.description

    def save(self, commit=True):
        ticket = super().save(commit=False)
        contact_method = self.cleaned_data.get('contact_method')
        request_type = self.cleaned_data.get('request_type')
        description = self.cleaned_data.get('description')
        preferred_date = self.cleaned_data.get('preferred_date')
        ticket.metadata = {
            'contact_method': contact_method,
            'contact_method_display': dict(self.CONTACT_CHOICES)[contact_method],
            'request_type': request_type,
            'request_type_display': dict(self.REQUEST_CHOICES)[request_type],
        }
        if preferred_date:
            ticket.metadata['preferred_date'] = preferred_date.strftime('%Y-%m-%d')
        ticket.description = description
        if commit:
            ticket.save()
        return ticket


class FacilitiesForm(forms.ModelForm):
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

    photo = forms.FileField(
        required=False,
        label="Attach a Photo (optional)",
        validators=[validate_image_extension],
        widget=forms.FileInput(attrs={'accept': '.jpeg,.jpg,.png'})
    )

    urgency = forms.ChoiceField(choices=URGENCY_CHOICES, label="Urgency Level")

    class Meta:
        model = Ticket
        fields = ['title']
        widgets = {
            'title': forms.TextInput(attrs={'placeholder': 'Issue Title'}),
        }

    def __init__(self, *args, **kwargs):
        instance = kwargs.get('instance')
        super().__init__(*args, **kwargs)
        if instance:
            if instance.metadata:
                self.fields['location'].initial = instance.metadata.get('location')
                self.fields['issue_type'].initial = instance.metadata.get('issue_type')
                self.fields['urgency'].initial = instance.metadata.get('urgency')
            if instance.description:
                self.fields['description'].initial = instance.description

    def save(self, commit=True):
        ticket = super().save(commit=False)
        location = self.cleaned_data.get('location')
        issue_type = self.cleaned_data.get('issue_type')
        description = self.cleaned_data.get('description')
        urgency = self.cleaned_data.get('urgency')
        photo = self.cleaned_data.get('photo')
        ticket.metadata = {
            'location': location,
            'issue_type': issue_type,
            'issue_type_display': dict(self.ISSUE_CHOICES)[issue_type],
            'urgency': urgency,
            'urgency_display': dict(self.URGENCY_CHOICES)[urgency]
        }
        ticket.description = description
        if photo:
            ticket.attachment = photo
        if commit:
            ticket.save()
        return ticket


class GeneralInquiryForm(forms.ModelForm):
    inquiry = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 6, 'placeholder': 'Type your question or inquiry here...'}),
        label="Your Inquiry"
    )

    class Meta:
        model = Ticket
        fields = ['title']
        widgets = {
            'title': forms.TextInput(attrs={'placeholder': 'Brief subject or title'}),
        }

    def __init__(self, *args, **kwargs):
        instance = kwargs.get('instance')
        super().__init__(*args, **kwargs)
        if instance and instance.description:
            self.fields['inquiry'].initial = instance.description

    def save(self, commit=True):
        ticket = super().save(commit=False)
        inquiry = self.cleaned_data.get('inquiry')
        ticket.description = inquiry
        ticket.metadata = {'form_type': 'general_inquiry'}
        if commit:
            ticket.save()
        return ticket