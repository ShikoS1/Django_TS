from django.contrib.auth.views import LoginView, LogoutView


class CustomLoginView(LoginView):
    template_name = 'registration/login.html'

    def get_success_url(self):
        return self.get_redirect_url() or '/'


from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from TS_equipment.views import guest_login

urlpatterns = [
    path('admin/', admin.site.urls),
    path('login/', CustomLoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(next_page='/login/'), name='logout'),
    path('guest-login/', guest_login, name='guest_login'),
    path('', include('TS_equipment.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)