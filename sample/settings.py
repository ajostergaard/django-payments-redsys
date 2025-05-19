"""
Django settings for sample app and tests.

"""

import os
from pathlib import Path

from django.utils.translation import gettext_lazy as _

BASE_DIR = Path(__file__).resolve().parent.parent

ENVIRONMENT = os.getenv("ENVIRONMENT", "dev")
SECRET_KEY = "no-secret"

INSTALLED_APPS = [
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.staticfiles",
    "django.forms",
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
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": "test.db",
    }
}
DEFAULT_AUTO_FIELD = "django.db.models.AutoField"

BASE_URL = "http://localhost:8000"

ALLOWED_HOSTS = ["*"]

USE_TZ = True

# -----
# django-payments

PAYMENT_HOST = BASE_URL.split("//")[1]
PAYMENT_USES_SSL = BASE_URL.startswith("https")

# A dotted path to the Payment class:
PAYMENT_MODEL = "sample.Payment"

PAYMENT_VARIANTS = {
    "redsys": (
        "payments_redsys.RedsysProvider",
        {
            # Mandatory fields, set with defaults as per redsys test environment
            # https://pagosonline.redsys.es/desarrolladores-inicio/integrate-con-nosotros/tarjetas-y-entornos-de-prueba/
            "merchant_code": "999008881",
            "terminal": "001",
            "shared_secret": "sq7HjrUOBfKmC576ILgskD5srU870gJ7",
            # Optional settings
            "order_number_prefix": "TEST",
            "order_number_min_length": 6,
            "language": "002",  # english. Use 003 for catalan, 001 for spanish
            "currency": "EUR",
            "process_on_redirect": ENVIRONMENT == "dev",
        },
    )
}
PAYMENT_VARIANTS["default"] = PAYMENT_VARIANTS["redsys"]
