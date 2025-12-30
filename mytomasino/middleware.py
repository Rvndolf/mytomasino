from django.contrib.auth import logout
from django.shortcuts import redirect
from django.utils import timezone

class SessionTimeoutMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            # Ignore notification polling endpoint - don't count as activity
            if request.path == '/dashboard/notifications/count/':
                return self.get_response(request)
            
            last_activity = request.session.get('last_activity')
            
            if last_activity:
                # Check if session has expired (30 minutes = 1800 seconds)
                timeout_duration = 1800  # 30 minutes (120 for testing)
                if timezone.now().timestamp() - last_activity > timeout_duration:
                    logout(request)
                    return redirect('user:login')
            
            # Update last activity time (except for notification polling)
            request.session['last_activity'] = timezone.now().timestamp()
        
        response = self.get_response(request)
        return response