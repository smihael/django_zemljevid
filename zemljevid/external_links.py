import json
import re
import time
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, quote, unquote, urlencode, urlparse
from urllib.request import Request, urlopen


WIKIDATA_PROJECT_IDENTIFIERS = {'wikidata', 'wikidata-item'}
WIKIPEDIA_HOST = 'sl.wikipedia.org'
WIKIDATA_ID_PATTERN = re.compile(r'^Q[1-9][0-9]*$', re.IGNORECASE)


class ExternalLinkError(ValueError):
    """Raised when an external link cannot be converted to a stored ID."""


def is_wikidata_project(project):
    identifier = (getattr(project, 'identifier', '') or '').lower()
    pattern = (getattr(project, 'url', '') or '').lower()
    return identifier in WIKIDATA_PROJECT_IDENTIFIERS or 'wikidata.org/' in pattern


def _extract_from_project_url(pattern, value):
    if not pattern or '[ID]' not in pattern:
        return None

    parts = pattern.split('[ID]')
    expression = '(?P<external_id>[^/?#]+)'.join(re.escape(part) for part in parts)
    match = re.fullmatch(expression, value, flags=re.IGNORECASE)
    if not match:
        return None
    return unquote(match.group('external_id'))


def _wikipedia_title(value):
    parsed = urlparse(value)
    if parsed.scheme not in {'http', 'https'} or parsed.netloc.lower() != WIKIPEDIA_HOST:
        return None

    prefix = '/wiki/'
    if not parsed.path.startswith(prefix):
        return None

    title = unquote(parsed.path[len(prefix):]).strip()
    if not title or title.startswith(('Special:', 'File:', 'Category:')):
        return None
    return title.replace('_', ' ')


def wikipedia_url_from_title(title):
    if not title:
        return ''
    return f'https://{WIKIPEDIA_HOST}/wiki/{quote(title.replace(" ", "_"), safe="():,")}'


def wikipedia_url_from_wikidata_id(wikidata_id):
    if not wikidata_id or not WIKIDATA_ID_PATTERN.fullmatch(str(wikidata_id).strip()):
        return ''
    return f'https://{WIKIPEDIA_HOST}/wiki/Special:GoToLinkedPage/slwiki/{str(wikidata_id).strip().upper()}'


def _wikidata_id_from_wikipedia(title, *, opener=urlopen, timeout=3, retries=3):
    query = urlencode({
        'action': 'query',
        'prop': 'pageprops',
        'redirects': '1',
        'titles': title,
        'format': 'json',
    })
    request = Request(
        f'https://{WIKIPEDIA_HOST}/w/api.php?{query}',
        headers={'User-Agent': 'django-zemljevid/connected-entry-resolver'},
    )

    last_error = None
    for attempt in range(retries):
        try:
            with opener(request, timeout=timeout) as response:
                payload = json.load(response)
            break
        except (HTTPError, URLError, TimeoutError, OSError, ValueError) as exc:
            last_error = exc
            if attempt + 1 < retries:
                time.sleep(0.5 * (attempt + 1))
    else:
        raise ExternalLinkError('Wikipedia lookup failed. Please enter a Wikidata ID manually.') from last_error

    pages = payload.get('query', {}).get('pages', {})
    for page in pages.values():
        wikidata_id = page.get('pageprops', {}).get('wikibase_item')
        if wikidata_id and WIKIDATA_ID_PATTERN.fullmatch(wikidata_id):
            return wikidata_id.upper(), page.get('title') or title

    raise ExternalLinkError('The Wikipedia article has no Wikidata item.')


def wikidata_id_from_label(label, *, opener=urlopen, timeout=3, retries=3):
    """Find a Wikidata item by an exact Slovenian label."""
    query = urlencode({
        'action': 'wbsearchentities',
        'search': label,
        'language': 'sl',
        'uselang': 'sl',
        'limit': '10',
        'format': 'json',
    })
    request = Request(
        f'https://www.wikidata.org/w/api.php?{query}',
        headers={'User-Agent': 'django-zemljevid/connected-entry-resolver'},
    )
    last_error = None
    for attempt in range(retries):
        try:
            with opener(request, timeout=timeout) as response:
                payload = json.load(response)
            break
        except (HTTPError, URLError, TimeoutError, OSError, ValueError) as exc:
            last_error = exc
            if attempt + 1 < retries:
                time.sleep(0.5 * (attempt + 1))
    else:
        raise ExternalLinkError('Wikidata search failed.') from last_error

    normalized_label = ' '.join((label or '').replace('_', ' ').split()).casefold()
    for item in payload.get('search', []):
        item_label = ' '.join((item.get('label') or '').split()).casefold()
        item_id = item.get('id') or ''
        if item_label == normalized_label and WIKIDATA_ID_PATTERN.fullmatch(item_id):
            return item_id.upper(), item.get('label') or label

    raise ExternalLinkError('No exact Wikidata label match was found.')


def resolve_external_link(project, value, *, opener=urlopen):
    """Return the canonical ID and optional page title for an entered link."""
    value = (value or '').strip()
    if not value:
        return value, None

    identifier = (getattr(project, 'identifier', '') or '').lower()
    if identifier == 'misc':
        return value, None

    wikipedia_title = _wikipedia_title(value)
    wikidata_project = is_wikidata_project(project)
    if wikipedia_title and wikidata_project:
        return _wikidata_id_from_wikipedia(wikipedia_title, opener=opener)

    if wikipedia_title:
        raise ExternalLinkError('Wikipedia article URLs can only be entered for a Wikidata connection.')

    if not urlparse(value).scheme:
        if wikidata_project and not WIKIDATA_ID_PATTERN.fullmatch(value):
            raise ExternalLinkError('Enter a Wikidata ID such as Q123 or a Slovenian Wikipedia article URL.')
        if wikidata_project:
            return value.upper(), None
        return value, None

    extracted_id = _extract_from_project_url(getattr(project, 'url', None), value)
    if extracted_id:
        if wikidata_project and not WIKIDATA_ID_PATTERN.fullmatch(extracted_id):
            raise ExternalLinkError('Enter a valid Wikidata ID such as Q123.')
        if wikidata_project:
            return extracted_id.upper(), None
        return extracted_id, None

    raise ExternalLinkError('Enter the ID or a URL matching the selected external project.')


def normalize_external_id(project, value, *, opener=urlopen):
    """Return the canonical ID for an admin-entered external ID or URL."""
    external_id, _ = resolve_external_link(project, value, opener=opener)
    return external_id
