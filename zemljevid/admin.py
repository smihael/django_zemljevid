from django.contrib import admin

# Register your models here.

from mapwidgets.widgets import LeafletPointFieldWidget, GoogleMapPointFieldWidget
from leaflet.admin import LeafletGeoAdmin

from django.contrib.gis.db.models import PointField

from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey
from django import forms
from django.http import JsonResponse
from django.urls import path
from django.utils.html import mark_safe

from zemljevid.models import *

from django.utils.translation import gettext_lazy as _

from django.contrib.admin.models import LogEntry
@admin.register(LogEntry)
class LogEntryAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
    
    list_display = ('action_time', 'user', 'object_repr', 'action_flag', 'change_message')

class CommonGeoAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'entry_author', 'entry_date', 'last_changed')
    list_filter = ('entry_date', 'last_changed')
    search_fields = ['name', 'description']
    formfield_overrides = {
        PointField: {"widget": LeafletPointFieldWidget},
    }

for model in [
    PartisanHospital,
    PartisanNaming,
    PartisanPointsWithoutMemorial,
    OtherMemorials,
    CroatianPartisanMemorial,
    AnonymousSubmission
]:
    admin.site.register(model, CommonGeoAdmin)


class PartisanMemorialAdmin(CommonGeoAdmin):
    list_display = tuple(CommonGeoAdmin.list_display) + ('get_memorial_categories',)
    list_filter = tuple(CommonGeoAdmin.list_filter) + ('memorial_categories',)

    def get_memorial_categories(self, obj):
        return ", ".join([c.name for c in obj.memorial_categories.all()])
    get_memorial_categories.short_description = "Categories"

admin.site.register(PartisanMemorial, PartisanMemorialAdmin)


admin.site.register(PartisanTrail, LeafletGeoAdmin)

for model in [
    #MemorialStatus, 
    #MemorialType, 
    ImageLicense,
    ExternalProject, 
    PartisanMemorialCategory,
    TranslatedContent]:
    admin.site.register(model)

@admin.register(ConnectedExternalEntry)
class ConnectedExternalEntryAdmin(admin.ModelAdmin):
    list_display = ('external_project', 'external_id')
    #autocomplete_fields = ['object_id'] 

class MemorialImageAdminForm(forms.ModelForm):
    object_id = forms.ChoiceField(label="Object", required=True)

    class Meta:
        model = MemorialImage
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        content_type = self.initial.get("content_type") or self.data.get("content_type")
        if content_type:
            try:
                ct = ContentType.objects.get(pk=content_type)
                model_class = ct.model_class()
                if model_class and issubclass(model_class, AbstractGeoEntry):
                    choices = [(obj.pk, str(obj)) for obj in model_class.objects.all()]
                    self.fields["object_id"].choices = choices
            except ContentType.DoesNotExist:
                self.fields["object_id"].choices = []
        else:
            self.fields["object_id"].choices = []
        # When editing, make fields hidden so their value is submitted
        if self.instance and self.instance.pk:
            self.fields["content_type"].widget = forms.HiddenInput()
            self.fields["object_id"].widget = forms.HiddenInput()

from django.contrib.admin import SimpleListFilter
class AbstractGeoEntryContentTypeFilter(SimpleListFilter):
    title = _('content type')
    parameter_name = 'content_type'

    def lookups(self, request, model_admin):
        allowed_cts = ContentType.objects.filter(
            pk__in=[ct.pk for ct in ContentType.objects.all()
                    if hasattr(ct.model_class(), '__mro__') and AbstractGeoEntry in ct.model_class().__mro__]
        )
        return [(ct.pk, ct.name) for ct in allowed_cts]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(content_type_id=self.value())
        return queryset

