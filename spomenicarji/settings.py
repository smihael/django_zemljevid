"""
Django settings for spomenicarji project.

Generated by 'django-admin startproject' using Django 5.0.

For more information on this file, see
https://docs.djangoproject.com/en/5.0/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/5.0/ref/settings/
"""

from pathlib import Path
import os


# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

from dotenv import load_dotenv
load_dotenv(os.path.join(BASE_DIR.parent, 'secrets.env'))


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.0/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.getenv('SECRET_KEY')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = False

ALLOWED_HOSTS = [
    #"220.ablak.arnes.si",
    "www.partizanstvo.si",
    "partizanstvo.si",
    "localhost",
    "127.0.0.1"
]

CSRF_TRUSTED_ORIGINS = [
    "https://partizanstvo.si",
    "https://www.partizanstvo.si",  # če uporabljaš tudi www
]

import socket

# Get current machine's IP address
try:
    hostname = socket.gethostname()
    local_ip = socket.gethostbyname(hostname)
except:
    local_ip = None

# Add current machine IP if it resolved correctly
if local_ip:
    ALLOWED_HOSTS.append(local_ip)
print(f"[settings] Added local IP {local_ip} to ALLOWED_HOSTS")

# Application definition

INSTALLED_APPS = [
    "admin_interface",
    "colorfield",
    # Django default apps
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # gis
    "django.contrib.gis",
    "rest_framework",
    "rest_framework_gis",
    #admin, forms 
    "tinymce",
    'mapwidgets',
    'leaflet',
    #slike
    #'filer',
    #'cabinet',
    #debugging
    'django_extensions',
    'django_tables2',
    'django_filters',
    'widget_tweaks',
    #moje aplikacije
    "zemljevid",
]

X_FRAME_OPTIONS = "SAMEORIGIN"
SILENCED_SYSTEM_CHECKS = ["security.W019"]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    #'pyinstrument.middleware.ProfilerMiddleware',
]

LANGUAGES = [
    ('en', 'English'),
    ('sl', 'Slovenian'),
]

LOCALE_PATHS = [
    BASE_DIR / 'locale',
]

#PYINSTRUMENT_PROFILE_DIR = 'profiles' 

ROOT_URLCONF = 'spomenicarji.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'spomenicarji.wsgi.application'


# Database
# https://docs.djangoproject.com/en/5.0/ref/settings/#databases

DATABASES = {
    "default": {
        "ENGINE": "django.contrib.gis.db.backends.postgis",
        "HOST": os.getenv("DB_HOST"),
        "NAME": os.getenv("DB_NAME"),
        "PASSWORD": os.getenv("DB_PASSWORD"),
        "PORT": os.getenv("DB_PORT"),
        "USER": os.getenv("DB_USER"),
    }
}

CSP_SCRIPT_SRC = (
    "'self'",
    'https://maps.googleapis.com',
    'https://maps.gstatic.com',
)
CSP_IMG_SRC = (
    "'self'",
    'https://maps.gstatic.com',
    'https://maps.googleapis.com',
)

# Password validation
# https://docs.djangoproject.com/en/5.0/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
# https://docs.djangoproject.com/en/5.0/topics/i18n/

LANGUAGE_CODE = 'sl-si'

TIME_ZONE = 'Europe/Ljubljana'

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.0/howto/static-files/

STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'static')
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# Media files (user-uploaded content)
# https://docs.djangoproject.com/en/5.0/topics/files/
MEDIA_ROOT = os.path.expanduser('~/media_files')
MEDIA_URL = '/media/'


# Default primary key field type
# https://docs.djangoproject.com/en/5.0/ref/settings/#default-auto-field
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'



# zemljevid settings
DEFAULT_LAT = '46.1511'  # Default latitude for the map center
DEFAULT_LNG = '14.9955'  # Default longitude for the map center

#django-leaflet 

LEAFLET_CONFIG = {
    'ATTRIBUTION_PREFIX': 'Spomeničarji',
}

# django-map-widgets settings

MAP_WIDGETS = {
    "GoogleMap": {
        "apiKey": os.getenv("GOOGLE_MAP_API_KEY"),
    },
    "Leaflet": {
        "PointField": {
            "mapOptions": {"zoom": 12, "scrollWheelZoom": False},
            "tileLayer": {
                "urlTemplate": "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
                "options": {"maxZoom": 20},
            },
            "markerFitZoom": 14,
            "showZoomNavigation": True,
            "mapCenterLocation": [DEFAULT_LAT,DEFAULT_LNG],
            "attributionPrefix": "Spomeničarji",
            }
        }
    }

MAPTILER_API_KEY = os.getenv('MAPTILER_API_KEY')

