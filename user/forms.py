from django import forms
from django.core.exceptions import ValidationError
from django.contrib.auth.models import User
from django import forms

class EmailVerificationForm(forms.Form):
    code = forms.CharField(
        max_length=6,
        label="Enter Verification Code",
        widget=forms.TextInput(attrs={'placeholder': '6-digit code', 'class':'form-control'})
    )

class RegisterForm(forms.Form):
    email = forms.EmailField(
        label="Email",
        widget=forms.EmailInput(attrs={'placeholder': 'yourname@ust-legazpi.edu.ph', 'class':'form-control'})
    )
    password = forms.CharField(
        label="Password",
        widget=forms.PasswordInput(attrs={'placeholder': 'Enter password', 'class':'form-control'})
    )
    password_confirm = forms.CharField(
        label="Confirm Password",
        widget=forms.PasswordInput(attrs={'placeholder': 'Confirm password', 'class':'form-control'})
    )

    def clean_email(self):
        email = self.cleaned_data['email']
        if not email.lower().endswith('@ust-legazpi.edu.ph'):
            raise ValidationError("Only @ust-legazpi.edu.ph emails are allowed.")
        if User.objects.filter(username=email).exists():
            raise ValidationError("This email is already registered.")
        return email

    def clean(self):
        cleaned_data = super().clean()
        pw = cleaned_data.get("password")
        pw2 = cleaned_data.get("password_confirm")
        if pw and pw2 and pw != pw2:
            raise ValidationError("Passwords do not match.")
        return cleaned_data


class LoginForm(forms.Form):
    email = forms.EmailField(
        label="Email",
        widget=forms.EmailInput(attrs={'placeholder': 'yourname@ust-legazpi.edu.ph', 'class':'form-control'})
    )
    password = forms.CharField(
        label="Password",
        widget=forms.PasswordInput(attrs={'placeholder': 'Enter password', 'class':'form-control'})
    )

    