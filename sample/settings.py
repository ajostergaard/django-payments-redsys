"""
Django settings for sample app and tests.

"""

import os
from pathlib import Path
from warnings import filterwarnings

from django.utils.translation import gettext_lazy as _

# ------------------------------------------------------------------
# First-party Django settings

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.0/howto/deployment/checklist/

SECRET_KEY = "no-secret"


# Application definition

INSTALLED_APPS = [
    "payments",
    "sample",
]

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "INFO",
    },
}

ROOT_URLCONF = "sample.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]
# make sure the django forms renderer uses local dirs templates
# (e.g. to override the leaflet admin widget template)
FORM_RENDERER = "django.forms.renderers.TemplatesSetting"

# Database
# https://docs.djangoproject.com/en/5.0/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': 'test.db',
    }
}# Try and prevent issue "Remaining connection slots are reserved for non-replication superuser connections"
# On the server you may set "ALTER SYSTEM SET idle_in_transaction_session_timeout = '5min';"
CONN_MAX_AGE = 1 * 60
CONN_HEALTH_CHECKS = True
DEFAULT_AUTO_FIELD = "django.db.models.AutoField"


# Forms, prevent deprecation warnings for URL Fields

filterwarnings(
    "ignore", "The FORMS_URLFIELD_ASSUME_HTTPS transitional setting is deprecated."
)
FORMS_URLFIELD_ASSUME_HTTPS = True

# -----
# django-payments
BASE_URL = "http://localhost:8000"
PAYMENT_HOST = BASE_URL.split("//")[1]
PAYMENT_USES_SSL = BASE_URL.startswith("https")

# A dotted path to the Payment class:
PAYMENT_MODEL = "sample.Payment"

PAYMENT_VARIANTS = {
    "redsys": (
        "pay.redsys.RedsysProvider",
        {
            "order_number_prefix": "TEST:",
            "order_number_min_length": 6,
            "language": "002",  # english. Use 003 for catalan, 001 for spanish
            # defaults as per redsys test environment
            # https://pagosonline.redsys.es/desarrolladores-inicio/integrate-con-nosotros/tarjetas-y-entornos-de-prueba/
            "merchant_code": "999008881",
            "terminal": "001",
            "shared_secret":"sq7HjrUOBfKmC576ILgskD5srU870gJ7",
            "currency": "EUR",
        },
    )
}
PAYMENT_VARIANTS["default"] = PAYMENT_VARIANTS["redsys"]
