from decimal import Decimal

from django import forms
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from payments import get_payment_model


class PaymentForm(forms.ModelForm):

    class Meta:
        model = get_payment_model()
        fields = [
            "billing_first_name",
            "billing_city",
        ]

    billing_first_name = forms.CharField(
        label=_("Name"),
        required=True,
        max_length=180,
    )
    billing_city = forms.CharField(
        label=_("City"),
        required=False,
        max_length=180,
    )

    def save(self, *args, **kwargs):
        self.instance.total = Decimal("50")
        self.instance.currency = "EUR"
        self.instance.variant = "redsys"
        return super().save(*args, **kwargs)
