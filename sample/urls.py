from django.urls import include, path

from .views import (
    PaymentFailureView,
    PaymentFormView,
    PaymentSuccessView,
    proceed_to_pay,
)

urlpatterns = [
    # 3rd party apps
    path("payments/", include("payments.urls")),
    # my views
    path("", PaymentFormView.as_view(), name="pay-form"),
    path("<int:pk>/pay", proceed_to_pay, name="pay-proceed"),
    path("<int:pk>/success", PaymentSuccessView.as_view(), name="pay-success"),
    path("<int:pk>/failure", PaymentFailureView.as_view(), name="pay-failure"),
]
