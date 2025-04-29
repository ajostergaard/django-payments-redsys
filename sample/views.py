from typing import Any

from django.shortcuts import redirect
from django.template.response import TemplateResponse
from django.urls import reverse
from django.views.generic import CreateView, DetailView
from payments import RedirectNeeded, get_payment_model

from .forms import PaymentForm

Payment = get_payment_model()


class PaymentFormView(CreateView):
    template_name = "sample/payment-form.html"
    context_object_name = "payment"
    model = Payment
    form_class = PaymentForm

    def get_success_url(self):
        return reverse("pay-proceed", kwargs={"pk": self.object.pk})


async def proceed_to_pay(request, pk: int = None):
    payment = await get_payment_model().objects.aget(pk=pk)

    try:
        form = payment.get_form(data=request.POST or None)
    except RedirectNeeded as redirect_to:
        return redirect(str(redirect_to))

    return TemplateResponse(
        request,
        "sample/payment.html",
        {
            "form": form,
            "payment": payment,
        },
    )


class PaymentSuccessView(DetailView):
    template_name = "sample/success.html"
    model = Payment
    context_object_name = "payment"


class PaymentFailureView(DetailView):
    template_name = "sample/failure.html"
    model = Payment
    context_object_name = "payment"
