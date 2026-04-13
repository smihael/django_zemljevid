from django.contrib.gis.db import models
from django.db import models as django_models
from django.db import connection
from django.db import transaction
from tinymce import models as tinymce_models
import re
import os
from PIL import Image
from io import BytesIO
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.contrib.postgres.fields import ArrayField

from django.conf import settings
from django.utils.translation import gettext_lazy as _, gettext_noop
from django.core.validators import RegexValidator, MinValueValidator, MaxValueValidator
from colorfield.fields import ColorField

class MemorialStatus(models.IntegerChoices):
    NA = 0, _('Not specified')
    EXISTING = 1, _('Existing memorials')
    NOT_VISITED = 3, _('Not visited memorials')
    DESTROYED = 2, _('Destroyed memorials')
    DAMAGED = 4, _('Damaged memorials')
    MOVED = 5, _('Moved memorials')
    DEPOSITED = 6, _('Deposited memorials')


class MemorialType(models.TextChoices):
    MONUMENT = 'spomenik', _('Monument')
    STATUE = 'kip', _('Statue')
    PLAQUE = 'plošča', _('Memorial plaque')
    #OBELISK = 'obelisk', _('Obelisk')
    STONE = 'spominski kamen', _('Memorial stone')
    STOLPERSTEIN = 'spotikavec', _('Stolperstein')
    BUST = 'doprsni kip', _('Bust')
    TOMBSTONE = 'nagrobnik', _('Tombstone')
    GRAVE = 'grob', _('Grave')
    SCULPTURE = 'skulptura', _('Sculpture')
    MUSEUM = 'muzej', _('Museum')
    #AIRPLANE = 'avion', _('Airplane')
    #ANCHOR = 'sidro', _('Anchor')
    INFOTABLE = 'infotabla', _('Info table')
    MEMORIAL_ROOM = 'spominska soba', _('Memorial room')
    #DIRECTION_SIGN = 'smerokaz', _('Direction sign')
    OTHER = 'durgo', _('Other')
    CHAPEL = 'kapelica', _('Chapel')
    SIGN = 'zmamenje', _('Sign')

    

class PartisanMemorialCategory(models.Model):
    """
    Model for Partisan memorial categories.
    """

    name = django_models.CharField(max_length=255, unique=True, verbose_name=_('Category Name'))

    description = django_models.TextField(blank=False, null=True, verbose_name=_('Description'),
                                          help_text=_('Enter a description for the category.'))
    


    #icon = django_models.CharField(max_length=255, blank=True, null=True, verbose_name=_('Icon'),
    #                               help_text=_('Enter the icon class for the category. This will be used to display the icon on the map.'))

    class Meta:
        verbose_name = _('Partisan Memorial Category')
        verbose_name_plural = _('Partisan Memorial Categories')

    def __str__(self):
        return self.name

class AbstractGeoEntry(models.Model):
    """
    Abstract base class for models with a geometry field.
    """
    id = models.AutoField(primary_key=True)
    geom = models.PointField(blank=True, null=True)
    name = django_models.CharField(max_length=500, blank=True, null=True, verbose_name=_('Name'))
    description = tinymce_models.HTMLField(blank=True, null=True, verbose_name=_('Description'))

    @staticmethod
    def _description_has_images(value):
        if not value:
            return False
        return re.search(r'<img\b', value, flags=re.IGNORECASE)

    @staticmethod
    def description_has_links(value):
        if not value:
            return False
        return (
            re.search(r'<a\b', value, flags=re.IGNORECASE)
            or re.search(r'(https?://|www\.)', value, flags=re.IGNORECASE)
        )

    def clean(self):
        super().clean()
        if not self._description_has_images(self.description):
            return

        raise ValidationError({
            'description': _('Images are not allowed in Description. Upload images via gallery.')
        })

    class Meta:
        abstract = True
        managed = False

