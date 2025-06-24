from django.utils.deprecation import MiddlewareMixin
from django.shortcuts import redirect
from django.urls import reverse

class ForceLoginMiddleware(MiddlewareMixin):
    def process_request(self, request):
        # Пути, которые не требуют авторизации
        allowed_paths = [
            '/login', '/logout', '/admin/login', '/admin/logout', '/favicon.ico', '/static', '/media'
        ]
        if any(request.path.startswith(p) for p in allowed_paths):
            # Явная проверка для /admin/logout: если не staff, сразу на login
            if request.path.startswith('/admin/logout'):
                if not (hasattr(request, 'user') and request.user.is_authenticated and request.user.is_staff):
                    return redirect(reverse('login'))
            return None

        # Важно: AuthenticationMiddleware должен идти раньше!
        if not hasattr(request, 'user'):
            return None

        # Для админки: разрешаем только staff, остальных сразу на login
        if request.path.startswith('/admin'):
            if not (request.user.is_authenticated and request.user.is_staff):
                return redirect(reverse('login'))
            return None

        # Для всех остальных: только аутентифицированные
        if not request.user.is_authenticated:
            return redirect(reverse('login'))

        # Если уже залогинен и идёт на /login — редирект на главную
        if request.user.is_authenticated and request.path.startswith('/login'):
            return redirect('/')

        return None