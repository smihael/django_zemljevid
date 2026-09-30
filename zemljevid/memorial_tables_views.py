import django_tables2 as tables
import django_filters
from django_tables2.views import SingleTableMixin
from django_filters.views import FilterView
from django.urls import path
from .models import PartisanMemorial, CroatianPartisanMemorial, PartisanHospital, PartisanNaming, PartisanPointsWithoutMemorial, OtherMemorials, PartisanTrail, OsamosvojitvenaObelezja
from .tables import (
    PartisanMemorialTable, PartisanMemorialFilter,
    CroatianPartisanMemorialTable, CroatianPartisanMemorialFilter,
    PartisanHospitalTable, PartisanHospitalFilter,
    PartisanNamingTable, PartisanNamingFilter,
    PartisanPointsWithoutMemorialTable, PartisanPointsWithoutMemorialFilter,
    OtherMemorialsTable, OtherMemorialsFilter,
    OsamosvojitvenaObelezjaTable, OsamosvojitvenaObelezjaFilter,
    PartisanTrailTable, PartisanTrailFilter,
)


class MemorialTableCountMixin:
    def get_context_data(self, **kwargs):
        try:
            context = super().get_context_data(**kwargs)
        except AttributeError:
            context = {}
        queryset = getattr(self, 'object_list', None)
        if queryset is None:
            queryset = self.get_queryset()
        if hasattr(queryset, 'count') and not isinstance(queryset, (list, tuple, set, dict)):
            context['match_count'] = queryset.count()
        else:
            context['match_count'] = len(queryset)
        return context


class PartisanMemorialListView(MemorialTableCountMixin, SingleTableMixin, FilterView):
    table_class = PartisanMemorialTable
    model = PartisanMemorial
    template_name = "memorial_table.html"
    filterset_class = PartisanMemorialFilter

class CroatianPartisanMemorialListView(MemorialTableCountMixin, SingleTableMixin, FilterView):
    table_class = CroatianPartisanMemorialTable
    model = CroatianPartisanMemorial
    template_name = "memorial_table.html"
    filterset_class = CroatianPartisanMemorialFilter

class PartisanHospitalListView(MemorialTableCountMixin, SingleTableMixin, FilterView):
    table_class = PartisanHospitalTable
    model = PartisanHospital
    template_name = "memorial_table.html"
    filterset_class = PartisanHospitalFilter

class PartisanNamingListView(MemorialTableCountMixin, SingleTableMixin, FilterView):
    table_class = PartisanNamingTable
    model = PartisanNaming
    template_name = "memorial_table.html"
    filterset_class = PartisanNamingFilter

class PartisanPointsWithoutMemorialListView(MemorialTableCountMixin, SingleTableMixin, FilterView):
    table_class = PartisanPointsWithoutMemorialTable
    model = PartisanPointsWithoutMemorial
    template_name = "memorial_table.html"
    filterset_class = PartisanPointsWithoutMemorialFilter

class OtherMemorialsListView(MemorialTableCountMixin, SingleTableMixin, FilterView):
    table_class = OtherMemorialsTable
    model = OtherMemorials
    template_name = "memorial_table.html"
    filterset_class = OtherMemorialsFilter

class OsamosvojitvenaObelezjaListView(MemorialTableCountMixin, SingleTableMixin, FilterView):
    table_class = OsamosvojitvenaObelezjaTable
    model = OsamosvojitvenaObelezja
    template_name = "memorial_table.html"
    filterset_class = OsamosvojitvenaObelezjaFilter

class PartisanTrailListView(MemorialTableCountMixin, SingleTableMixin, FilterView):
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
    path('filter/osamosvojitvenaobelezja/', OsamosvojitvenaObelezjaListView.as_view(), name='osamosvojitvena_obelezja_table'),
    path('filter/croatianpartisanmemorial/', CroatianPartisanMemorialListView.as_view(), name='croatian_partisan_memorial_table'),
]