class Memorial(AbstractGeoEntry):
    """
    Model for memorials with a gallery field.
    """
    
    memorial_access = django_models.TextField(null=True, blank=True, verbose_name=_('Location and access'),
                                          help_text=_('Enter information about access to the memorial'), db_collation='slovenian_icu')
    memorial_text = tinymce_models.HTMLField(blank=True, null=True, verbose_name=_('Text on the memorial'), db_collation='slovenian_icu')
    memorial_author = django_models.CharField(max_length=255, blank=True, null=True, verbose_name=_('Author of the memorial'), db_collation='slovenian_icu')
    memorial_start = django_models.CharField(max_length=255, blank=True, null=True, verbose_name=_('Time of creation'), db_collation='slovenian_icu')

    status = models.IntegerField(choices=MemorialStatus.choices, default=MemorialStatus.NA, blank=True, null=True, verbose_name=_('Status'))
    vandalism_years = ArrayField(
        base_field=django_models.PositiveSmallIntegerField(
            validators=[MinValueValidator(1900), MaxValueValidator(2200)]
        ),
        blank=True,
        default=list,
        verbose_name=_('Year of vandalization'),
        help_text=_('Enter one or more years when the memorial was vandalized, comma separated.')
    )
    
    remarks = django_models.TextField(blank=True, null=True, verbose_name=_('Remarks'),
                                      help_text=_('Enter additional remarks. These will not be displayed on the map, but will be saved in the database and can be used to filter memorials within the editor.'))
    entry_author = django_models.TextField(max_length=255, blank=True, null=True, verbose_name=_('Entry author'),
                                           help_text=_('Enter the names of the authors/reporters.'))
    entry_date = models.DateTimeField(auto_now_add=True, null=True, blank=True, verbose_name=_('Entry date'))
    last_changed = models.DateTimeField(auto_now=True, null=True, blank=True, verbose_name=_('Last changed'))

    changes = django_models.TextField(blank=True, null=True,
        verbose_name=_('Changes, supplements, corrections'),
        help_text=_('Here we enter what we have changed, added, or corrected in the existing record, and current events related to the memorial. We sign and date the record.')
    )

    hidden = django_models.BooleanField(default=False, verbose_name=_('Hidden (will not be displayed on the map)'),
                                        help_text=_('If checked, the memorial will not be displayed on the map, but will still be saved in the database and can be edited'))

    class Meta:
        verbose_name = _('Memorial')
        verbose_name_plural = _('Memorials')
        abstract = True

    def __str__(self):
        return self.name + " (" + str(self.pk) + ")"



class AbstractPartisanMemorial(Memorial):
    """
    Model for Partisan memorials.
    """

    memorial_type = models.CharField(
        max_length=255,
        choices=MemorialType.choices,
        default=MemorialType.MONUMENT,
        verbose_name=_('Type of memorial'),
        help_text=_('Select the type of memorial'),
        blank=True, null=True
    )

    obcina = django_models.CharField(
        max_length=255, blank=True, null=True, verbose_name=_('Municipality'),
        help_text=_('Enter the name of the municipality where the memorial is located.'), db_collation='slovenian_icu'
    )

    katastrski_podatki = django_models.CharField(
        max_length=500, blank=True, null=True, verbose_name=_('Cadastral data'),
        help_text=_('Enter cadastral data if available.')
    )

    icon = 'star-icon'

    class Meta:
        abstract = True

class AnonymousSubmission(AbstractPartisanMemorial):

    class Meta:
        verbose_name = 'PREDLOG'
        verbose_name_plural = 'PREDLAGANI VNOSI (zunanji uporabniki)'

    def __str__(self):
        return f"Predlog: {self.name} ({self.pk})"
    
