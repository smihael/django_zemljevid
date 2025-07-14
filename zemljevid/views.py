import os
import json
import urllib.parse
from pathlib import Path
from rest_framework.response import Response
from rest_framework import viewsets
from django.http import JsonResponse
from django.apps import apps
import csv
from django.http import StreamingHttpResponse
import openpyxl
from openpyxl.utils import get_column_letter
from django.http import HttpResponse
from django.utils.html import strip_tags

from django.shortcuts import render, get_object_or_404
from django.views import View
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt

from rest_framework import viewsets
from rest_framework_gis.filters import InBBoxFilter
from rest_framework.filters import SearchFilter
from django.views.generic.detail import DetailView
from rest_framework.views import APIView
from rest_framework import status
from .forms import AnonymousMemorialForm
from django.http import HttpResponseRedirect
from django.urls import reverse


# class GalleryView(View):
#     def get(self, request, *args, **kwargs):
#         table_id = request.GET.get('table_id')
#         fid = request.GET.get('fid')

#         if not table_id or not fid:
#             return JsonResponse({"error": "Missing table_id or fid"}, status=400)

#         # Use the ImageListViewSet to get the list of images
#         image_list_view_set = ImageListViewSet()
#         response = image_list_view_set.list(request)
#         images = response.data

#         return render(request, 'gallery.html', {'images': images})

    
class GenericDetailView(View):
    def get(self, request, *args, **kwargs):
        model_name = kwargs.get('model_name')
        object_id = kwargs.get('object_id')

        if not model_name or not object_id:
            return JsonResponse({"error": "Missing model_name or object_id"}, status=400)

        try:
            model = apps.get_model('zemljevid', model_name)
        except LookupError:
            return JsonResponse({"error": "Model not found"}, status=404)

        obj = get_object_or_404(model, pk=object_id)
        fields = {field.name: getattr(obj, field.name) for field in model._meta.get_fields()}

        return render(request, 'generic_detail.html', {'model_name': model_name, 'fields': fields})

class GeopediaDetailView(DetailView):
    model = None  # This will be set dynamically
    template_name = 'generic_detail.html'
    context_object_name = 'entry'
    extra_context = {}
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(self.extra_context)
        return context
    def get_object(self, queryset=None):
        # Get the model name and object ID from the URL
        model_name = self.kwargs.get('model_name')
        object_id = self.kwargs.get('object_id')

        # Get the model class dynamically
        try:
            self.model = apps.get_model('zemljevid', model_name)
        except LookupError:
            return JsonResponse({"error": "Model not found"}, status=404)

        # Fetch the object using the object ID
        obj = get_object_or_404(self.model, pk=object_id)
        return obj
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['model_name'] = self.kwargs.get('model_name')
        context['object_id'] = self.kwargs.get('object_id')
        context['fields'] = {field.name: getattr(self.object, field.name) for field in self.model._meta.get_fields()}
        return context

class ExportTableCSVView(View):
    def get(self, request, *args, **kwargs):
        model_name = kwargs.get('model_name')
        if not model_name:
            return JsonResponse({"error": "Missing model_name"}, status=400)
        try:
            model = apps.get_model('zemljevid', model_name)
        except LookupError:
            return JsonResponse({"error": "Model not found"}, status=404)
        # Query all objects
        queryset = model.objects.all()
        # Get field names
        field_names = [field.name for field in model._meta.fields]
        # Streaming response for large tables
        def row_generator():
            yield ','.join(field_names) + '\n'
            for obj in queryset.iterator():
                row = [str(getattr(obj, field, '')) for field in field_names]
                yield ','.join(row) + '\n'
        response = StreamingHttpResponse(row_generator(), content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="{model_name}.csv"'
        return response

class ExportTableXLSXView(View):
    def get(self, request, *args, **kwargs):
        model_name = kwargs.get('model_name')
        if not model_name:
            return JsonResponse({"error": "Missing model_name"}, status=400)
        try:
            model = apps.get_model('zemljevid', model_name)
        except LookupError:
            return JsonResponse({"error": "Model not found"}, status=404)
        queryset = model.objects.all()
        # Skip geom field
        field_names = [field.name for field in model._meta.fields if field.name != 'geom']
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = model_name

        ws.append(field_names)
        for obj in queryset.iterator():
            row = []
            for field in field_names:
                value = getattr(obj, field, '')
                # If field is datetime, show only date in YYYY-MM-DD format
                import datetime
                if isinstance(value, datetime.datetime):
                    value = value.date().isoformat()
                elif isinstance(value, datetime.date):
                    value = value.isoformat()
                # Remove timezone info for datetime/time objects
                if hasattr(value, 'tzinfo') and value.tzinfo is not None:
                    value = value.replace(tzinfo=None)
                # Convert HTML fields to plain text
                #if isinstance(value, str) and ('<p>' in value or '<div>' in value or '<br' in value or '<span>' in value or '<li>' in value or '<font>' in value):
                from tinymce.models import HTMLField
                if hasattr(model, field) and isinstance(model._meta.get_field(field), HTMLField):
                    value = strip_tags(value)
                row.append(value)
            ws.append(row)

        # Set overall font to Arial 12
        from openpyxl.styles import Font
        arial_font = Font(name='Arial', size=12)        
        for row in ws.iter_rows():
            for cell in row:
                cell.font = arial_font
                
        # Auto-size columns
        for col_num, column_title in enumerate(field_names, 1):
            column_letter = get_column_letter(col_num)
            ws.column_dimensions[column_letter].width = max(10, len(column_title) + 2)
        response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = f'attachment; filename="{model_name}.xlsx"'
        wb.save(response)
        return response

class ExportTableView(View):
    def get(self, request, *args, **kwargs):
        model_name = kwargs.get('model_name')
        if not model_name:
            return JsonResponse({"error": "Missing model_name"}, status=400)
        export_url = request.build_absolute_uri(f'/export_csv/{model_name}/')
        return render(request, 'export_table.html', {'export_url': export_url, 'model_name': model_name})

def missing_memorial_view(request):
    if request.method == 'POST':
        form = AnonymousMemorialForm(request.POST)
        if form.is_valid():
            form.save()
            return render(request, 'zemljevid/missing_memorial.html', {'form': None, 'success': True})
    else:
        form = AnonymousMemorialForm()
    return render(request, 'zemljevid/missing_memorial.html', {'form': form})