@admin.register(MemorialImage)
class MemorialImageAdmin(admin.ModelAdmin):
    form = MemorialImageAdminForm
    list_display = ('image_tag', 'caption', 'copyright', 'object_name')
    list_filter = (AbstractGeoEntryContentTypeFilter, 'license', 'author', 'source')
    search_fields = ('caption', 'author', 'license__name')
    list_per_page = 20

    def image_tag(self, obj):
        if obj.thumbnail_url:
            return mark_safe(f'<img src="{obj.thumbnail_url}" style="max-height:100px; max-width:150px;" />')
        return ""
    image_tag.short_description = "Image preview"

    def image_preview(self, obj):
        if obj and obj.thumbnail_url:
            #            return mark_safe(f'<a href="{obj.image.url}" target="_blank"><img src="{obj.thumbnail_url}" style="max-height:200px; max-width:300px;" /></a>')

            return mark_safe(f'<img src="{obj.thumbnail_url}" style="max-height:200px; max-width:300px;" />')
        return ""
    image_preview.short_description = _("Current image thumbnail")

    def object_name(self, obj):
        ct = obj.content_type.model if obj.content_type else None
        name = str(obj.content_object) if obj.content_object else obj.object_id
        return f"{name}" if ct else name
    
    object_name.short_description = _("Object name")

    def copyright(self, obj):
        lines = []
        if obj.author:
            lines.append(str(obj.author))
        if obj.license:
            lines.append(str(obj.license))
        if obj.source:
            lines.append(str(obj.source))
        if lines:
            return mark_safe("<br>".join(lines))
        return _("Unknown")

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "content_type":
            allowed_models = [
                ct.pk for ct in ContentType.objects.all()
                if hasattr(ct.model_class(), '__mro__') and
                   AbstractGeoEntry in ct.model_class().__mro__
            ]
            kwargs["queryset"] = ContentType.objects.filter(pk__in=allowed_models)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                'get-objects/',
                self.admin_site.admin_view(self.get_objects_view),
                name='memorialimage-get-objects',
            ),
        ]
        return custom_urls + urls

    def get_objects_view(self, request):
        content_type_id = request.GET.get('content_type')
        q = request.GET.get('q', '')
        object_id = request.GET.get('object_id')
        page = int(request.GET.get('page', 1))
        page_size = 20
        results = []
        more = False
        if content_type_id:
            try:
                ct = ContentType.objects.get(pk=content_type_id)
                model_class = ct.model_class()
                if model_class and issubclass(model_class, AbstractGeoEntry):
                    if object_id:
                        obj = model_class.objects.filter(pk=object_id).first()
                        if obj:
                            results = [{"id": obj.pk, "text": str(obj)}]
                            return JsonResponse({"results": results, "more": False})
                    qs = model_class.objects.all()
                    if q:
                        if hasattr(model_class, 'name'):
                            qs = qs.filter(name__icontains=q)
                            is_queryset = True
                        else:
                            qs = [obj for obj in qs if q.lower() in str(obj).lower()]
                            is_queryset = False
                    else:
                        is_queryset = True
                    total = qs.count() if is_queryset else len(qs)
                    start = (page - 1) * page_size
                    end = start + page_size
                    if is_queryset:
                        objects = qs.order_by('pk')[start:end]
                    else:
                        objects = qs[start:end]
                    results = [{"id": obj.pk, "text": str(obj)} for obj in objects]
                    more = end < total
            except ContentType.DoesNotExist:
                pass
        return JsonResponse({"results": results, "more": more})

    def get_readonly_fields(self, request, obj=None):
        base = list(super().get_readonly_fields(request, obj))
        if obj:  # editing
            base += ["content_type_display", "object_id_display"]
        return tuple(base)

    def content_type_display(self, obj):
        return obj.content_type
    content_type_display.short_description = "Content type"

    def object_id_display(self, obj):
        return str(obj.content_object) if obj.content_object else obj.object_id
    object_id_display.short_description = "Object"

    def get_fields(self, request, obj=None):
        # List all fields you want to show, in order, except id
        base_fields = [f.name for f in self.model._meta.fields if f.name != "id"]
        if obj:
            # Show display fields instead of editable ones, but keep the real fields for hidden input
            fields = ["content_type_display", "object_id_display"] + base_fields
            # Remove duplicates, keep order (display fields first, then hidden fields)
            seen = set()
            result = []
            for f in fields:
                if f not in seen:
                    result.append(f)
                    seen.add(f)
            return result
        else:
            # Show editable fields when adding
            return base_fields

    def get_search_results(self, request, queryset, search_term):
        queryset, use_distinct = super().get_search_results(request, queryset, search_term)
        # Search related object's name field
        if search_term:
            # Only consider AbstractGeoEntry subclasses
            from django.db.models import Q
            related_ids = []
            for ct in ContentType.objects.all():
                model_class = ct.model_class()
                if model_class and hasattr(model_class, 'name') and hasattr(model_class, '__mro__') and AbstractGeoEntry in model_class.__mro__:
                    matches = model_class.objects.filter(name__icontains=search_term).values_list('pk', flat=True)
                    if matches:
                        related_ids.extend([(ct.pk, pk) for pk in matches])
            if related_ids:
                q = Q()
                for ct_pk, obj_pk in related_ids:
                    q |= Q(content_type_id=ct_pk, object_id=obj_pk)
                queryset |= self.model.objects.filter(q)
        return queryset, use_distinct

    class Media:
        js = (
            "https://cdn.jsdelivr.net/npm/select2@4.1.0-rc.0/dist/js/select2.min.js",
            "admin/js/memorialimage_dynamic_object_id.js",
        )
        css = {
            "all": (
                "https://cdn.jsdelivr.net/npm/select2@4.1.0-rc.0/dist/css/select2.min.css",
            )
        }

