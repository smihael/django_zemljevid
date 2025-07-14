from rest_framework import viewsets, serializers, views, response, routers
from django.urls import path
from rest_framework_gis.filters import InBBoxFilter
from rest_framework.filters import SearchFilter
from django.apps import apps
from rest_framework.response import Response
from django.http import JsonResponse
from django.contrib.contenttypes.models import ContentType
from django.db import connection

from .models import MemorialImage, AbstractGeoEntry
from .models import PartisanMemorial, PartisanHospital, PartisanNaming, PartisanPointsWithoutMemorial, OtherMemorials, PartisanTrail, CroatianPartisanMemorial

models = [
    PartisanMemorial,
    PartisanHospital,
    PartisanNaming,
    PartisanPointsWithoutMemorial,
    PartisanTrail,
    OtherMemorials,
    CroatianPartisanMemorial,
]

from .serializers import FullGeoEntrySerializer


class BriefGeoEntryViewSet(viewsets.ViewSet):
    table_name = None
    has_status_column = False

    def list(self, request):

        with connection.cursor() as cursor:
            cursor.execute(f"""
                SELECT json_build_object(
                'type', 'FeatureCollection',
                'features', json_agg(
                    json_build_object(
                    'type', 'Feature',
                    'id', id,
                    'geometry', ST_AsGeoJSON(geom)::json,
                    'properties', json_build_object(
                        'name', name{"," if self.has_status_column else ""}
                        {"'status', status" if self.has_status_column else ""}
                    )
                )
                )
                ) AS geojson
                FROM "{self.table_name}"
                WHERE geom IS NOT NULL AND (hidden IS FALSE OR hidden IS NULL);
            """)
            row = cursor.fetchone()
        return JsonResponse(row[0])

# Dynamic serializer generator
def create_serializer(name_suffix, base_class, model):
    class_name = f"{model.__name__}{name_suffix}"
    meta_class = type('Meta', (base_class.Meta,), {'model': model})
    return type(class_name, (base_class,), {'Meta': meta_class})

def create_viewset(model, serializer_class):
    class_name = f"{model.__name__}ViewSet"
    return type(
        class_name,
        (viewsets.ReadOnlyModelViewSet,),
        {
            'queryset': model.objects.all(),
            'serializer_class': serializer_class,
            'bbox_filter_field': 'geom',
            'filter_backends': [InBBoxFilter],
        }
    )

router = routers.DefaultRouter()

for model in models:
    model_name = model._meta.model_name

    full_serializer = create_serializer("Serializer", FullGeoEntrySerializer, model)
    #globals()[full_serializer.__name__] = full_serializer
    full_viewset = create_viewset(model, full_serializer)
    router.register(f"full/{model_name}", full_viewset, basename=f'full_{model_name}')
    
    brief_viewset = type(
        f"{model_name}BriefGeoEntryViewSet",
        (BriefGeoEntryViewSet,),
        {'table_name': model._meta.db_table, 'has_status_column': False if model_name != 'partisanmemorial' else True},
    )

    router.register(f"brief/{model_name}", brief_viewset, basename=f'brief_{model_name}')

    def get_details(self, request, *args, **kwargs):
        if not request.query_params.get('in_bbox'):
            if not request.query_params.get('id') or request.query_params.get('id') == '':
                return Response({"error": "Search parameter 'id' is required."}, status=400)
        return super(self.__class__, self).list(request, *args, **kwargs)
    
    detailed_viewset_class = type(
        f"{model_name}DetailedViewSet",
        (viewsets.ReadOnlyModelViewSet,),
        {
            "queryset": model.objects.all(),
            "serializer_class": full_serializer,
            "filter_backends": [InBBoxFilter, SearchFilter],
            "bbox_filter_field": "geom",
            "search_fields": ["=id"],
            "list": get_details,
        },
    )

    # Register the detailed viewset with the router for a single marker
    router.register(
        f"detail/{model_name.lower()}", detailed_viewset_class, basename=f"detail_{model_name.lower()}"
    )

# detail lahko verjento ukinem?


# Serializer
class GeoLayersSerializer(serializers.Serializer):
    model_name = serializers.CharField()
    description = serializers.CharField()
    verbose_name = serializers.CharField()
    verbose_name_plural = serializers.CharField()
    icon = serializers.CharField()

# API View
class GeoLayerListView(views.APIView):
    """
    Returns metadata about all non-abstract subclasses of AbstractGeoEntry.
    """
    def get(self, request):
        model_descriptions = [
            {
                'model_name': model.__name__.lower(),
                'description': model.__doc__ or 'No description available',
                'verbose_name': getattr(model._meta, 'verbose_name', 'No verbose name available'),
                'verbose_name_plural': getattr(model._meta, 'verbose_name_plural', 'No verbose name plural available'),
                'icon': str(model.icon) if hasattr(model, 'icon') else 'default_icon',
            }
            #for model in apps.get_models()
            #if issubclass(model, AbstractGeoEntry) and not model._meta.abstract
            for model in models
        ]
        serializer = GeoLayersSerializer(model_descriptions, many=True)
        return response.Response(serializer.data)

class GetImagesAPIView(views.APIView):
    def get(self, request, *args, **kwargs):
        model_name = request.query_params.get('model_name')
        object_id = request.query_params.get('object_id')

        if not model_name or not object_id:
            return Response({'error': 'model_name and object_id are required'}, status=400)

        # Validate model name and fetch content type
        try:
            content_type = ContentType.objects.get(app_label='zemljevid', model=model_name.lower())
        except ContentType.DoesNotExist:
            return Response({'error': f'Model name {model_name} is invalid'}, status=400)

        # Fetch images directly related to the content type and object ID
        images = MemorialImage.objects.filter(
            content_type=content_type,
            object_id=object_id
        )

        # Serialize image data
        image_data = [
            {
                'url': image.image.url,
                'thumbnail_url': image.thumbnail_url,
                'filename': image.image.name.split('/')[-1] if image.image else None,
                'caption': image.caption,
                'author': image.author,
                'license': image.license.name if image.license else None,
                'source': image.source
            }
            for image in images
        ]

        return Response({'images': image_data})

# URL patterns for the API
urlpatterns = router.urls 
urlpatterns += [
    path('get_images/', GetImagesAPIView.as_view(), name='get_images'),
    path('get_layers/', GeoLayerListView.as_view(), name='get_layers'),
]
