# Copyright (C) 2018 AJ Ostergaard
#
# This file is part of django-payments-redsys.
#
# django-payments-redsys is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# django-payments-redsys is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with django-payments-redsys.  If not, see <https://www.gnu.org/licenses/>.

from __future__ import unicode_literals

import base64
import hashlib
import hmac
import json
import logging
import re

import pyDes
import requests
from django import forms
from django.http import HttpResponseRedirect
from payments import PaymentError
from payments.core import BasicProvider, get_base_url, urljoin
from payments.forms import PaymentForm

logger = logging.getLogger(__name__)

# https://en.wikipedia.org/wiki/ISO_4217
ISO_CURRENCY_LOOKUP = {
    "EUR": "978",
    "GBP": "826",
    "USD": "840",
}


def compute_signature(salt: str, payload: bytes, key: str):
    """
    For Redsys:
        salt = order number (Ds_Order or Ds_Merchant_Order)
        payload = Ds_MerchantParameters
        key = shared secret (aka key) from the Redsys Administration Module
              (Merchant Data Query option in the "See Key" section)
    """
    bkey = base64.b64decode(key)
    des3 = pyDes.triple_des(
        bkey, mode=pyDes.CBC, IV="\0" * 8, pad="\0", padmode=pyDes.PAD_NORMAL
    )
    pepper = des3.encrypt(str(salt))
    payload_hash = hmac.new(pepper, payload, hashlib.sha256).digest()
    return base64.b64encode(payload_hash)


def compare_signatures(sig1, sig2):
    alphanumeric_characters = re.compile("[^a-zA-Z0-9]")
    sig1safe = re.sub(alphanumeric_characters, "", sig1)
    sig2safe = re.sub(alphanumeric_characters, "", sig2)
    return sig1safe == sig2safe


class RedsysResponseForm(forms.Form):
    Ds_SignatureVersion = forms.CharField(max_length=256)
    Ds_Signature = forms.CharField(max_length=256)
    Ds_MerchantParameters = forms.CharField(max_length=2048)


REDSYS_ENVIRONMENTS = {
    "real": "https://sis.redsys.es",
    "test": "https://sis-t.redsys.es:25443",
}


