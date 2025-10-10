from django.contrib.gis.db import models
from django.db import models as django_models
from django.db import connection
from tinymce import models as tinymce_models
import os
from PIL import Image
from io import BytesIO
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError

from django.conf import settings
from django.utils.translation import gettext_lazy as _, gettext_noop
from django.core.validators import RegexValidator
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
    OBELISK = 'obelisk', _('Obelisk')
    STONE = 'spominski kamen', _('Memorial stone')
    STOLPERSTEIN = 'spotikavec', _('Stolperstein')
    BUST = 'doprsni kip', _('Bust')
    TOMBSTONE = 'nagrobnik', _('Tombstone')
    GRAVE = 'grob', _('Grave')
    SCULPTURE = 'skulptura', _('Sculpture')
    MUSEUM = 'muzej', _('Museum')
    AIRPLANE = 'avion', _('Airplane')
    ANCHOR = 'sidro', _('Anchor')
    INFOTABLE = 'infotabla', _('Info table')
    MEMORIAL_ROOM = 'spominska soba', _('Memorial room')
    DIRECTION_SIGN = 'smerokaz', _('Direction sign')
    OTHER = 'durgo', _('Other')

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

    class Meta:
        abstract = True
        managed = False

class Memorial(AbstractGeoEntry):
    """
    Model for memorials with a gallery field.
    """
    
    memorial_access = django_models.TextField(null=True, blank=True, verbose_name=_('Location and access'),
                                          help_text=_('Enter information about access to the memorial'))
    memorial_text = tinymce_models.HTMLField(blank=True, null=True, verbose_name=_('Text on the memorial'))
    memorial_author = django_models.CharField(max_length=255, blank=True, null=True, verbose_name=_('Author of the memorial'))
    memorial_start = django_models.CharField(max_length=255, blank=True, null=True, verbose_name=_('Time of creation'),)

    status = models.IntegerField(choices=MemorialStatus.choices, default=MemorialStatus.NA, blank=True, null=True, verbose_name=_('Status'))

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
        help_text=_('Enter the name of the municipality where the memorial is located.')
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
    external_id = models.CharField(max_length=255, blank=True, null=True, verbose_name=_('External ID'), help_text=_('External project ID.'))

    class Meta:
        verbose_name = _('Connected External Entry')
        verbose_name_plural = _('Connected External Entries')

    def __str__(self):
        return f"{self.content_object} - {self.external_project.name} - {self.external_id}" if self.content_object else self.external_id

    def save(self, *args, **kwargs):
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


from django.core.files.uploadedfile import InMemoryUploadedFile

def validate_image_size(image):
    # Limit the image size to 5MB (5 * 1024 * 1024 bytes)
    max_size = 5 * 1024 * 1024
    if image.size > max_size:
        raise ValidationError(_("The image file is too large. Size should be less than 5 MB."))

class MemorialImage(models.Model):
    
    image = models.ImageField(max_length=500, validators=[validate_image_size], verbose_name=_('Image'),
                              help_text=_('Upload an image related to the memorial.'))
    caption = models.CharField(max_length=255, blank=True, null=True)
    author = models.CharField(max_length=255, blank=True, null=True)
    date_taken = models.DateField(blank=True, null=True, verbose_name=_('Date taken'),
                                  help_text=_('Enter the date when the image was taken.'))
    license = models.ForeignKey(ImageLicense, on_delete=models.SET_NULL, blank=True, null=True)
    source = models.CharField(max_length=255, blank=True, null=True)
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')
    
    class Meta:
        verbose_name = _('Memorial Image')
        verbose_name_plural = _('Memorial Images')

    def save(self, *args, **kwargs):
        # Set upload_to dynamically before saving
        if self.content_type and self.object_id and self.image:
            # Build the path using content_type and object_id
            filename = os.path.basename(self.image.name)
            upload_path = f"memorial_images/{self.content_type.model}/{self.object_id}/{filename}"
            self.image.name = upload_path

        if self.pk:
            old = type(self).objects.filter(pk=self.pk).first()
            if old and old.image and self.image and old.image != self.image:
                if os.path.isfile(old.image.path):
                    os.remove(old.image.path)
                # Remove old thumbnail if exists
                old_thumb_path = self.get_thumbnail_path(old.image.name)
                if default_storage.exists(old_thumb_path):
                    default_storage.delete(old_thumb_path)
        # Ensure the related object is a subclass of AbstractGeoEntry
        if not issubclass(self.content_object.__class__, AbstractGeoEntry):
            raise ValidationError(_("The image can only be associated with a model that inherits from AbstractGeoEntry."))

        super().save(*args, **kwargs)

        # Create and save thumbnail
        if self.image:
            self.create_thumbnail()

    def get_thumbnail_path(self, image_name=None):
        if not image_name:
            image_name = self.image.name

        if 'geopedia_slike/' in image_name:
            return image_name.replace('geopedia_slike/', 'geopedia_slike/thumb/')
        else:
            return image_name.replace('memorial_images/', 'memorial_images/thumb/')

    @property
    def thumbnail_url(self):
        thumb_path = self.get_thumbnail_path()
        # Try to use default_storage if file exists, else construct /media/ path
        if default_storage.exists(thumb_path):
            return default_storage.url(thumb_path)
        # Fallback: construct /media/ path
        return f"/media/{thumb_path}"

    def create_thumbnail(self, size=(300, 300)):
        if not self.image:
            return

        img = Image.open(self.image)
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

