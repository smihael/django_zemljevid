import django_tables2 as tables
import django_filters
from django_filters import LookupChoiceFilter
from django.utils.safestring import mark_safe
from django.urls import reverse

from .models import (
    PartisanMemorial,
    PartisanHospital,
    PartisanNaming,
    PartisanPointsWithoutMemorial,
    OtherMemorials
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
                    ('icontains', 'vsebuje'),
                    ('iexact', 'se ujema popolnoma'),
                    ('istartswith', 'začne se z'),
                    ('iendswith', 'konča se z'),
                ]
            )
        elif field_type in ('DateField', 'DateTimeField'):
            filters[field.name] = django_filters.DateFromToRangeFilter(field_name=field.name, label=field.verbose_name)
    return filters

# List of model classes
models_list = [
    PartisanMemorial,
    PartisanHospital,
    PartisanNaming,
    PartisanPointsWithoutMemorial,
    OtherMemorials
]

htmlfield_types = ('HTMLField', 'RichTextField', 'TextField')

# Dynamically create table and filter classes
for model in models_list:
    model_name = model.__name__

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
    table_class = type(
        f"{model_name}Table",
        (tables.Table,),
        {
            **render_methods,
            "Meta": type("Meta", (), {
                "model": model,
                "template_name": "django_tables2/bootstrap4.html",
                "exclude": ["geom", "hidden"],
                "row_attrs": {
                    "data-lat": lambda record: record.geom.y if getattr(record, "geom", None) else "",
                    "data-lng": lambda record: record.geom.x if getattr(record, "geom", None) else "",
                }
            })
        }
    )

    # Create filter class
    filter_fields = add_lookup_choice_filters(model, exclude=['geom', 'hidden'])
    filter_class = type(
        f"{model_name}Filter",
        (django_filters.FilterSet,),
        {
            **filter_fields,
            "Meta": type("Meta", (), {
                "model": model,
                "exclude": ['geom', 'hidden']
            })
        }
    )

    # Register classes globally (optional but useful)
    globals()[f"{model_name}Table"] = table_class
    globals()[f"{model_name}Filter"] = filter_class
