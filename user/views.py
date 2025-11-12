from django.shortcuts import render, redirect
from django.contrib import messages
from django.core.mail import send_mail
from django.conf import settings
from django.contrib.auth import authenticate, login
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta
from django.contrib.auth import logout
from django.template.loader import render_to_string
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes
from django.contrib.auth.tokens import default_token_generator
from django.contrib.auth import get_user_model
User = get_user_model()
from .forms import RegisterForm, LoginForm, EmailVerificationForm
from .models import EmailVerification
from admin_panel import views as views


def send_verification_email(email, code):
    subject = "Verify Your Email"
    message = f"Your verification code is: {code}"
    from_email = settings.DEFAULT_FROM_EMAIL
    recipient_list = [email]
    send_mail(subject, message, from_email, recipient_list)

def register_view(request):
    if request.method == "POST":
        form = RegisterForm(request.POST)
        if form.is_valid():
            first_name = form.cleaned_data['first_name']
            last_name = form.cleaned_data['last_name']
            email = form.cleaned_data['email']
            password = form.cleaned_data['password']

            if User.objects.filter(username=email).exists():
                messages.error(request, "This email is already registered. Please log in.")
                return redirect('user:login')

            user = User.objects.create_user(
                username=email,
                email=email,
                first_name=first_name,
                last_name=last_name,
                password=password,
                is_active=False, 
            )
            try:
                code = EmailVerification.generate_code()
                EmailVerification.objects.update_or_create(
                    email=email,
                    defaults={'password': password, 'code': code}
                )

                try:
                    send_verification_email(email, code)
                except Exception as e:
                    print("Email sending failed:", e)
                    messages.error(request, "Could not send verification email. Check email settings.")
                    user.delete()  # cleanup
                    return redirect('user:register')

                request.session['verify_email'] = email
                return redirect('user:verify_email')

            except Exception as e:
                print("Registration error:", e)
                messages.error(request, "An unexpected error occurred during registration.")
                return redirect('user:register')

    else:
        form = RegisterForm()

    return render(request, 'user/register.html', {'form': form})

def verify_email_view(request):
    email = request.session.get('verify_email')
    if not email:
        return redirect('user:register')

    verification = EmailVerification.objects.filter(email=email).first()
    if not verification:
        messages.error(request, "No verification code found. Please register again.")
        return redirect('user:register')

    if request.method == "POST":
        form = EmailVerificationForm(request.POST)
        if form.is_valid():
            code_input = form.cleaned_data['code']
            if code_input == verification.code:
                
                user = User.objects.get(username=email)
                user.is_active = True
                user.save()

                verification.delete()
                messages.success(request, "Email verified! You can now log in.")
                return redirect('user:login')
            else:
                messages.error(request, "Incorrect verification code.")
                user.delete()
                verification.delete()
                return redirect('user:register')
    else:
        form = EmailVerificationForm()

    return render(request, 'user/verify_email.html', {'form': form, 'email': email})

def login_view(request):
    
    if request.user.is_authenticated:
        if request.user.is_superuser or request.user.is_staff:
            return redirect('admin_panel:admin_home')
        return redirect('dashboard:home')

    form = LoginForm(request.POST or None)

    if request.method == "POST" and form.is_valid():
        email = form.cleaned_data['email']
        password = form.cleaned_data['password']

        try:
            user_obj = User.objects.get(email=email)
        except User.DoesNotExist:
            user_obj = None

        
        if user_obj and (email.endswith('@ust-legazpi.edu.ph') or user_obj.is_superuser or user_obj.is_staff):
            
            user = authenticate(request, username=user_obj.username, password=password)
            if user:
                login(request, user)
                messages.success(request, "Logged in successfully!")

                if user.is_superuser or user.is_staff:
                    return redirect('admin_panel:admin_home')
                return redirect('dashboard:home')
            else:
                messages.error(request, "Invalid email or password.")
        else:
            messages.error(request, "Email must be a @ust-legazpi.edu.ph account.")

    return render(request, 'user/login.html', {'form': form})

def logout_view(request):
    logout(request)
    messages.success(request, "Logged out successfully.")
    return redirect('user:login')

def password_reset_request(request):
    if request.method == "POST":
        email = request.POST.get("email")
        users = User.objects.filter(email=email)
        if users.exists():
            user = users.first()
            subject = "Reset your MyTomasino password"
            context = {
                'user': user,
                'domain': '127.0.0.1:8000',  
                'uid': urlsafe_base64_encode(force_bytes(user.pk)),
                'token': default_token_generator.make_token(user),
                'protocol': 'http',
            }

            message = render_to_string('user/password_reset_email.txt', context)

            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                [email],
                fail_silently=False,
            )

            messages.success(request, "A password reset link has been sent to your email.")
            return redirect('user:password_reset_done')
        else:
            messages.error(request, "No account found with that email.")
    
    return render(request, 'user/password_reset.html')

def password_reset_done(request):
    return render(request, 'user/password_reset_done.html')

def password_reset_confirm(request, uidb64, token):
    try:
        uid = urlsafe_base64_decode(uidb64).decode()
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None

    if user is not None and default_token_generator.check_token(user, token):
        if request.method == "POST":
            password1 = request.POST.get("new_password1")
            password2 = request.POST.get("new_password2")

            if password1 and password2 and password1 == password2:
                user.set_password(password1)
                user.save()
                messages.success(request, "Your password has been reset successfully.")
                return redirect('user:password_reset_complete')
            else:
                messages.error(request, "Passwords do not match. Please try again.")

        return render(request, 'user/password_reset_confirm.html', {'validlink': True})
    else:
        messages.error(request, "The reset link is invalid or has expired.")
        return render(request, 'user/password_reset_confirm.html', {'validlink': False})

def password_reset_complete(request):
    return render(request, 'user/password_reset_complete.html')