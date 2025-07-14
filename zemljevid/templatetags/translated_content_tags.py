# myapp/templatetags/translated_content_tags.py
from django import template
from django.utils.translation import get_language
from ..models import TranslatedContent

register = template.Library()

from django.conf import settings

@register.simple_tag
def get_translated_content(element_id):
    lang = get_language()
    fallback_lang = 'sl'
    try:
        return TranslatedContent.objects.get(html_element_id=element_id, lang=lang).content
    except TranslatedContent.DoesNotExist:
        try:
            return TranslatedContent.objects.get(html_element_id=element_id, lang=fallback_lang).content
        except TranslatedContent.DoesNotExist:
            return ''