class PartisanMemorial(AbstractPartisanMemorial):
    """
    Model for Partisan memorials.
    """

    icon = 'star-icon'

    memorial_categories = django_models.ManyToManyField(
        PartisanMemorialCategory, blank=True, verbose_name=_('Partisan Memorial Categories'),
        help_text=_('Select one or more categories for the memorial.')
    )

    class Meta:
        verbose_name = _('Partisan memorial')
        verbose_name_plural = _('Partisan memorials')

    def __str__(self):
        return f"Partizanski spomenik: {self.name} ({self.pk})"
    
class CroatianPartisanMemorial(AbstractPartisanMemorial):
    """
    Model for Croatian Partisan memorials.
    """
    icon = 'star-icon'

    class Meta:
        verbose_name = _('Croatian Partisan memorial')
        verbose_name_plural = _('Croatian Partisan memorials')

    def __str__(self):
        return f"Hrvatski partizanski spomenik: {self.name} ({self.pk})"

class PartisanHospital(Memorial):
    icon = 'hospital'
    obdobje_delovanja = django_models.CharField(
        max_length=255, blank=True, null=True, verbose_name=_('Period of operation'))
    class Meta:
        verbose_name = _('Partisan hospital')
        verbose_name_plural = _('Hospitals')

    def __str__(self):
        return f"Partizanska bolnišnica: {self.name} ({self.pk})"

class PartisanNaming(Memorial):

    icon = 'cross-icon red'

    vrsta_poimenovanja = django_models.CharField(
        max_length=255, blank=True, null=True, verbose_name=_('Type of naming'),
        help_text=_('inscription on the plaque, official document, folk naming'))

    class Meta:
        verbose_name = _('Partisan naming')
        verbose_name_plural = _('Namings')

    def __str__(self):
        return f"Partizansko poimenovanje: {self.name} ({self.pk})"

class PartisanPointsWithoutMemorial(Memorial):
    """
    Model for Partisan points without memorials.
    """

    obcina = django_models.CharField(blank=True, null=True, max_length=255, verbose_name=_('Municipality'))
    katasterski_podatki = django_models.CharField(blank=True, null=True, max_length=255, verbose_name=_('Cadastral data'))

    icon = 'cross-icon purple'

    class Meta:
        verbose_name = _('Point without memorial')
        verbose_name_plural = _('Points without memorials')

    def __str__(self):
        return f"Partizanska točka brez obeležja: {self.name} ({self.pk})"

class PartisanTrail(models.Model):
    """
    Model for Partisan trails.
    """
    name = django_models.CharField(max_length=255, blank=True, null=True, verbose_name=_('Name of the trail'),
                                   help_text=_('Enter the name of the Partisan trail.'))
    description = django_models.TextField(blank=True, null=True, verbose_name=_('Description of the trail'),
                                          help_text=_('Enter the description of the Partisan trail.'))
    geom = models.MultiLineStringField(blank=True, null=True, verbose_name=_('Geometry of the trail'))

    entry_author = django_models.TextField(max_length=255, blank=True, null=True, verbose_name=_('Entry author'),
                                           help_text=_('Enter the names of the authors/reporters.'))
    entry_date = models.DateTimeField(auto_now_add=True, null=True, blank=True, verbose_name=_('Entry date'))

    hidden = django_models.BooleanField(default=False, verbose_name=_('Hidden (will not be displayed on the map)'),
                                        help_text=_('If checked, the trail will not be displayed on the map, but will still be saved in the database and can be edited'))

    class Meta:
        verbose_name = _('Partisan trail')
        verbose_name_plural = _('Partisan trails')

    def __str__(self):
        return f"Partizanska obhodnica: {self.name} ({self.pk})"

class OtherMemorials(Memorial):
    """
    Model for Obelezja.
    """

    category = django_models.CharField(max_length=255, blank=True, null=True, verbose_name=_('Category'),
                                       help_text=_('mobilized / partisan without insignia / home guard / Rapallo / independence / World War I'))
    
    icon = 'asterisk-icon'

    class Meta:
        verbose_name = _('Other memorial')
        verbose_name_plural = _('Other memorials')

    def __str__(self):
        return f"Obeležje: {self.name} ({self.pk})"

