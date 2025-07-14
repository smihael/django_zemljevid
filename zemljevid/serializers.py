from rest_framework_gis import serializers as gis_serializers
from .models import MemorialStatus

class FullGeoEntrySerializer(gis_serializers.GeoFeatureModelSerializer):
    """Base serializer for detailed geo feature data with all fields."""
    class Meta:
        abstract = True
        fields = '__all__'
        #fields = ('geom', 'id', 'name')
        geo_field = 'geom'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        exclude_fields = ['hidden', 'remarks']  
        for field in exclude_fields:
            self.fields.pop(field, None)

    def to_representation(self, instance):
        geojson = super().to_representation(instance)
        model = getattr(self.Meta, 'model', None)

        if 'properties' in geojson and model:
            new_properties = {}
            for field_name, value in geojson['properties'].items():
                verbose_name = field_name
                try:
                    model_field = model._meta.get_field(field_name)
                    verbose_name = model_field.verbose_name
                except Exception:
                    serializer_field = self.fields.get(field_name)
                    if serializer_field and getattr(serializer_field, 'label', None):
                        verbose_name = serializer_field.label

                if field_name.lower() == 'status':
                    try:
                        value = str(MemorialStatus(value).label)
                    except Exception:
                        pass

                new_properties[str(verbose_name)] = value

            geojson['properties'] = new_properties

        return geojson

# this is too slow, so we will use a custom viewset for lists
