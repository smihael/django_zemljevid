import django_tables2 as tables
import django_filters
from django_tables2.views import SingleTableMixin
from django_filters.views import FilterView
from django.urls import path
from .models import PartisanMemorial, CroatianPartisanMemorial, PartisanHospital, PartisanNaming, PartisanPointsWithoutMemorial, OtherMemorials, PartisanTrail
from .tables import (
    PartisanMemorialTable, PartisanMemorialFilter,
    CroatianPartisanMemorialTable, CroatianPartisanMemorialFilter,
    PartisanHospitalTable, PartisanHospitalFilter,
    PartisanNamingTable, PartisanNamingFilter,
    PartisanPointsWithoutMemorialTable, PartisanPointsWithoutMemorialFilter,
    OtherMemorialsTable, OtherMemorialsFilter,
    PartisanTrailTable, PartisanTrailFilter,
)

class PartisanMemorialListView(SingleTableMixin, FilterView):
    table_class = PartisanMemorialTable
    model = PartisanMemorial
    template_name = "memorial_table.html"
    filterset_class = PartisanMemorialFilter

class CroatianPartisanMemorialListView(SingleTableMixin, FilterView):
    table_class = CroatianPartisanMemorialTable
    model = CroatianPartisanMemorial
    template_name = "memorial_table.html"
    filterset_class = CroatianPartisanMemorialFilter

class PartisanHospitalListView(SingleTableMixin, FilterView):
    table_class = PartisanHospitalTable
    model = PartisanHospital
    template_name = "memorial_table.html"
    filterset_class = PartisanHospitalFilter

class PartisanNamingListView(SingleTableMixin, FilterView):
    table_class = PartisanNamingTable
    model = PartisanNaming
    template_name = "memorial_table.html"
    filterset_class = PartisanNamingFilter

class PartisanPointsWithoutMemorialListView(SingleTableMixin, FilterView):
    table_class = PartisanPointsWithoutMemorialTable
    model = PartisanPointsWithoutMemorial
    template_name = "memorial_table.html"
    filterset_class = PartisanPointsWithoutMemorialFilter

class OtherMemorialsListView(SingleTableMixin, FilterView):
    table_class = OtherMemorialsTable
    model = OtherMemorials
    template_name = "memorial_table.html"
    filterset_class = OtherMemorialsFilter

class PartisanTrailListView(SingleTableMixin, FilterView):
    table_class = PartisanTrailTable
    model = PartisanTrail
    template_name = "memorial_table.html"
    filterset_class = PartisanTrailFilter

urlpatterns = [
    path('filter/partisanmemorial/', PartisanMemorialListView.as_view(), name='partisan_memorial_table'),
    path('filter/partisanhospital/', PartisanHospitalListView.as_view(), name='partisan_hospital_table'),
    path('filter/partisannaming/', PartisanNamingListView.as_view(), name='partisan_naming_table'),
    path('filter/partisanpointswithoutmemorial/', PartisanPointsWithoutMemorialListView.as_view(), name='partisan_points_table'),
    path('filter/partisantrail/', PartisanTrailListView.as_view(), name='partisan_trail_table'),
    path('filter/othermemorials/', OtherMemorialsListView.as_view(), name='other_memorials_table'),
    path('filter/croatianpartisanmemorial/', CroatianPartisanMemorialListView.as_view(), name='croatian_partisan_memorial_table'),
]
