from decimal import Decimal
from typing import Iterable

from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from payments import PurchasedItem
from payments.models import BasePayment


class Payment(BasePayment):
    class Meta:
        verbose_name = _("Payment")
        verbose_name_plural = _("Payments")
        ordering = ["-modified"]

    def __str__(self):
        return (
            f"id={self.id} total={self.total} status={self.status}"
        )

    def get_success_url(self) -> str:
        return reverse("pay-success", kwargs={"pk": self.pk})

    def get_failure_url(self) -> str:
        return reverse("pay-failure", kwargs={"pk": self.pk})

    def get_purchased_items(self) -> Iterable[PurchasedItem]:
        yield PurchasedItem(
            name="You bought something...",
            sku=f"{self.id}",
            quantity=1,
            price=self.total,
            currency="EUR",
        )
