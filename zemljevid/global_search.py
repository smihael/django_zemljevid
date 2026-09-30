import re
import unicodedata
from functools import reduce
from operator import or_
from urllib.parse import urlencode

from django.contrib.gis.db.models import GeometryField
from django.db.models import (
    BooleanField,
    CharField,
    DateField,
    DateTimeField,
    DecimalField,
    F,
    Func,
    FloatField,
    IntegerField,
    Q,
    Subquery,
    TextField,
    Value,
)
from django.db.models.functions import Cast, Lower
from django.shortcuts import render
from django.urls import reverse
from django.utils.html import strip_tags
from django.utils.translation import gettext as _
from django.views import View
from django.contrib.postgres.fields import ArrayField

from .models import (
    PartisanMemorial,
    CroatianPartisanMemorial,
    PartisanHospital,
    PartisanNaming,
    PartisanPointsWithoutMemorial,
    OtherMemorials,
    PartisanTrail,
    OkupacijskeMeje,
    ConnectedExternalEntry,
    MemorialImage,
)


# Public map record types, including map-only layers. Anonymous submissions and
# hidden records are intentionally not included in public search results.
SEARCH_MODELS = (
    PartisanMemorial,
    CroatianPartisanMemorial,
    PartisanHospital,
    PartisanNaming,
    PartisanPointsWithoutMemorial,
    OtherMemorials,
    PartisanTrail,
    OkupacijskeMeje,
)

# Translate common Slovenian/Croatian diacritics and dash variants in SQL, so
# accentless queries and hyphen/dash variants behave like the map search.
TRANSLATE_FROM = 'ČĆĐŠŽčćđšž‐‑‒–—―−-'
TRANSLATE_TO = 'CCDSZccdsz        '

SEARCHABLE_FIELD_TYPES = (
    CharField,
    TextField,
    IntegerField,
    FloatField,
    DecimalField,
    BooleanField,
    DateField,
    DateTimeField,
    ArrayField,
)

EXCLUDED_FIELD_NAMES = {'geom', 'hidden'}
MIN_QUERY_LENGTH = 3
MATCH_CONTEXT_CHARS = 60


class Translate(Func):
    function = 'TRANSLATE'
    output_field = TextField()


def normalize_query(query):
    query = unicodedata.normalize('NFD', query or '')
    query = ''.join(character for character in query if unicodedata.category(character) != 'Mn')
    query = query.replace('đ', 'd').replace('Đ', 'd')
    query = re.sub(r'[-‐‑‒–—―−]+', ' ', query)
    return re.sub(r'\s+', ' ', query).strip().lower()


def _normalize_with_positions(value):
    normalized_chars = []
    source_positions = []

    for source_position, character in enumerate(value):
        decomposed = ' ' if character in '-‐‑‒–—―−' else unicodedata.normalize('NFD', character)
        for normalized_character in decomposed:
            if unicodedata.category(normalized_character) == 'Mn':
                continue
            if normalized_character in 'đĐ':
                normalized_character = 'd'
            for folded_character in normalized_character.lower():
                if folded_character.isspace():
                    if normalized_chars and normalized_chars[-1] != ' ':
                        normalized_chars.append(' ')
                        source_positions.append(source_position)
                    continue
                normalized_chars.append(folded_character)
                source_positions.append(source_position)

    if normalized_chars and normalized_chars[-1] == ' ':
        normalized_chars.pop()
        source_positions.pop()
    return ''.join(normalized_chars), source_positions


def _snippet_around_match(value, terms):
    normalized, source_positions = _normalize_with_positions(value)
    matches = [
        (normalized.find(term), term)
        for term in terms
        if term and normalized.find(term) >= 0
    ]
    if not matches:
        return None

    normalized_start, term = min(matches, key=lambda match: match[0])
    normalized_end = normalized_start + len(term)
    source_start = source_positions[normalized_start]
    source_end = source_positions[normalized_end - 1] + 1
    start = max(0, source_start - MATCH_CONTEXT_CHARS)
    end = min(len(value), source_end + MATCH_CONTEXT_CHARS)
    return {
        'before': value[start:source_start],
        'match': value[source_start:source_end],
        'after': value[source_end:end],
        'leading_ellipsis': start > 0,
        'trailing_ellipsis': end < len(value),
    }


def _has_minimum_query_length(query):
    return sum(character.isalnum() for character in normalize_query(query)) >= MIN_QUERY_LENGTH


def _normalized_expression(value):
    return Lower(Translate(
        Cast(value, output_field=TextField()),
        Value(TRANSLATE_FROM),
        Value(TRANSLATE_TO),
    ))