class OkupacijskeMeje(models.Model):
    """Model for occupancy/occupation borders (Okupacijske meje)."""
    name = django_models.CharField(max_length=255, blank=True, null=True, verbose_name=_('Name'))
    description = django_models.TextField(blank=True, null=True, verbose_name=_('Description'))
    geom = models.MultiLineStringField(blank=True, null=True, verbose_name=_('Border geometry'))
    source = django_models.CharField(max_length=255, blank=True, null=True, verbose_name=_('Source'))
    color = ColorField(default='#FF0000', blank=True, null=True, verbose_name=_('Color'), help_text=_('Color used to style this border on the map.'))
    hidden = django_models.BooleanField(default=False, verbose_name=_('Hidden (will not be displayed on the map)'))

    class Meta:
        verbose_name = _('Occupation border')
        verbose_name_plural = _('Occupation borders')

    def __str__(self):
        return self.name or f"Meja {self.pk}"
    
# ExternalProject model
class ExternalProject(models.Model):
    identifier = models.CharField(max_length=255, primary_key=True)  # Make identifier the primary key
    name = models.CharField(max_length=255)
    description = models.CharField(max_length=255, blank=True, null=True, verbose_name=_('Description'),
                            help_text=_('Description of the external project. Hints for the user, which part of the link to fill in, etc.'))
    url = models.URLField(blank=True, null=True, verbose_name=_('URL pattern'), 
                          help_text=_('URL pattern for the connected entry. Use [ID] as placeholder.'))
    unique_connection = models.BooleanField(default=False)  # To decide if connections should be unique

    def __str__(self):
        return self.name
    
    class Meta:
        verbose_name = _('External project')
        verbose_name_plural = _('External projects')

# ConnectedExternalEntry model
class ConnectedExternalEntry(models.Model):
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')

    external_project = models.ForeignKey(ExternalProject, on_delete=models.CASCADE)
    external_id = models.CharField(max_length=255, blank=True, null=True, verbose_name=_('External ID'), help_text=_('ID of the object in the external database. This will be used to construct the URL based on the defined pattern.'))
    additional_info = models.CharField(max_length=255, blank=True, null=True, verbose_name=_('Additional info'), help_text=_('Additional information about the connection, such as name of the object (when there are many entries for the same monument).'))
    order = models.PositiveIntegerField(
        default=0,
        db_index=True,
        verbose_name=_('Order'),
        help_text=_('Display order of connected entries for the same object (lower value is shown first).')
    )

    class Meta:
        verbose_name = _('Connected External Entry')
        verbose_name_plural = _('Connected External Entries')
        ordering = ('order', 'id')

    #def __str__(self):
    #    return f"{self.content_object} - {self.external_project.name} - {self.external_id}" if self.content_object else self.external_id

    def save(self, *args, **kwargs):
        if self._state.adding and self.content_type_id and self.object_id and self.order == 0:
            last_order = (
                type(self).objects.filter(
                    content_type_id=self.content_type_id,
                    object_id=self.object_id,
                )
                .aggregate(max_order=django_models.Max('order'))
                .get('max_order')
                or 0
            )
            self.order = last_order + 1

        # Check the unique_connection field of the associated ExternalProject
        if self.external_project.unique_connection:
            # Ensure uniqueness for this combination
            if ConnectedExternalEntry.objects.filter(
                content_type=self.content_type,
                object_id=self.object_id,
                external_project=self.external_project
            ).exists():
                raise ValueError(_("This connection already exists and must be unique."))
        
        super().save(*args, **kwargs)  # Proceed with the save

class ImageLicense(models.Model):
    """
    Model for image licenses.
    """
    name = models.CharField(max_length=255, unique=True)
    url = models.URLField(blank=True, null=True)

    class Meta:
        db_table = 'image_licenses'

    def __str__(self):
        return self.name


