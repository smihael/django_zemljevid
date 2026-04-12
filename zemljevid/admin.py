import os

from django.contrib import admin
from django.contrib import messages

# Register your models here.

from mapwidgets.widgets import LeafletPointFieldWidget, GoogleMapPointFieldWidget
from leaflet.admin import LeafletGeoAdmin

from django.contrib.gis.db.models import PointField

from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.admin import GenericTabularInline
from django import forms
from django.http import JsonResponse
from django.urls import path
from django.urls import reverse, NoReverseMatch
from django.utils.html import mark_safe
from django.utils.html import format_html
from django.db.models import Max
from django.db import transaction

from zemljevid.models import *

from django.utils.translation import gettext_lazy as _

from django.contrib.admin.models import LogEntry
from django.contrib.admin.widgets import AdminDateWidget


class AdminSlDateWidget(AdminDateWidget):
    pass


@admin.register(LogEntry)
class LogEntryAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
    
    list_display = ('action_time', 'user', 'object_link', 'action_flag', 'change_message')

    def object_link(self, obj):
        if not obj.content_type_id or not obj.object_id:
            return obj.object_repr

        app_label = obj.content_type.app_label
        model = obj.content_type.model
        try:
            url = reverse(f'admin:{app_label}_{model}_change', args=[obj.object_id])
            return format_html('<a href="{}">{}</a>', url, obj.object_repr)
        except NoReverseMatch:
            return obj.object_repr
    object_link.short_description = _('Object')
    object_link.admin_order_field = 'object_repr'


class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True


class MultipleFileField(forms.FileField):
    widget = MultipleFileInput

    def clean(self, data, initial=None):
        single_file_clean = super().clean
        if not data:
            return []
        if isinstance(data, (list, tuple)):
            return [single_file_clean(d, initial) for d in data]
        return [single_file_clean(data, initial)]


class MemorialBulkImageUploadAdminForm(forms.ModelForm):
    bulk_images = MultipleFileField(
        required=False,
        label=_("Upload multiple images"),
        help_text=_("You can select multiple files. They will be added to this memorial and appended at the end of the current order."),
    )
    bulk_caption = forms.CharField(
        required=False,
        label=_("Caption for all uploaded images"),
    )
    bulk_author = forms.CharField(
        required=False,
        label=_("Author for all uploaded images"),
    )
    bulk_date_taken = forms.DateField(
        required=False,
        label=_("Date taken for all uploaded images"),
        widget=AdminSlDateWidget(),
        input_formats=['%d. %B %Y', '%d. %b %Y', '%d.%m.%Y', '%d. %m. %Y', '%Y-%m-%d'],
    )
    bulk_date_mode = forms.ChoiceField(
        required=False,
        label=_("Date mode for all uploaded images"),
        choices=ImageDateMode.choices,
        initial=ImageDateMode.EXACT,
    )
    bulk_date_approx_text = forms.CharField(
        required=False,
        label=_("Approximate date text for all uploaded images"),
        help_text=_("Examples: around 1970, early 1950s, before WWII"),
    )
    bulk_license = forms.ModelChoiceField(
        required=False,
        queryset=ImageLicense.objects.all(),
        label=_("License for all uploaded images"),
    )
    bulk_source = forms.CharField(
        required=False,
        label=_("Source for all uploaded images"),
    )

    class Meta:
        fields = '__all__'

    def clean(self):
        cleaned_data = super().clean()
        files = self.files.getlist('bulk_images')
        if not files:
            return cleaned_data

        mode = cleaned_data.get('bulk_date_mode') or ImageDateMode.EXACT
        date_taken = cleaned_data.get('bulk_date_taken')
        date_approx_text = cleaned_data.get('bulk_date_approx_text')

        if mode == ImageDateMode.EXACT:
            if not date_taken:
                self.add_error('bulk_date_taken', _('Please provide Date taken for exact date mode.'))
            cleaned_data['bulk_date_approx_text'] = None
            return cleaned_data

        cleaned_data['bulk_date_taken'] = None

        if mode == ImageDateMode.APPROXIMATE:
            if not date_approx_text:
                self.add_error('bulk_date_approx_text', _('Please provide approximate date text.'))
            return cleaned_data

        if mode == ImageDateMode.UNKNOWN:
            cleaned_data['bulk_date_approx_text'] = None

        return cleaned_data

    class Media:
        js = ('admin/js/memorialimage_bulk_toggle.js',)


class MemorialImageInlineForm(forms.ModelForm):
    class Meta:
        model = MemorialImage
        fields = '__all__'
        widgets = {
            'date_taken': AdminSlDateWidget(),
        }


class MemorialImageInline(GenericTabularInline):
    model = MemorialImage
    form = MemorialImageInlineForm
    ct_field = 'content_type'
    ct_fk_field = 'object_id'
    extra = 0
    ordering = ('order', 'id')
    fields = (
        'drag_handle', 'image_preview', 'image', 'order', 'caption', 'author',
        'date_mode', 'date_taken', 'date_approx_text', 'license', 'source'
    )
    readonly_fields = ('drag_handle', 'image_preview',)

    class Media:
        js = (
            'admin/js/memorialimage_inline_sort.js',
            'admin/js/memorialimage_date_mode_guard.js',
        )
        css = {
            'all': ('admin/css/memorialimage_inline_sort.css',)
        }

    def drag_handle(self, obj):
        return mark_safe('<span class="memorialimage-drag-handle" title="Drag to reorder" aria-label="Drag to reorder">↕</span>')
    drag_handle.short_description = _("Move")

    def image_preview(self, obj):
        if obj and getattr(obj, 'thumbnail_url', None):
            return mark_safe(f'<img src="{obj.thumbnail_url}" style="max-height:80px; max-width:120px;" />')
        return ""
    image_preview.short_description = _("Preview")

