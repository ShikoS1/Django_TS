from django.utils.deprecation import MiddlewareMixin
from django.shortcuts import redirect
from django.urls import reverse

class ForceLoginMiddleware(MiddlewareMixin):
    def process_request(self, request):
        if request.path.startswith('/admin/login'):
            return redirect(reverse('login'))

        if not hasattr(request, 'user'):
            return None
            
        if not request.user.is_authenticated and not (
            request.path.startswith('/login') or request.path.startswith('/static') or request.path.startswith('/admin')
        ):
            return redirect('login')
            
        if request.user.is_authenticated and request.path.startswith('/login'):
            return redirect('/')