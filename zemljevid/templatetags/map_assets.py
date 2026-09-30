import hashlib
from pathlib import Path

from django import template
from django.conf import settings
from django.contrib.staticfiles import finders


register = template.Library()


@register.simple_tag
def map_script_version():
    """Return a content fingerprint for the map script served from STATIC_ROOT."""
    static_file = Path(settings.STATIC_ROOT) / 'js' / 'map.js'
    if not static_file.is_file():
        found_file = finders.find('js/map.js')
        if isinstance(found_file, (list, tuple)):
            found_file = found_file[0] if found_file else None
        if not found_file:
            return 'missing'
        static_file = Path(found_file)

    return hashlib.sha256(static_file.read_bytes()).hexdigest()[:16]
