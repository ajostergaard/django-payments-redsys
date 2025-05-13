from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class PayConfig(AppConfig):
    name = "sample"
    verbose_name = _("Sample Payments App")