class CommonGeoAdmin(admin.ModelAdmin):
    form = MemorialBulkImageUploadAdminForm
    list_display = ('id', 'name', 'entry_author', 'entry_date', 'last_changed')
    list_filter = ('entry_date', 'last_changed')
    search_fields = ['name', 'description']
    formfield_overrides = {
        PointField: {"widget": LeafletPointFieldWidget},
    }
    inlines = [MemorialImageInline]

    def change_view(self, request, object_id, form_url='', extra_context=None):
        obj = self.get_object(request, object_id)
        if obj:
            content_type = ContentType.objects.get_for_model(obj, for_concrete_model=False)
            broken = [
                img for img in MemorialImage.objects.filter(
                    content_type=content_type, object_id=obj.pk
                )
                if img.image and not img.image.storage.exists(img.image.name)
            ]
            if broken:
                names = ', '.join(os.path.basename(img.image.name) for img in broken)
                self.message_user(
                    request,
                    _("Warning: the following linked image files are missing from disk "
                      "and will be skipped during save: %(names)s") % {'names': names},
                    level=messages.WARNING,
                )
        return super().change_view(request, object_id, form_url, extra_context)

    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change)

        files = request.FILES.getlist('bulk_images')
        if not files:
            return

        obj = form.instance
        content_type = ContentType.objects.get_for_model(obj, for_concrete_model=False)
        caption = form.cleaned_data.get('bulk_caption')
        author = form.cleaned_data.get('bulk_author')
        date_taken = form.cleaned_data.get('bulk_date_taken')
        date_mode = form.cleaned_data.get('bulk_date_mode') or ImageDateMode.EXACT
        date_approx_text = form.cleaned_data.get('bulk_date_approx_text')
        license_obj = form.cleaned_data.get('bulk_license')
        source = form.cleaned_data.get('bulk_source')

        with transaction.atomic():
            obj.__class__.objects.select_for_update().filter(pk=obj.pk).first()

            max_order = (
                MemorialImage.objects.filter(content_type=content_type, object_id=obj.pk)
                .aggregate(max_order=Max('order'))
                .get('max_order')
                or 0
            )

            for index, uploaded_file in enumerate(files, start=1):
                MemorialImage.objects.create(
                    content_type=content_type,
                    object_id=obj.pk,
                    image=uploaded_file,
                    order=max_order + index,
                    caption=caption,
                    author=author,
                    date_taken=date_taken,
                    date_mode=date_mode,
                    date_approx_text=date_approx_text,
                    license=license_obj,
                    source=source,
                )


class PartisanNamingAdminForm(MemorialBulkImageUploadAdminForm):
    class Meta(MemorialBulkImageUploadAdminForm.Meta):
        model = PartisanNaming
        fields = '__all__'
        labels = {
            'memorial_start': _('Time of naming, designation'),
        }


class PartisanNamingAdmin(CommonGeoAdmin):
    form = PartisanNamingAdminForm
    exclude = ('memorial_text',)


for model in [
    PartisanHospital,
    PartisanPointsWithoutMemorial,
    OtherMemorials,
    CroatianPartisanMemorial,
    AnonymousSubmission
]:
    admin.site.register(model, CommonGeoAdmin)

admin.site.register(PartisanNaming, PartisanNamingAdmin)


class PartisanMemorialAdmin(CommonGeoAdmin):
    list_display = tuple(CommonGeoAdmin.list_display) + ('get_memorial_categories',)
    list_filter = tuple(CommonGeoAdmin.list_filter) + ('memorial_categories',)

    def get_memorial_categories(self, obj):
        return ", ".join([c.name for c in obj.memorial_categories.all()])
    get_memorial_categories.short_description = "Categories"

admin.site.register(PartisanMemorial, PartisanMemorialAdmin)


admin.site.register(PartisanTrail, LeafletGeoAdmin)
from .models import OkupacijskeMeje

@admin.register(OkupacijskeMeje)
class OkupacijskeMejeAdmin(LeafletGeoAdmin):
    list_display = ('id', 'name', 'color_swatch', 'source')
    search_fields = ('name', 'description', 'source')
    def color_swatch(self, obj):
        if obj.color:
            return mark_safe(f'<span style="display:inline-block;width:24px;height:16px;background:{obj.color};border:1px solid #333"></span> {obj.color}')
        return ''
    color_swatch.short_description = 'Color'

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
        widgets = {
            'date_taken': AdminSlDateWidget(),
        }

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
    list_display = ('image_tag', 'order', 'caption', 'date_info', 'copyright', 'object_name')
    list_filter = (AbstractGeoEntryContentTypeFilter, 'license', 'author', 'source')
    search_fields = ('caption', 'author', 'license__name')
    list_per_page = 20
    ordering = ('content_type', 'object_id', 'order', 'id')

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

    def date_info(self, obj):
        if obj.date_mode == ImageDateMode.EXACT:
            return obj.date_taken or _("Missing exact date")
        if obj.date_mode == ImageDateMode.APPROXIMATE:
            return f"{obj.get_date_mode_display()}: {obj.date_approx_text or '-'}"
        return obj.get_date_mode_display()
    date_info.short_description = _("Date")

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
            "admin/js/memorialimage_date_mode_guard.js",
        )
        css = {
            "all": (
                "https://cdn.jsdelivr.net/npm/select2@4.1.0-rc.0/dist/css/select2.min.css",
            )
        }

