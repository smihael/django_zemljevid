from django.urls import path
from django.shortcuts import render, redirect
from django.views.generic import TemplateView
from django.conf import settings
#from zemljevid.views import GalleryView, GenericDetailView, GeopediaDetailView

from django.utils.translation import gettext_lazy as _

from django.contrib.auth import views as auth_views
from .views import ExportTableCSVView, ExportTableView, ExportTableXLSXView, missing_memorial_view



urlpatterns = [
    path(
        _("map/"),
        TemplateView.as_view(
            template_name="map.html",
            extra_context={'api_key': settings.MAPTILER_API_KEY, 'default_lat': settings.DEFAULT_LAT, 'default_lng': settings.DEFAULT_LNG}  
        ),
        name='map'
    ),
    #path('detail/<str:model_name>/<int:object_id>/', GenericDetailView.as_view(), name='generic_detail'),
    path(
        '',
        lambda request: redirect('map', permanent=False),
        name='home-redirect'
    ),
    path(
        _('about/'),
        lambda request: redirect('https://sl.wikiversity.org/wiki/Partizanski_spomeniki_na_zemljevidu'),
        name='about'
    ),
    path('export_csv/<str:model_name>/', ExportTableCSVView.as_view(), name='export_csv'),
    path('export_xslx/<str:model_name>/', ExportTableXLSXView.as_view(), name='export_xslx'),
    path('export_table/<str:model_name>/', ExportTableView.as_view(), name='export_table'),
    path(
        _('contribute_memorial/'),
        missing_memorial_view,
        name='contribute_memorial'
    ),
]

