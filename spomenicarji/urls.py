"""
URL configuration for spomenicarji project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import include, path
from django.conf.urls.static import static
from django.views.generic.base import RedirectView

#wagtail
#from wagtail.admin import urls as wagtailadmin_urls
#from wagtail import urls as wagtail_urls
#from wagtail.documents import urls as wagtaildocs_urls

from django.conf import settings

from django.conf.urls.i18n import i18n_patterns
from django.utils.translation import gettext_lazy as _
from django.views.i18n import set_language
from django.views.static import serve as static_serve
from django.contrib.auth import views as auth_views


urlpatterns = [
    path('i18n/setlang/', set_language, name='set_language'),
    path(
        "o-projektu/",
        RedirectView.as_view(
            url="https://sl.wikiversity.org/wiki/Partizanski_spomeniki_na_zemljevidu",
            permanent=True,
        ),
        name="o-projektu-redirect",
    ),
    path('admin/', admin.site.urls),
    path("api/", include("zemljevid.api")),
    #path('cms/', include(wagtailadmin_urls)),
    #path('documents/', include(wagtaildocs_urls)),
    #path('pages/', include(wagtail_urls)),
    #path('filer/', include('filer.urls')),
    path("favicon.svg", static_serve, {
        'path': 'images/rdeca-zvezdica.svg',
        'document_root': settings.STATIC_ROOT or settings.STATICFILES_DIRS[0],
    }),
    path("favicon.ico", static_serve, {
        'path': 'images/favicon.ico',
        'document_root': settings.STATIC_ROOT or settings.STATICFILES_DIRS[0],
    }),
    path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(), name='password_reset_confirm'),
   path('password_reset/done/', auth_views.PasswordResetDoneView.as_view(), name='password_reset_done'),
    path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    path('reset/done/', auth_views.PasswordResetCompleteView.as_view(), name='password_reset_complete'),
# redirect accounts/login/ → admin/login
    path('accounts/login/', RedirectView.as_view(url='/admin/login/', permanent=True)),
#    path('robots.txt', static_serve, {
#        'path': 'robots.txt',
#        'document_root': settings.STATIC_ROOT or settings.STATICFILES_DIRS[0],
#    }),
]
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
urlpatterns += i18n_patterns(
    path(_(''), include('zemljevid.urls')),
)
from zemljevid.memorial_tables_views import urlpatterns as memorial_tables_urlpatterns
urlpatterns += memorial_tables_urlpatterns

