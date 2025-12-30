from django import forms
from django.core.exceptions import ValidationError
from django.contrib.auth.models import User
from django import forms

class LoginForm(forms.Form):
    email = forms.EmailField(
        label="Email",
        widget=forms.EmailInput(attrs={'placeholder': 'yourname@ust-legazpi.edu.ph', 'class':'form-control'})
    )
    password = forms.CharField(
        label="Password",
        widget=forms.PasswordInput(attrs={'placeholder': 'Enter password', 'class':'form-control'})
    )

    