class RedsysProvider(BasicProvider):
    def __init__(self, *args, **kwargs):
        self.language = kwargs.pop("language")
        self.merchant_code = kwargs.pop("merchant_code")
        self.terminal = kwargs.pop("terminal")
        self.shared_secret = kwargs.pop("shared_secret")
        self.currency = kwargs.pop("currency", "978")
        self.direct_payment = str(kwargs.pop("direct_payment", False)).upper()
        self.endpoint = REDSYS_ENVIRONMENTS[kwargs.pop("environment", "test")]
        self.order_number_prefix = kwargs.pop("order_number_prefix", "0000")
        self.order_number_min_length = kwargs.pop("order_number_min_length", 0)
        self.process_on_redirect = kwargs.pop("process_on_redirect", False)
        self.signature_version = kwargs.pop("signature_version", "HMAC_SHA256_V1")
        super(RedsysProvider, self).__init__(*args, **kwargs)

    def get_form(self, payment, data=None):
        order_number = self.get_order_number(payment)

        amount = str(int(payment.total * 100))  # price is in cents
        # switch to payment.get_total_price() at some point
        # returns a TaxedMoney from 'prices'
        # need the gross element of TaxedMoney
        # also switch to amount.quantize(CENTS, rounding=ROUND_HALF_UP)

        data = self.encode_redsys_request(
            order_number,
            {
                "DS_MERCHANT_AMOUNT": amount,
                "DS_MERCHANT_ORDER": order_number,
                "DS_MERCHANT_MERCHANTCODE": self.merchant_code,
                "DS_MERCHANT_DIRECTPAYMENT": self.direct_payment,
                "DS_MERCHANT_CURRENCY": self.get_currency_code(payment),
                "DS_MERCHANT_TRANSACTIONTYPE": "0",
                "DS_MERCHANT_TERMINAL": self.terminal,
                "DS_MERCHANT_MERCHANTURL": self.get_return_url(payment),
                "DS_MERCHANT_URLOK": (
                    self.get_return_url(payment)
                    if self.process_on_redirect
                    else self.get_success_url(payment)
                ),
                "DS_MERCHANT_URLKO": (
                    self.get_return_url(payment)
                    if self.process_on_redirect
                    else self.get_failure_url(payment)
                ),
                "Ds_Merchant_ConsumerLanguage": self.language,
            },
        )

        return PaymentForm(
            data,
            action=self.endpoint_form,
            method="post",
            payment=payment,
            hidden_inputs=True,
        )

    def process_data(self, payment, request):
        success = False
        url_success = urljoin(get_base_url(), payment.get_success_url())
        url_failure = urljoin(get_base_url(), payment.get_failure_url())

        form = RedsysResponseForm(request.POST or request.GET)
        logger.info(
            f"Processing gateway response payment={payment.pk} form={form.data}"
        )

        if form.is_valid():
            logger.debug(
                "processing payment gateway response for payment %d" % payment.pk
            )
            response_dict = form.cleaned_data
            order_number = self.get_order_number(payment)
            merchant_parameters = self.validate_and_parse_response(
                response_dict, order_number
            )
            transaction_type = merchant_parameters["Ds_TransactionType"]
            response_code = int(merchant_parameters["Ds_Response"])

            # https://pagosonline.redsys.es/desarrolladores-inicio/integrate-con-nosotros/parametros-de-entrada-y-salida/
            if response_code < 100:
                # Authorised transaction for payments and preauthorisations
                if transaction_type == "0":
                    payment.captured_amount = (
                        int(merchant_parameters["Ds_Amount"]) / 100
                    )
                    payment.transaction_id = merchant_parameters["Ds_AuthorisationCode"]
                    payment.extra_data = merchant_parameters
                    payment.change_status("confirmed")
                    logger.debug("payment %d confirmed" % payment.pk)
                elif transaction_type == "1":
                    payment.extra_data = merchant_parameters
                    payment.change_status("preauth")
                    logger.debug("payment %d preauthorised" % payment.pk)
                else:
                    logger.debug(
                        "authorised payment response but unrecognised transaction type %s"
                        % transaction_type
                    )
                success = True

            if response_code == 900:
                # Authorised transaction for refunds and confirmations
                if transaction_type == "3":
                    payment.extra_data = merchant_parameters
                    payment.change_status("refunded")
                    logger.debug("payment %d automatic refund" % payment.pk)
                else:
                    logger.debug(
                        "authorised refund response but unrecognised transaction type %s"
                        % transaction_type
                    )
                success = True

            if response_code > 100 and response_code != 900:
                # any of a long list of errors/rejections
                payment.extra_data = merchant_parameters
                payment.change_status(
                    "rejected", message="Ds_Response was %d" % response_code
                )
                # perhaps import and raise PaymentError from django-payments
                logger.debug("rejected: %s" % json.dumps(merchant_parameters))

        if success:
            return HttpResponseRedirect(self.get_success_url(payment))
        else:
            return HttpResponseRedirect(self.get_failure_url(payment))

    def get_failure_url(self, payment):
        return urljoin(get_base_url(), payment.get_failure_url())

    def get_success_url(self, payment):
        return urljoin(get_base_url(), payment.get_success_url())

    def refund(self, payment, amount=None):
        """
        It requests a refund to Redsys using their Webservices layer

        More information about the process and the error codes at
        https://canales.redsys.es/canales/ayuda/documentacion/Manual%20integracion%20para%20conexion%20por%20Web%20Service.pdf
        """
        refund_amount = amount or payment.captured_amount
        # cents = str(int(
        #     refund_amount.quantize(CENTS, rounding=ROUND_HALF_UP)) * 100
        # )
        cents = str(int(refund_amount * 100))
        order_number = self.get_order_number(payment)
        currency_code = self.get_currency_code(payment)

        data = self.encode_redsys_request(
            order_number,
            {
                "DS_MERCHANT_AMOUNT": cents,
                "DS_MERCHANT_CURRENCY": currency_code,
                "DS_MERCHANT_MERCHANTCODE": self.merchant_code,
                "DS_MERCHANT_ORDER": order_number,
                "DS_MERCHANT_TERMINAL": self.terminal,
                "DS_MERCHANT_TRANSACTIONTYPE": "3",
            },
        )

        response = requests.post(self.endpoint_rest, json=data)
        response_code = None
        response_dict = json.loads(response.content.decode("utf-8"))

        if "errorCode" in response_dict:
            raise PaymentError(
                f"Redsys error {response_dict['errorCode']} '{response_dict['errorCodeDescription']}'"
            )

        merchant_parameters = self.validate_and_parse_response(
            response_dict, order_number
        )
        response_code = merchant_parameters["Ds_Response"]
        if response_code in ["0400", "0900"]:
            return refund_amount

        raise PaymentError(
            "Redsys error '{}'".format(response_code or "non matched response")
        )

    @property
    def endpoint_form(self):
        return "{}/sis/realizarPago".format(self.endpoint)

    @property
    def endpoint_rest(self):
        return "{}/sis/rest/trataPeticionREST".format(self.endpoint)

    def get_currency_code(self, payment):
        currency = payment.currency or self.currency
        # we translate textual currencies to numerical codes used by redsys
        # to allow apps to use the ISO 4217 currency code
        currency_number = ISO_CURRENCY_LOOKUP.get(currency, currency)
        return currency_number

    def validate_and_parse_response(self, response_dict, order_number):
        signature = compute_signature(
            order_number,
            response_dict["Ds_MerchantParameters"].encode(),
            self.shared_secret,
        )

        if not compare_signatures(signature.decode(), response_dict["Ds_Signature"]):
            raise PaymentError("signature mismatch - possible attack")

        binary_merchant_parameters = base64.b64decode(
            response_dict["Ds_MerchantParameters"]
        )

        merchant_parameters = json.loads(binary_merchant_parameters.decode())
        return merchant_parameters

    def get_order_number(self, payment):
        if order_number := getattr(payment, "order_number", None):
            return order_number
        return f"{self.order_number_prefix}{payment.pk}"

    def encode_redsys_request(self, order_number, merchant_data):
        json_data = json.dumps(merchant_data)
        logger.debug(json_data)
        b64_params = base64.b64encode(json_data.encode())
        signature = compute_signature(
            str(order_number),
            b64_params,
            self.shared_secret,
        )
        return {
            "Ds_SignatureVersion": self.signature_version,
            "Ds_MerchantParameters": b64_params.decode(),
            "Ds_Signature": signature.decode(),
        }
