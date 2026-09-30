import django_tables2 as tables
import django_filters
from django.contrib.gis.db.models.functions import GeoFunc
from django.db.models import Exists, FloatField, OuterRef
from django_filters import LookupChoiceFilter
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _
from django.urls import reverse

from .models import (
    PartisanMemorial,
    CroatianPartisanMemorial,
    PartisanHospital,
    PartisanNaming,
    PartisanPointsWithoutMemorial,
    OtherMemorials,
    OsamosvojitvenaObelezja,
    PartisanTrail,
    ConnectedExternalEntry,
    ExternalProject,
    MemorialImage,
)

import bleach


def add_lookup_choice_filters(model, exclude=None):
    exclude = exclude or []
    filters = {}
    for field in model._meta.get_fields():
        if field.name in exclude or field.auto_created:
            continue
        field_type = getattr(field, 'get_internal_type', lambda: None)()
        if field_type in ('CharField', 'TextField', 'HTMLField', 'RichTextField'):
            filters[field.name] = LookupChoiceFilter(
                field_name=field.name,
                lookup_choices=[
                    ('icontains', _('contains')),
                    ('iexact', _('matches exactly')),
                    ('istartswith', _('starts with')),
                    ('iendswith', _('ends with')),
                ]
            )
        elif field_type in ('DateField', 'DateTimeField'):
            filters[field.name] = django_filters.DateFromToRangeFilter(field_name=field.name, label=field.verbose_name)
    return filters


class XCoord(GeoFunc):
    function = 'ST_X'
    output_field = FloatField()


class YCoord(GeoFunc):
    function = 'ST_Y'
    output_field = FloatField()


def add_coordinate_filters(model):
    filters = {}
    geom_field = next((field for field in model._meta.get_fields() if field.name == 'geom'), None)
    if geom_field is None:
        return filters

    geom_type = getattr(geom_field, 'get_internal_type', lambda: None)()
    if geom_type != 'PointField':
        return filters

    def make_coord_filter(axis_name, lookup_expr, label):
        def coord_filter_method(queryset, name, value):
            if value in (None, ''):
                return queryset
            annotation_name = f'geom_{axis_name}'
            value_expr = XCoord('geom') if axis_name == 'x' else YCoord('geom')
            return queryset.annotate(**{annotation_name: value_expr}).filter(**{f'{annotation_name}__{lookup_expr}': value})
        return django_filters.NumberFilter(method=coord_filter_method, label=label)

    filters['geom_x_min'] = make_coord_filter('x', 'gte', _('X from'))
    filters['geom_x_max'] = make_coord_filter('x', 'lte', _('X to'))
    filters['geom_y_min'] = make_coord_filter('y', 'gte', _('Y from'))
    filters['geom_y_max'] = make_coord_filter('y', 'lte', _('Y to'))
    filters['geom_missing'] = django_filters.BooleanFilter(
        field_name='geom',
        lookup_expr='isnull',
        label=_('Without coordinates'),
    )
    return filters


def add_relation_filters(model):
    def related_entries(related_model):
        return related_model.objects.filter(
            content_type__app_label=model._meta.app_label,
            content_type__model=model._meta.model_name,
            object_id=OuterRef('pk'),
        )

    def filter_external_project(queryset, name, value):
        if not value:
            return queryset
        matching_entries = related_entries(ConnectedExternalEntry).filter(
            external_project_id=value.pk,
        )
        return queryset.filter(Exists(matching_entries))

    def filter_relation_presence(related_model):
        def filter_method(queryset, name, value):
            if value in (None, ''):
                return queryset
            related_queryset = related_entries(related_model)
            if related_model is MemorialImage:
                related_queryset = related_queryset.exclude(image='')
            matching_entries = Exists(related_queryset)
            return queryset.filter(matching_entries if value == 'yes' else ~matching_entries)
        return filter_method

    return {
        'external_project': django_filters.ModelChoiceFilter(
            queryset=ExternalProject.objects.order_by('name'),
            method=filter_external_project,
            label=_('External project'),
            empty_label=_('All projects'),
        ),
        'has_external_links': django_filters.ChoiceFilter(
            method=filter_relation_presence(ConnectedExternalEntry),
            choices=(('yes', _('Has external links')), ('no', _('No external links'))),
            label=_('External links'),
            empty_label=_('All'),
        ),
        'has_images': django_filters.ChoiceFilter(
            method=filter_relation_presence(MemorialImage),
            choices=(('yes', _('Has images')), ('no', _('No images'))),
            label=_('Images'),
            empty_label=_('All'),
        ),
    }