def _related_record_ids_containing(model, filters, field_names, term):
    queryset = model.objects.filter(**filters)
    conditions = []
    for index, field_name in enumerate(field_names):
        alias = f'_global_related_{index}'
        queryset = queryset.annotate(**{alias: _normalized_expression(F(field_name))})
        conditions.append(Q(**{f'{alias}__contains': term}))
    return queryset.filter(reduce(or_, conditions)).values('object_id')


def _searchable_fields(model):
    fields = []
    for field in model._meta.concrete_fields:
        if field.name in EXCLUDED_FIELD_NAMES or field.is_relation:
            continue
        if isinstance(field, GeometryField):
            continue
        if isinstance(field, SEARCHABLE_FIELD_TYPES):
            fields.append((field.name, field, F(field.name)))
    return fields


def _search_model(model, terms):
    queryset = model.objects.all()
    if any(field.name == 'hidden' for field in model._meta.concrete_fields):
        queryset = queryset.filter(Q(hidden=False) | Q(hidden__isnull=True))

    searchable_fields = _searchable_fields(model)
    normalized_aliases = []
    for index, (field_name, field, value_expression) in enumerate(searchable_fields):
        alias = f'_global_normalized_{index}'
        queryset = queryset.annotate(**{
            alias: Lower(Translate(
                Cast(value_expression, output_field=TextField()),
                Value(TRANSLATE_FROM),
                Value(TRANSLATE_TO),
            ))
        })
        normalized_aliases.append((field_name, field, value_expression, alias))

    content_type_filters = {
        'content_type__app_label': model._meta.app_label,
        'content_type__model': model._meta.model_name,
    }
    external_fields = (
        'external_project__name',
        'external_project__identifier',
        'external_project__description',
        'external_project__url',
        'external_id',
        'additional_info',
    )
    image_fields = (
        'caption',
        'author',
        'source',
        'date_taken',
        'date_mode',
        'date_approx_text',
        'license__name',
        'license__url',
    )

    for term in terms:
        term_conditions = [Q(**{f'{alias}__contains': term}) for _, _, _, alias in normalized_aliases]

        for field in model._meta.concrete_fields:
            if field.name in EXCLUDED_FIELD_NAMES or not field.choices:
                continue
            choice_conditions = [
                Q(**{field.name: value})
                for value, label in field.flatchoices
                if term in normalize_query(str(label))
            ]
            if choice_conditions:
                term_conditions.append(reduce(or_, choice_conditions))

        if model is PartisanMemorial:
            categories = PartisanMemorial.objects.annotate(
                _global_category_normalized=_normalized_expression(F('memorial_categories__name')),
            ).filter(_global_category_normalized__contains=term).values('pk')
            term_conditions.append(Q(pk__in=Subquery(categories)))

        term_conditions.extend((
            Q(pk__in=Subquery(_related_record_ids_containing(
                ConnectedExternalEntry, content_type_filters, external_fields, term,
            ))),
            Q(pk__in=Subquery(_related_record_ids_containing(
                MemorialImage, content_type_filters, image_fields, term,
            ))),
        ))
        queryset = queryset.filter(reduce(or_, term_conditions))

    queryset = queryset.annotate(
        _global_model_label=Value(str(model._meta.verbose_name_plural), output_field=CharField()),
        _global_model_slug=Value(model._meta.model_name, output_field=CharField()),
        _global_object_id=Cast('pk', output_field=IntegerField()),
        _global_name=Cast('name', output_field=TextField()),
        _global_description=Cast('description', output_field=TextField()),
    )
    return queryset.values(
        '_global_model_label',
        '_global_model_slug',
        '_global_object_id',
        '_global_name',
        '_global_description',
    )


def _related_values_for_page(model, object_ids):
    content_type_filters = {
        'content_type__app_label': model._meta.app_label,
        'content_type__model': model._meta.model_name,
        'object_id__in': object_ids,
    }
    values_by_object = {object_id: [] for object_id in object_ids}

    external_fields = (
        ('external_project__name', _('External project')),
        ('external_project__identifier', _('External project ID')),
        ('external_project__description', _('External project description')),
        ('external_project__url', _('External project URL')),
        ('external_id', _('External ID')),
        ('additional_info', _('Additional info')),
    )
    external_query_fields = [field_name for field_name, _ in external_fields]
    for row in ConnectedExternalEntry.objects.filter(**content_type_filters).values(
        'object_id', *external_query_fields
    ):
        values_by_object[row['object_id']].extend(
            (label, row[field_name]) for field_name, label in external_fields
        )

    image_fields = (
        ('caption', _('Caption')),
        ('author', _('Author')),
        ('source', _('Source')),
        ('date_taken', _('Date taken')),
        ('date_mode', _('Date mode')),
        ('date_approx_text', _('Approximate date')),
        ('license__name', _('Image license')),
        ('license__url', _('Image license URL')),
    )
    image_query_fields = [field_name for field_name, _ in image_fields]
    for row in MemorialImage.objects.filter(**content_type_filters).values(
        'object_id', *image_query_fields
    ):
        values_by_object[row['object_id']].extend(
            (label, row[field_name]) for field_name, label in image_fields
        )

    if model is PartisanMemorial:
        category_label = str(model._meta.get_field('memorial_categories').verbose_name)
        for object_id, category_name in model.objects.filter(pk__in=object_ids).values_list(
            'pk', 'memorial_categories__name'
        ):
            values_by_object[object_id].append((category_label, category_name))

    return values_by_object


