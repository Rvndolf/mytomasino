from django.shortcuts import render
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.models import User

# Only allow staff (admin) users to access this panel
def admin_required(view_func):
    decorated_view_func = user_passes_test(lambda u: u.is_staff, login_url='/user/login/')(view_func)
    return decorated_view_func

@login_required
@admin_required
def dashboard_home(request):
    return render(request, 'admin_panel/dashboard.html')

@login_required
@admin_required
def users_list(request):
    users = User.objects.all()
    return render(request, 'admin_panel/users_list.html', {'users': users})