class ImageDateMode(models.TextChoices):
    EXACT = 'exact', _('Exact date')
    APPROXIMATE = 'approximate', _('Approximate date (text)')
    UNKNOWN = 'unknown', _('Unknown date')


from django.core.files.uploadedfile import InMemoryUploadedFile

def validate_image_size(image):
    # Limit the image size to 5MB (5 * 1024 * 1024 bytes)
    max_size = 5 * 1024 * 1024
    try:
        size = image.size
    except (FileNotFoundError, OSError):
        # Broken DB reference to a missing file: do not block saving parent object.
        return
    if size > max_size:
        raise ValidationError(_("The image file is too large. Size should be less than 5 MB."))

class MemorialImage(models.Model):
    
    image = models.ImageField(max_length=500, validators=[validate_image_size], verbose_name=_('Image'),
                              help_text=_('Upload an image related to the memorial.'))
    caption = models.CharField(max_length=255, blank=True, null=True)
    author = models.CharField(max_length=255, blank=True, null=True)
    date_taken = models.DateField(blank=True, null=True, verbose_name=_('Date taken'),
                                  help_text=_('Enter the exact date when the image was taken.'))
    date_mode = models.CharField(
        max_length=16,
        choices=ImageDateMode.choices,
        default=ImageDateMode.EXACT,
        verbose_name=_('Date mode'),
        help_text=_('Choose if date is exact, approximate (text), or unknown.')
    )
    date_approx_text = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name=_('Approximate date (text)'),
        help_text=_('Freeform approximate date, e.g. "around 1970", "early 1950s", "before WWII".')
    )
    license = models.ForeignKey(ImageLicense, on_delete=models.SET_NULL, blank=True, null=True)
    source = models.CharField(max_length=255, blank=True, null=True)
    order = models.PositiveIntegerField(
        default=0,
        db_index=True,
        verbose_name=_('Order'),
        help_text=_('Display order of images for the same memorial (lower value is shown first).')
    )
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')
    
    class Meta:
        verbose_name = _('Memorial Image')
        verbose_name_plural = _('Memorial Images')
        ordering = ('id', 'order')

    def build_image_path(self, filename):
        """
        Canonical relative path for all memorial images:
        <content_type_model>/<object_id>/<filename>
        """
        clean_name = os.path.basename(filename or '')
        if self.content_type and self.object_id and clean_name:
            return f"{self.content_type.model}/{self.object_id}/{clean_name}"
        return clean_name

    def clean(self):
        super().clean()

        if self.content_type_id and self.object_id:
            model_class = self.content_type.model_class() if self.content_type else None
            if not model_class or not issubclass(model_class, AbstractGeoEntry):
                raise ValidationError({
                    'content_type': _('The image can only be associated with a model that inherits from AbstractGeoEntry.')
                })

        if self.date_mode == ImageDateMode.EXACT:
            if not self.date_taken:
                raise ValidationError({'date_taken': _('Please provide Date taken for exact date mode.')})
            self.date_approx_text = None
            return

        if self.date_mode == ImageDateMode.APPROXIMATE:
            if not self.date_approx_text:
                raise ValidationError({'date_approx_text': _('Please provide approximate date text.')})
            self.date_taken = None
            return

        if self.date_mode == ImageDateMode.UNKNOWN:
            self.date_taken = None
            self.date_approx_text = None

    def save(self, *args, **kwargs):
        if self._state.adding and self.content_type_id and self.object_id and self.order == 0:
            last_order = (
                type(self).objects.filter(
                    content_type_id=self.content_type_id,
                    object_id=self.object_id,
                )
                .aggregate(max_order=django_models.Max('order'))
                .get('max_order')
                or 0
            )
            self.order = last_order + 1

        old = None
        if self.pk:
            old = type(self).objects.filter(pk=self.pk).only('image').first()

        has_new_upload = bool(self.image) and not self.image._committed
        should_create_thumbnail = has_new_upload

        # Set upload path dynamically for newly uploaded files.
        # Canonical format is always: <content_type>/<object_id>/<filename>
        if has_new_upload:
            target_name = self.build_image_path(self.image.name)

            if old and old.image:
                old_name = old.image.name
                # Remove old file if path changes.
                if old_name and old_name != target_name and default_storage.exists(old_name):
                    default_storage.delete(old_name)

                # Remove possible legacy/new thumbnail locations for old file.
                for old_thumb_path in self.get_thumbnail_path_candidates(old_name):
                    if default_storage.exists(old_thumb_path):
                        default_storage.delete(old_thumb_path)

            # Overwrite existing target file and thumbnail for deterministic path.
            if target_name and default_storage.exists(target_name):
                default_storage.delete(target_name)
            target_thumb_path = self.get_thumbnail_path(target_name)
            if target_thumb_path and default_storage.exists(target_thumb_path):
                default_storage.delete(target_thumb_path)

            self.image.name = target_name

        super().save(*args, **kwargs)

        # Generate thumbnail only on first upload.
        if should_create_thumbnail and self.image and self.image.storage.exists(self.image.name):
            self.create_thumbnail()

    def get_thumbnail_path(self, image_name=None):
        if not image_name:
            image_name = self.image.name
        if not image_name:
            return ''
        return f"thumb/{image_name}"

    def get_thumbnail_path_candidates(self, image_name=None):
        """
        Candidate thumbnail locations, first being the canonical one.
        Legacy candidates are kept for backward-compatible reads.
        """
        if not image_name:
            image_name = self.image.name
        if not image_name:
            return []

        candidates = [self.get_thumbnail_path(image_name)]

        if image_name.startswith('geopedia_slike/'):
            candidates.append(image_name.replace('geopedia_slike/', 'geopedia_slike/thumb/', 1))
        if image_name.startswith('memorial_images/'):
            candidates.append(image_name.replace('memorial_images/', 'memorial_images/thumb/', 1))

        # Deduplicate while preserving order.
        return list(dict.fromkeys(candidates))

    @property
    def thumbnail_url(self):
        thumb_candidates = self.get_thumbnail_path_candidates()
        # Prefer thumbnail when available.
        for thumb_path in thumb_candidates:
            if default_storage.exists(thumb_path):
                return default_storage.url(thumb_path)
        # Fallback for legacy images without thumbnails.
        if self.image:
            try:
                return self.image.url
            except ValueError:
                pass
        # Last fallback: construct /media/ thumbnail path.
        return f"/media/{thumb_candidates[0]}" if thumb_candidates else ''

    def create_thumbnail(self, size=(300, 300)):
        if not self.image:
            return

        try:
            img = Image.open(self.image)
        except (FileNotFoundError, OSError):
            # Broken file reference in DB: skip thumbnail generation.
            return
        img = img.convert('RGB')
        img.thumbnail(size, Image.LANCZOS)

        thumb_io = BytesIO()
        img.save(thumb_io, format='JPEG', quality=85)

        thumb_path = self.get_thumbnail_path()
        default_storage.save(thumb_path, ContentFile(thumb_io.getvalue()))

    def __str__(self):
        return f"Image for {self.content_object.__class__.__name__} {self.object_id} with caption: {self.caption}"

class TranslatedContent(django_models.Model):
    html_element_id = django_models.CharField(max_length=255, verbose_name=_('HTML element'))
    lang = django_models.CharField(
        max_length=10,
        choices=settings.LANGUAGES,
        default='sl',
        verbose_name=_('Language'),
        help_text=_('Select the language for the content.')
    )
    content = tinymce_models.HTMLField(verbose_name=_('Content'))

    class Meta:
        unique_together = ('html_element_id', 'lang')
        verbose_name = _('Translated Content')
        verbose_name_plural = _('Translated Content')

    def __str__(self):
        return f"{self.html_element_id} ({self.lang})"