# List of model classes
models_list = [
    PartisanMemorial,
    CroatianPartisanMemorial,
    PartisanHospital,
    PartisanNaming,
    PartisanPointsWithoutMemorial,
    OtherMemorials,
    OsamosvojitvenaObelezja,
    PartisanTrail,
]

htmlfield_types = ('HTMLField', 'RichTextField', 'TextField')

# Dynamically create table and filter classes
for model in models_list:
    model_name = model.__name__
    excluded_table_fields = ['geom', 'hidden']
    excluded_filter_fields = ['geom', 'hidden']

    if model is PartisanNaming:
        excluded_table_fields.append('memorial_text')
        excluded_filter_fields.append('memorial_text')

    excluded_filter_fields.extend(
        [
            field.name
            for field in model._meta.get_fields()
            if getattr(field, 'get_internal_type', lambda: None)() == 'ArrayField'
        ]
    )

    # Prepare render methods for HTML-safe fields
    render_methods = {}
    for field in model._meta.get_fields():
        #print(f"Processing field: {field.name} of type {getattr(field, 'get_internal_type', lambda: None)()}")
        if getattr(field, 'get_internal_type', lambda: None)() in htmlfield_types:
            # define render_<fieldname> function
            def make_renderer(field_name):
                def render_method(self, value):


                    allowed_tags = ['b', 'i', 'u', 'em', 'strong', 'a', 'p', 'ul', 'ol', 'li', 'br']
                    allowed_attributes = {
                        'a': ['href', 'title']
                    }

                    clean_html = bleach.clean(
                        value,
                        tags=allowed_tags,
                        attributes=allowed_attributes,
                        strip=True
                    )


                    return mark_safe(clean_html)
                render_method.__name__ = f"render_{field_name}"
                return render_method
            render_methods[f"render_{field.name}"] = make_renderer(field.name)
        elif getattr(field, 'get_internal_type', lambda: None)() == 'ArrayField':
            def make_array_renderer(field_name):
                def render_method(self, value):
                    return value if value else '—'

                render_method.__name__ = f"render_{field_name}"
                return render_method

            render_methods[f"render_{field.name}"] = make_array_renderer(field.name)

    # Add custom render_id for edit button
    def render_id(self, value, record):
        model_admin = record._meta.model_name
        model_layer = model_admin  # already lowercase
        map_url = reverse('map') + f"?layer={model_layer}&id={value}"
        admin_url = f"/admin/zemljevid/{model_admin}/{value}/change/"
        return mark_safe(
            f'<a href="{admin_url}" class="btn btn-sm btn-outline-primary me-1" title="Uredi"><i class="bi bi-pencil-square"></i></a>'
            f'<a href="{map_url}" class="btn btn-sm btn-outline-success" title="Pokaži na zemljevidu"><i class="bi bi-map"></i></a> '
            f'{value}'
        )
    render_methods['render_id'] = render_id

    # Create table class
    table_attrs = {
        **render_methods,
        "Meta": type("Meta", (), {
            "model": model,
            "template_name": "django_tables2/bootstrap4.html",
            "exclude": excluded_table_fields,
            "row_attrs": {
                "data-lat": lambda record: getattr(record.geom, "y", "") if getattr(record, "geom", None) else "",
                "data-lng": lambda record: getattr(record.geom, "x", "") if getattr(record, "geom", None) else "",
            }
        })
    }

    if model is PartisanNaming:
        table_attrs['memorial_start'] = tables.Column(verbose_name='Čas poimenovanja, oznaka')

    table_class = type(
        f"{model_name}Table",
        (tables.Table,),
        table_attrs
    )

    # Create filter class
    filter_fields = add_lookup_choice_filters(model, exclude=excluded_filter_fields)
    filter_fields.update(add_coordinate_filters(model))
    filter_fields.update(add_relation_filters(model))
    filter_class = type(
        f"{model_name}Filter",
        (django_filters.FilterSet,),
        {
            **filter_fields,
            "Meta": type("Meta", (), {
                "model": model,
                "exclude": excluded_filter_fields
            })
        }
    )

    # Register classes globally (optional but useful)
    globals()[f"{model_name}Table"] = table_class
    globals()[f"{model_name}Filter"] = filter_class