def _add_match_details(results, query):
    terms = normalize_query(query).split()
    groups = {}
    for result in results:
        model_slug = result['_global_model_slug']
        groups.setdefault(model_slug, []).append(result)

    for model in SEARCH_MODELS:
        model_results = groups.get(model._meta.model_name, [])
        if not model_results:
            continue

        object_ids = [result['_global_object_id'] for result in model_results]
        field_definitions = [
            (field_name, field)
            for field_name, field, _ in _searchable_fields(model)
        ]
        db_rows = model.objects.filter(pk__in=object_ids).values(
            'pk', *(field_name for field_name, _ in field_definitions)
        )
        values_by_object = {
            row['pk']: [
                (str(field.verbose_name), row[field_name], field)
                for field_name, field in field_definitions
            ]
            for row in db_rows
        }
        for object_id, related_values in _related_values_for_page(model, object_ids).items():
            values_by_object.setdefault(object_id, []).extend(
                (str(label), value, None) for label, value in related_values
            )

        for result in model_results:
            matching_values = []
            for label, raw_value, field in values_by_object.get(result['_global_object_id'], []):
                if raw_value in (None, ''):
                    continue

                display_value = strip_tags(str(raw_value)).strip()
                candidate_values = [display_value]
                if field is not None and field.choices:
                    choice_labels = dict(field.flatchoices)
                    choice_label = choice_labels.get(raw_value)
                    if choice_label:
                        candidate_values.insert(0, str(choice_label))

                for candidate in candidate_values:
                    snippet = _snippet_around_match(candidate, terms)
                    if snippet:
                        matching_values.append({
                            'field': label,
                            **snippet,
                        })
                        break

            result['model_label'] = result.pop('_global_model_label')
            result['name'] = result.pop('_global_name') or ''
            result['description'] = result.pop('_global_description') or ''
            result['matches'] = matching_values
            slug = result['_global_model_slug']
            object_id = result['_global_object_id']
            result['map_url'] = f"{reverse('map')}?{urlencode({'layer': slug, 'id': object_id})}"
            if slug != OkupacijskeMeje._meta.model_name:
                result['detail_url'] = reverse(
                    'memorial_detail',
                    kwargs={'model_slug': slug, 'object_id': object_id},
                )
            else:
                result['detail_url'] = None


def build_global_search_page(query, page_number, page_size):
    terms = normalize_query(query).split()
    if not terms:
        return [], False

    offset = (page_number - 1) * page_size
    candidate_limit = offset + page_size + 1
    candidates = []
    for model in SEARCH_MODELS:
        model_rows = _search_model(model, terms).order_by(
            '_global_name',
            '_global_object_id',
        )[:candidate_limit]
        candidates.extend(model_rows)

    candidates.sort(key=lambda result: (
        result['_global_model_label'].casefold(),
        (result['_global_name'] or '').casefold(),
        result['_global_object_id'],
    ))
    has_next = len(candidates) > offset + page_size
    page_results = candidates[offset:offset + page_size]
    _add_match_details(page_results, query)
    return page_results, has_next


class GlobalSearchView(View):
    template_name = 'global_search.html'
    page_size = 25

    def get(self, request):
        query = request.GET.get('q', '').strip()
        results = []
        query_too_short = bool(query) and not _has_minimum_query_length(query)
        page_number = request.GET.get('page', 1)
        try:
            page_number = max(1, int(page_number))
        except (TypeError, ValueError):
            page_number = 1
        has_previous = page_number > 1
        has_next = False

        if query and not query_too_short:
            results, has_next = build_global_search_page(query, page_number, self.page_size)

        return render(request, self.template_name, {
            'query': query,
            'query_too_short': query_too_short,
            'results': results,
            'page_number': page_number,
            'has_previous': has_previous,
            'has_next': has_next,
            'result_count': len(results),
        })
